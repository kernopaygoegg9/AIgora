"""Ends every process the fake CLIs started, so none outlives a test.

The fake CLIs (fake_*_cli.py, via fake_cli_support.record_pid) write their own pid and every
child's pid as `<pid>.pid` files into the folder `AIGORA_TEST_PID_DIR` names. conftest's
`cli_processes` fixture wraps each test in `reap_cli_processes`.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

PID_DIR_ENV = "AIGORA_TEST_PID_DIR"


def alive(pid: int) -> bool:
    """Whether process `pid` is still running."""
    if sys.platform == "win32":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def recorded_pids(pid_dir: Path) -> list[int]:
    return [int(f.stem) for f in pid_dir.glob("*.pid")]


def _kill(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
    else:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, signal.SIGKILL)


@contextlib.contextmanager
def reap_cli_processes(pid_dir: Path) -> Iterator[Path]:
    """Point the fake CLIs at `pid_dir`; on exit, end every recorded process still running."""
    pid_dir.mkdir(parents=True, exist_ok=True)
    previous = os.environ.get(PID_DIR_ENV)
    os.environ[PID_DIR_ENV] = str(pid_dir)
    try:
        yield pid_dir
    finally:
        if previous is None:
            os.environ.pop(PID_DIR_ENV, None)
        else:
            os.environ[PID_DIR_ENV] = previous
        pids = recorded_pids(pid_dir)
        for pid in pids:
            if alive(pid):
                _kill(pid)
        deadline = time.monotonic() + 5
        while any(alive(pid) for pid in pids) and time.monotonic() < deadline:
            time.sleep(0.05)
