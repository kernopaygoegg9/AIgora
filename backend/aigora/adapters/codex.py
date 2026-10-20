"""`codex` adapter: drives the Codex CLI (`codex exec --json`).

Isolation (ADR 0002): every local feature is disabled except `code_mode_host`
(web search breaks without it); the user's config and rules are ignored; the
sandbox is read-only; the CLI runs inside the turn's workspace. The argument
list below is long on purpose; do not "simplify" it. Re-run the `real_ai`
canary test after every CLI upgrade, since new versions may add tools.

The prompt goes through stdin (`-`), which avoids command-line length and
quoting limits (on Windows `codex` is an npm `.cmd` shim).

No participant options yet.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import subprocess
import sys
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
from aigora.config import ParticipantConfig

_STATUS_TIMEOUT_SECONDS = 15

# Local features to turn off (ADR 0002). Never add `code_mode_host` here.
DISABLED_FEATURES: tuple[str, ...] = (
    "shell_tool",
    "unified_exec",
    "view_image",
    "browser_use",
    "browser_use_external",
    "computer_use",
    "apps",
    "plugins",
    "multi_agent",
    "multi_agent_v2",
    "image_generation",
    "hooks",
    "in_app_browser",
    "skill_search",
    "workspace_dependencies",
)


def exec_args(request: TurnRequest) -> list[str]:
    """Arguments after the executable for one isolated, non-interactive turn."""
    args = [
        "exec",
        "--json",
        "--ephemeral",
        "--skip-git-repo-check",
        "--ignore-user-config",
        "--ignore-rules",
        "--sandbox", "read-only",
        "--cd", str(request.workspace),
        "-c", 'web_search="live"',
        "--color", "never",
    ]
    for feature in DISABLED_FEATURES:
        args += ["--disable", feature]
    if request.participant.model:
        args += ["--model", request.participant.model]
    args.append("-")  # read the prompt from stdin
    return args


class _Turn:
    """Turns the CLI's JSONL events into adapter events."""

    def __init__(self) -> None:
        self._messages: dict[str, str] = {}  # agent_message id -> text so far, in arrival order
        self.error: str | None = None

    @property
    def text(self) -> str:
        return "\n\n".join(t for t in self._messages.values() if t)

    def feed(self, line: str) -> list[Delta]:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return []
        if not isinstance(event, dict):
            return []
        kind = event.get("type")
        if kind in ("item.started", "item.updated", "item.completed"):
            return self._item(event.get("item") or {})
        if kind == "turn.failed":
            error = event.get("error") or {}
            self.error = str(error.get("message") or error) if isinstance(error, dict) else str(error)
        elif kind == "error":
            self.error = str(event.get("message") or "")
        return []

    def _item(self, item: Mapping[str, Any]) -> list[Delta]:
        if item.get("type") != "agent_message":
            return []
        item_id = str(item.get("id"))
        new = str(item.get("text") or "")
        is_new_item = item_id not in self._messages
        old = self._messages.get(item_id, "")
        self._messages[item_id] = new
        if not new.startswith(old):
            return []  # the CLI rewrote the message; only `Completed` carries the fixed text
        added = new[len(old):]
        if not added:
            return []
        if is_new_item and len(self._messages) > 1 and any(self._messages[k] for k in list(self._messages)[:-1]):
            added = "\n\n" + added
        return [Delta(added)]


_AUTH_MARKERS = ("not logged in", "unauthorized", "401", "codex login", "please log in", "login required",
                 "refresh token", "token expired", "authentication")
_QUOTA_MARKERS = ("usage limit", "rate limit", "quota", "429", "too many requests", "insufficient_quota")


def classify(message: str) -> FailureKind | None:
    lowered = message.lower()
    if any(m in lowered for m in _QUOTA_MARKERS):
        return "quota"
    if any(m in lowered for m in _AUTH_MARKERS):
        return "auth"
    return None


async def _kill_tree(process: asyncio.subprocess.Process) -> None:
    """Terminate the CLI and everything it started (npm shim -> node -> native binary)."""
    if process.returncode is not None:
        return
    try:
        if sys.platform == "win32":
            killer = await asyncio.create_subprocess_exec(
                "taskkill", "/F", "/T", "/PID", str(process.pid),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            await killer.wait()
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass
    if process.returncode is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except asyncio.TimeoutError:
        pass


class CodexAdapter(Adapter):
    id = "codex"

    def __init__(self, command: Sequence[str] | None = None) -> None:
        # `command` replaces the `codex` executable (tests use a fake CLI).
        self._command = list(command) if command is not None else None

    def _executable(self) -> list[str] | None:
        if self._command is not None:
            return self._command
        found = shutil.which("codex")
        return [found] if found else None

    def validate_options(self, options: Mapping[str, Any]) -> None:
        if options:
            raise ValueError(f"unknown codex option(s): {', '.join(sorted(options))}")

    def capabilities(self, participant: ParticipantConfig) -> Capabilities:
        return Capabilities(web_access=True, streaming=True)

    async def check_availability(self, participant: ParticipantConfig) -> Availability:
        """`codex login status`: no model call, so no quota is spent."""
        executable = self._executable()
        if executable is None:
            return Availability(False, "codex CLI not found on PATH")
        try:
            process = await self._spawn(executable, ["login", "status"], cwd=None, stdin=False)
        except OSError as exc:
            return Availability(False, f"could not start codex CLI: {exc}")
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=_STATUS_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            return Availability(False, "codex login status did not answer in time")
        finally:
            await _kill_tree(process)
        output = (stdout + stderr).decode("utf-8", errors="replace").strip()
        if process.returncode != 0 or "not logged in" in output.lower():
            return Availability(False, f"codex: {output or 'not logged in'} (run `codex login`)")
        return Availability(True)

    async def _spawn(self, executable: list[str], args: list[str], cwd: str | None,
                     stdin: bool) -> asyncio.subprocess.Process:
        extra: dict[str, Any] = {}
        if sys.platform == "win32":
            extra["creationflags"] = subprocess.CREATE_NO_WINDOW
        else:
            extra["start_new_session"] = True  # own process group, so the whole tree can be killed
        return await asyncio.create_subprocess_exec(
            *executable, *args,
            cwd=cwd,
            stdin=subprocess.PIPE if stdin else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **extra,
        )

    async def run_turn(self, request: TurnRequest) -> AsyncIterator[AdapterEvent]:
        executable = self._executable()
        if executable is None:
            yield Failed("not_available", "codex CLI not found on PATH")
            return
        try:
            process = await self._spawn(executable, exec_args(request), str(request.workspace), stdin=True)
        except OSError as exc:
            yield Failed("not_available", f"could not start codex CLI: {exc}")
            return

        stderr_task: asyncio.Task[bytes] | None = None
        try:
            assert process.stdin and process.stdout and process.stderr
            stderr_task = asyncio.create_task(process.stderr.read())
            try:
                process.stdin.write(request.prompt.encode("utf-8"))
                await process.stdin.drain()
                process.stdin.close()
            except (BrokenPipeError, ConnectionResetError):
                pass  # the CLI exited early; its exit code and stderr tell why

            turn = _Turn()
            async for raw in process.stdout:
                for delta in turn.feed(raw.decode("utf-8", errors="replace")):
                    yield delta
            returncode = await process.wait()
            stderr = (await stderr_task).decode("utf-8", errors="replace").strip()

            if turn.error is None and returncode == 0:
                if turn.text:
                    yield Completed(turn.text)
                else:
                    yield Failed("unknown", "codex: finished without a reply")
                return
            yield self._failure(turn.error, stderr, returncode)
        finally:
            await _kill_tree(process)
            if stderr_task is not None and not stderr_task.done():
                stderr_task.cancel()

    @staticmethod
    def _failure(error: str | None, stderr: str, returncode: int) -> Failed:
        detail = error or stderr[-500:] or f"codex exited with code {returncode}"
        kind = classify(f"{error or ''}\n{stderr}") or "crashed"
        return Failed(kind, f"codex: {detail}")


def create_adapter() -> Adapter:
    return CodexAdapter()
