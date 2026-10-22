"""`gemini` adapter: Gemini CLI (`npm install -g @google/gemini-cli`).

One turn = one headless run, `gemini --output-format stream-json`, with the
prompt on stdin (no `--prompt`, so long prompts do not hit the Windows
command-line limit and nothing in it is parsed as a flag). The JSONL events
are mapped like this:

- `message` with `role: "assistant"` -> `Delta(content)`
- `result` with `status: "success"` (and exit code 0) -> `Completed(all deltas)`
- `result` with `status: "error"`, `error` events with `severity: "error"`,
  a non-zero exit code or stderr -> `Failed` (kind guessed from the text:
  quota / auth, else exit-code based)
- everything else (`init`, `tool_use`, `tool_result`, warnings, non-JSON
  lines) is ignored.

Isolation (ADR 0002). Gemini CLI has no "ignore my settings" flag, so the
adapter writes its own *system settings override* file (highest-precedence
settings file, picked via `GEMINI_CLI_SYSTEM_SETTINGS_PATH`) and an *admin
policy* (`--admin-policy`, highest policy tier) into a private temp folder
outside the workspace, deleted after the turn:

- settings: `tools.core` = only `google_web_search` + `web_fetch`; every local
  tool also in `tools.exclude`; no MCP (`mcpServers` empty, `mcp.allowed` set
  to a name that does not exist, `admin.mcp.enabled` false); extensions,
  skills, hooks, subagents, checkpointing, memory/context files
  (`context.fileName` points to a file that does not exist), yolo mode,
  folder-trust prompts, auto update and telemetry all off.
- policy: deny `*` (low priority), allow the two web tools, deny every MCP
  tool (`mcpName = "*"`, highest priority).
- flags: `--approval-mode default` (in headless mode anything that would ask
  is denied), `--extensions none`, `--allowed-mcp-server-names <nothing>`.
- env: `GEMINI_SANDBOX=false` (a user `GEMINI_SANDBOX` would re-launch the CLI
  in a container with its own config), `NO_BROWSER=true`.

The user's own login (`~/.gemini/oauth_creds.json` or an API key) is still
used; nothing else from their config should take effect. The canary test in
`tests/test_gemini_adapter_real.py` checks this; rerun it after CLI upgrades.

Cancellation kills the whole process tree (the CLI re-launches itself as a
child process).

No `options`.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import tempfile
from collections.abc import AsyncIterator, Mapping, Sequence
from pathlib import Path
from typing import Any

from aigora.adapters.base import (
    Adapter,
    AdapterEvent,
    Availability,
    Capabilities,
    Completed,
    Delta,
    Failed,
    FailureKind,
    TurnRequest,
)
from aigora.adapters.subprocesses import kill_tree, process_group_options
from aigora.config import ParticipantConfig

INSTALL_HINT = "npm install -g @google/gemini-cli"
WEB_TOOLS = ["google_web_search", "web_fetch"]
NO_MCP = "__aigora_no_mcp__"
_NO_CONTEXT_FILE = "AIGORA_NO_CONTEXT_FILE.md"

# Every built-in local tool we know of (docs/reference/tools.md), plus legacy
# names. `tools.core` already restricts to WEB_TOOLS; this is a second layer.
LOCAL_TOOLS = [
    "run_shell_command",
    "read_file",
    "read_many_files",
    "list_directory",
    "glob",
    "grep_search",
    "search_file_content",
    "write_file",
    "replace",
    "edit",
    "save_memory",
    "write_todos",
    "activate_skill",
    "get_internal_docs",
    "list_mcp_resources",
    "read_mcp_resource",
    "ask_user",
    "enter_plan_mode",
    "exit_plan_mode",
    "invoke_agent",
    "codebase_investigator",
    "complete_task",
    "update_topic",
    "tracker_create_task",
    "tracker_update_task",
    "tracker_get_task",
    "tracker_list_tasks",
    "tracker_add_dependency",
    "tracker_visualize",
    "ShellTool",
    "ReadFileTool",
    "ReadManyFilesTool",
    "LSTool",
    "GlobTool",
    "GrepTool",
    "WriteFileTool",
    "EditTool",
    "MemoryTool",
]

SETTINGS: dict[str, Any] = {
    "tools": {
        "core": WEB_TOOLS,
        "allowed": WEB_TOOLS,
        "exclude": LOCAL_TOOLS,
        "sandbox": False,
        "discoveryCommand": "",
        "callCommand": "",
    },
    "mcpServers": {},
    "mcp": {"allowed": [NO_MCP], "serverCommand": ""},
    "hooksConfig": {"enabled": False},
    "hooks": {},
    "skills": {"enabled": False},
    "admin": {
        "extensions": {"enabled": False},
        "mcp": {"enabled": False},
        "skills": {"enabled": False},
    },
    "experimental": {"enableAgents": False, "extensionManagement": False},
    "security": {
        "disableYoloMode": True,
        "folderTrust": {"enabled": False},
        "blockGitExtensions": True,
    },
    "context": {
        "fileName": [_NO_CONTEXT_FILE],
        "includeDirectories": [],
        "loadMemoryFromIncludeDirectories": False,
    },
    "general": {
        "checkpointing": {"enabled": False},
        "enableAutoUpdate": False,
        "enableAutoUpdateNotification": False,
    },
    "telemetry": {"enabled": False},
    "privacy": {"usageStatisticsEnabled": False},
}

POLICY = f"""\
# AIgora: only web search / fetch (ADR 0002).
[[rule]]
toolName = "*"
decision = "deny"
priority = 10
denyMessage = "AIgora participants may only use web search and web fetch."

[[rule]]
toolName = "google_web_search"
decision = "allow"
priority = 500

[[rule]]
toolName = "web_fetch"
decision = "allow"
priority = 500

[[rule]]
mcpName = "*"
decision = "deny"
priority = 990
denyMessage = "AIgora participants may not use MCP tools."
"""

_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
_QUOTA_RE = re.compile(r"quota|RESOURCE_EXHAUSTED|\b429\b|rate.?limit", re.IGNORECASE)
_AUTH_RE = re.compile(
    r"\bauth|log ?in\b|credential|api key|\b401\b|\b403\b|PERMISSION_DENIED|UNAUTHENTICATED|invalid_grant",
    re.IGNORECASE,
)
_EXIT_AUTH = 41
_EXIT_INPUT = 42
_EXIT_TURN_LIMIT = 53
_STDERR_TAIL = 2000
_LINE_LIMIT = 16 * 1024 * 1024


class GeminiAdapter(Adapter):
    id = "gemini"

    def __init__(self, command: Sequence[str] | None = None, user_home: Path | None = None):
        """`command`: how to start the CLI (default: `gemini` on PATH). `user_home`: where
        `.gemini/` lives (default: `GEMINI_CLI_HOME` or the user's home). Both for tests."""
        self._command = list(command) if command else None
        self._user_home = user_home

    def validate_options(self, options: Mapping[str, Any]) -> None:
        if options:
            raise ValueError(
                f"the gemini adapter has no options (got: {', '.join(sorted(options))})"
            )

    def capabilities(self, participant: ParticipantConfig) -> Capabilities:
        return Capabilities(web_access=True, streaming=True)

    async def check_availability(self, participant: ParticipantConfig) -> Availability:
        if participant.model is not None and not _MODEL_RE.match(participant.model):
            return Availability(False, f"invalid gemini model name: {participant.model!r}")
        base = self._base_command()
        if base is None:
            return Availability(
                False, f"Gemini CLI not found on PATH; install it with `{INSTALL_HINT}`"
            )
        try:
            proc = await asyncio.create_subprocess_exec(
                *base,
                "--version",
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=_child_env(None),
            )
        except OSError as exc:
            return Availability(
                False, f"Gemini CLI could not be started ({exc}); install it with `{INSTALL_HINT}`"
            )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=30)
        except TimeoutError:
            await kill_tree(proc)
            return Availability(False, "`gemini --version` did not answer within 30 s")
        if proc.returncode != 0:
            detail = (err or out).decode("utf-8", "replace").strip()[-500:]
            return Availability(
                False, f"`gemini --version` failed (exit code {proc.returncode}): {detail}"
            )
        if not self._has_credentials():
            return Availability(
                False,
                "Gemini CLI is not logged in: run `gemini` once and log in with Google, or set GEMINI_API_KEY",
            )
        return Availability(True)

    async def run_turn(self, request: TurnRequest) -> AsyncIterator[AdapterEvent]:
        model = request.participant.model
        if model is not None and not _MODEL_RE.match(model):
            yield Failed("unknown", f"invalid gemini model name: {model!r}")
            return
        base = self._base_command()
        if base is None:
            yield Failed(
                "not_available", f"Gemini CLI not found on PATH; install it with `{INSTALL_HINT}`"
            )
            return

        config_dir = Path(tempfile.mkdtemp(prefix="aigora-gemini-"))
        proc: asyncio.subprocess.Process | None = None
        stderr_task: asyncio.Task[bytes] | None = None
        try:
            settings_path = config_dir / "settings.json"
            settings_path.write_text(json.dumps(SETTINGS, indent=2), encoding="utf-8")
            policy_path = config_dir / "aigora-policy.toml"
            policy_path.write_text(POLICY, encoding="utf-8")
            args = [
                *base,
                "--output-format",
                "stream-json",
                "--approval-mode",
                "default",
                "--extensions",
                "none",
                "--allowed-mcp-server-names",
                NO_MCP,
                "--admin-policy",
                str(policy_path),
            ]
            if model:
                args += ["--model", model]

            try:
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    cwd=request.workspace,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=_child_env(settings_path),
                    limit=_LINE_LIMIT,
                    **process_group_options(),
                )
            except OSError as exc:
                yield Failed(
                    "not_available",
                    f"Gemini CLI could not be started ({exc}); install it with `{INSTALL_HINT}`",
                )
                return

            stderr_task = asyncio.create_task(_read_tail(proc.stderr))
            await _send_prompt(proc, request.prompt)

            text: list[str] = []
            errors: list[str] = []
            result_status: str | None = None
            assert proc.stdout is not None
            async for raw in proc.stdout:
                event = _parse_line(raw)
                if event is None:
                    continue
                kind = event.get("type")
                if kind == "message" and event.get("role") == "assistant":
                    content = event.get("content")
                    if isinstance(content, str) and content:
                        text.append(content)
                        yield Delta(content)
                elif kind == "error" and event.get("severity") == "error":
                    errors.append(str(event.get("message", "")))
                elif kind == "result":
                    result_status = event.get("status")
                    error = event.get("error")
                    if isinstance(error, dict) and error.get("message"):
                        errors.append(str(error["message"]))

            code = await proc.wait()
            stderr = (await stderr_task).decode("utf-8", "replace").strip()
            if result_status == "success" and code == 0 and not errors:
                yield Completed("".join(text))
                return
            yield _failure(code, result_status, errors, stderr)
        finally:
            if proc is not None and proc.returncode is None:
                await kill_tree(proc)
            if stderr_task is not None and not stderr_task.done():
                stderr_task.cancel()
            shutil.rmtree(config_dir, ignore_errors=True)

    # --- helpers -----------------------------------------------------------

    def _base_command(self) -> list[str] | None:
        if self._command:
            return self._command
        exe = shutil.which("gemini")
        if exe is None:
            return None
        return _bypass_npm_shim(Path(exe)) or [exe]

    def _gemini_dir(self) -> Path:
        if self._user_home is not None:
            return self._user_home / ".gemini"
        home = os.environ.get("GEMINI_CLI_HOME")
        return Path(home) / ".gemini" if home else Path.home() / ".gemini"

    def _has_credentials(self) -> bool:
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            return True
        if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true":
            return True
        gemini_dir = self._gemini_dir()
        if (gemini_dir / "oauth_creds.json").is_file():
            return True
        env_file = gemini_dir / ".env"
        if env_file.is_file():
            content = env_file.read_text(encoding="utf-8", errors="replace")
            return (
                re.search(
                    r"^\s*(export\s+)?(GEMINI_API_KEY|GOOGLE_API_KEY)\s*=\s*\S", content, re.M
                )
                is not None
            )
        return False


def _child_env(settings_path: Path | None) -> dict[str, str]:
    env = dict(os.environ)
    env["GEMINI_SANDBOX"] = "false"
    env["NO_BROWSER"] = "true"
    if settings_path is not None:
        env["GEMINI_CLI_SYSTEM_SETTINGS_PATH"] = str(settings_path)
    return env


def _bypass_npm_shim(exe: Path) -> list[str] | None:
    """On Windows `gemini` is an npm `.cmd` shim; run node directly so no cmd.exe sits in between."""
    if exe.suffix.lower() not in (".cmd", ".bat"):
        return None
    package = exe.parent / "node_modules" / "@google" / "gemini-cli"
    try:
        manifest = json.loads((package / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    bin_field = manifest.get("bin")
    entry = bin_field.get("gemini") if isinstance(bin_field, dict) else bin_field
    if not isinstance(entry, str) or not (package / entry).is_file():
        return None
    node = exe.parent / "node.exe"
    node_path = str(node) if node.is_file() else shutil.which("node")
    if node_path is None:
        return None
    return [node_path, str(package / entry)]


async def _send_prompt(proc: asyncio.subprocess.Process, prompt: str) -> None:
    assert proc.stdin is not None
    try:
        proc.stdin.write(prompt.encode("utf-8"))
        await proc.stdin.drain()
        proc.stdin.close()
    except (BrokenPipeError, ConnectionResetError):
        pass  # the CLI exited early; its exit code / stderr tell why


async def _read_tail(stream: asyncio.StreamReader | None) -> bytes:
    if stream is None:
        return b""
    tail = b""
    while chunk := await stream.read(65536):
        tail = (tail + chunk)[-_STDERR_TAIL:]
    return tail


def _parse_line(raw: bytes) -> dict[str, Any] | None:
    line = raw.decode("utf-8", "replace").strip()
    if not line.startswith("{"):
        return None
    try:
        event = json.loads(line)
    except ValueError:
        return None
    return event if isinstance(event, dict) else None


def _failure(code: int, result_status: str | None, errors: list[str], stderr: str) -> Failed:
    details = [e for e in errors if e] or ([stderr] if stderr else [])
    text = "; ".join(details)
    kind: FailureKind
    if _QUOTA_RE.search(text):
        kind = "quota"
    elif code == _EXIT_AUTH or _AUTH_RE.search(text):
        kind = "auth"
    elif code == _EXIT_INPUT:
        kind, text = (
            "unknown",
            f"invalid input or arguments (exit code {code})" + (f": {text}" if text else ""),
        )
    elif code == _EXIT_TURN_LIMIT:
        kind, text = (
            "unknown",
            f"turn limit exceeded (exit code {code})" + (f": {text}" if text else ""),
        )
    else:
        kind = "crashed"
        if not text:
            text = (f"exit code {code}" if code != 0 else "the CLI ended without a result") + (
                f" (result status: {result_status})" if result_status else ""
            )
    return Failed(kind, f"gemini: {text}")


def create_adapter() -> Adapter:
    return GeminiAdapter()
