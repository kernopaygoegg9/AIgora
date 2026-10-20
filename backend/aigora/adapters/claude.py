"""`claude` adapter: drives the Claude Code CLI (`claude -p`) as a Participant.

Isolation (ADR 0002). Every turn runs as

    claude -p --output-format stream-json --verbose --include-partial-messages
           --tools WebSearch,WebFetch --allowedTools WebSearch,WebFetch
           --strict-mcp-config --setting-sources "" --disable-slash-commands
           --no-session-persistence [--model <model>]

inside the turn's workspace, with the prompt on stdin:

- `-p`: non-interactive.
- `--tools` / `--allowedTools`: only the two web tools exist, and they are
  pre-approved so nothing waits for a permission prompt. No shell, no file tools.
- `--strict-mcp-config` without `--mcp-config`: no MCP server at all (this is
  what removes claude.ai connectors, which `--tools` does not cover).
- `--setting-sources ""`: ignore user / project / local settings, so the
  user's hooks, permissions, plugins and CLAUDE.md-related settings never load.
- `--disable-slash-commands`: no skills.
- `ENABLE_CLAUDEAI_MCP_SERVERS=false` in the environment: belt and braces for
  claude.ai connectors.

The argument list is long on purpose; do not "simplify" it. A CLI upgrade can
add tools, so re-run the canary test (`pytest -m real_ai`) after upgrading.

Options: none (any `options` key is rejected). `model` is passed as `--model`.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from collections.abc import AsyncIterator, Mapping, Sequence
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

WEB_TOOLS = "WebSearch,WebFetch"

ISOLATION_ARGS: tuple[str, ...] = (
    "-p",
    "--output-format", "stream-json",
    "--verbose",
    "--include-partial-messages",
    "--tools", WEB_TOOLS,
    "--allowedTools", WEB_TOOLS,
    "--strict-mcp-config",
    "--setting-sources", "",
    "--disable-slash-commands",
    "--no-session-persistence",
)

AUTH_CHECK_TIMEOUT_SECONDS = 20.0
_STDERR_LIMIT = 4000

_AUTH_MARKERS = (
    "not logged in", "please run /login", "/login", "invalid api key", "authentication",
    "oauth token", "unauthorized", "401",
)
_QUOTA_MARKERS = (
    "usage limit", "rate limit", "rate_limit", "limit reached", "quota", "credit balance",
    "billing", "429", "out of extra usage",
)
# `error` field on assistant messages (newer CLI versions).
_ERROR_FIELD_KINDS: dict[str, FailureKind] = {
    "authentication_failed": "auth",
    "oauth_org_not_allowed": "auth",
    "billing_error": "quota",
    "rate_limit": "quota",
}


def _classify(text: str) -> FailureKind | None:
    lowered = text.lower()
    if any(m in lowered for m in _AUTH_MARKERS):
        return "auth"
    if any(m in lowered for m in _QUOTA_MARKERS):
        return "quota"
    return None


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    # The backend may itself be started from a Claude Code session; the child
    # must not think it is nested inside one.
    for key in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT"):
        env.pop(key, None)
    env["ENABLE_CLAUDEAI_MCP_SERVERS"] = "false"
    return env


class ClaudeAdapter(Adapter):
    id = "claude"

    def __init__(self, command: Sequence[str] | None = None) -> None:
        """`command`: how to start the CLI (default: `claude` on PATH). Tests pass a fake."""
        self._command = list(command) if command is not None else None

    def _resolve_command(self) -> list[str] | None:
        if self._command is not None:
            return self._command
        exe = shutil.which("claude")
        return [exe] if exe else None

    def validate_options(self, options: Mapping[str, Any]) -> None:
        if options:
            raise ValueError(f"the claude adapter has no options (got: {', '.join(sorted(options))})")

    def capabilities(self, participant: ParticipantConfig) -> Capabilities:
        return Capabilities(web_access=True, streaming=True)

    async def check_availability(self, participant: ParticipantConfig) -> Availability:
        command = self._resolve_command()
        if command is None:
            return Availability(False, "Claude Code CLI (`claude`) is not installed or not on PATH")
        try:
            proc = await asyncio.create_subprocess_exec(
                *command, "auth", "status", "--json",
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=_child_env(),
                **process_group_options(),
            )
        except OSError as exc:
            return Availability(False, f"cannot start Claude Code CLI: {exc}")
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=AUTH_CHECK_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            await kill_tree(proc)
            return Availability(False, "`claude auth status` did not answer in time")
        stdout = out.decode("utf-8", "replace")
        stderr = err.decode("utf-8", "replace").strip()
        try:
            status = json.loads(stdout)
        except json.JSONDecodeError:
            status = None
        if isinstance(status, dict) and "loggedIn" in status:
            if status["loggedIn"]:
                return Availability(True)
            return Availability(False, "Claude Code CLI is not logged in (run `claude auth login`)")
        detail = stderr or stdout.strip() or f"exit code {proc.returncode}"
        return Availability(False, f"cannot read Claude Code login status: {detail[:300]}")

    def build_args(self, participant: ParticipantConfig) -> list[str]:
        args = list(ISOLATION_ARGS)
        if participant.model:
            args += ["--model", participant.model]
        return args

    async def run_turn(self, request: TurnRequest) -> AsyncIterator[AdapterEvent]:
        command = self._resolve_command()
        if command is None:
            yield Failed("not_available", "Claude Code CLI (`claude`) is not installed or not on PATH")
            return
        try:
            proc = await asyncio.create_subprocess_exec(
                *command, *self.build_args(request.participant),
                cwd=str(request.workspace),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=_child_env(),
                limit=16 * 1024 * 1024,  # one stream-json line can be a whole long message
                **process_group_options(),  # so cancelling kills the CLI's children too
            )
        except OSError as exc:
            yield Failed("not_available", f"cannot start Claude Code CLI: {exc}")
            return

        stderr_task = asyncio.ensure_future(proc.stderr.read())
        try:
            async for event in self._stream(proc, request.prompt, stderr_task):
                yield event
        finally:
            # Normal end, cancellation (stop / timeout) or generator close: never
            # leave the CLI (or anything it started) running.
            await kill_tree(proc)
            if not stderr_task.done():
                stderr_task.cancel()

    async def _stream(
        self, proc: asyncio.subprocess.Process, prompt: str, stderr_task: asyncio.Future[bytes]
    ) -> AsyncIterator[AdapterEvent]:
        assert proc.stdin is not None and proc.stdout is not None
        try:
            proc.stdin.write(prompt.encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()
        except (BrokenPipeError, ConnectionResetError):
            pass  # the CLI died early; reported below from its exit status

        streamed: list[str] = []
        need_separator = False
        final: dict[str, Any] | None = None
        error_kind: FailureKind | None = None

        while line := await proc.stdout.readline():
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue  # not a stream-json line (warnings etc.)
            if not isinstance(msg, dict):
                continue
            kind = msg.get("type")
            if kind == "stream_event":
                ev = msg.get("event") or {}
                if ev.get("type") == "content_block_start" and streamed:
                    need_separator = True
                elif ev.get("type") == "content_block_delta":
                    delta = ev.get("delta") or {}
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        text = delta["text"]
                        if need_separator:
                            # A new text block after a web search etc.: keep paragraphs apart.
                            text = "\n\n" + text
                            need_separator = False
                        streamed.append(text)
                        yield Delta(text)
            elif kind == "assistant":
                field = msg.get("error")
                if isinstance(field, str):
                    error_kind = _ERROR_FIELD_KINDS.get(field, error_kind)
            elif kind == "result":
                final = msg

        await proc.wait()
        stderr = (await stderr_task).decode("utf-8", "replace").strip()[-_STDERR_LIMIT:]

        if final is not None and not final.get("is_error") and final.get("subtype", "success") == "success":
            text = "".join(streamed) if streamed else str(final.get("result") or "")
            yield Completed(text)
            return

        if final is not None:
            reason = str(final.get("result") or "") or "; ".join(map(str, final.get("errors") or [])) \
                or f"Claude Code CLI reported an error ({final.get('subtype')})"
            kind_ = error_kind or _classify(reason) or _classify(stderr) or "unknown"
            yield Failed(kind_, f"claude: {reason}")
            return

        detail = stderr or f"exit code {proc.returncode}"
        kind_ = error_kind or _classify(stderr) or "crashed"
        yield Failed(kind_, f"claude: CLI exited without a result ({detail})")


def create_adapter() -> Adapter:
    return ClaudeAdapter()

