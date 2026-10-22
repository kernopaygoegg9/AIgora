"""Subprocess helpers shared by the CLI adapters (claude, codex, gemini).

A CLI is often a launcher for the real program (npm shim -> node -> native binary),
so cancelling a turn (stop / timeout) must kill the whole process tree, not just
the process we started. Start the CLI with `process_group_options()` and end it
with `kill_tree()`.

Not an adapter module: the registry only loads the ids it lists.
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
from typing import Any

KILL_WAIT_SECONDS = 5.0


def process_group_options() -> dict[str, Any]:
    """`create_subprocess_exec` keyword arguments that let `kill_tree` reach every descendant."""
    if sys.platform == "win32":
        # taskkill /T follows the parent-child tree; no console window pops up.
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
    return {"start_new_session": True}  # own process group, killed with killpg


async def kill_tree(proc: asyncio.subprocess.Process) -> None:
    """Terminate the process and everything it started; a no-op once it has exited."""
    if proc.returncode is None:
        try:
            if sys.platform == "win32":
                killer = await asyncio.create_subprocess_exec(
                    "taskkill",
                    "/F",
                    "/T",
                    "/PID",
                    str(proc.pid),
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await killer.wait()
            else:
                os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass
        if proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
    try:
        await asyncio.wait_for(proc.wait(), timeout=KILL_WAIT_SECONDS)
    except asyncio.TimeoutError:  # pragma: no cover - the OS did not reap it in time
        pass
