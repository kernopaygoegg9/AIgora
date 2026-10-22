"""Shared fixtures: a participants file of Fake Adapter participants and a throwaway
discussion record folder (wired in through the backend's environment variables), and the
reaper that ends every process the fake CLIs started."""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aigora.app import create_app


@pytest.fixture
def data_dir(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "discussions"
    monkeypatch.setenv("AIGORA_DATA_DIR", str(path))
    return path


@pytest.fixture
def write_participants(tmp_path, monkeypatch) -> Callable[[str], Path]:
    """Write a participants.toml (TOML text) and point the backend at it."""

    def write(text: str) -> Path:
        path = tmp_path / "participants.toml"
        path.write_text(text, encoding="utf-8")
        monkeypatch.setenv("AIGORA_PARTICIPANTS_FILE", str(path))
        return path

    return write


# The fake CLIs (fake_*_cli.py) write their own pid and every child's pid as `<pid>.pid`
# files into the folder this variable names.
PID_DIR_ENV = "AIGORA_TEST_PID_DIR"


def _alive(pid: int) -> bool:
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
        pids = [int(f.stem) for f in pid_dir.glob("*.pid")]
        for pid in pids:
            if _alive(pid):
                _kill(pid)
        deadline = time.monotonic() + 5
        while any(_alive(pid) for pid in pids) and time.monotonic() < deadline:
            time.sleep(0.05)


@pytest.fixture
def cli_processes(tmp_path) -> Iterator[Path]:
    """Ends the fake CLIs' processes (and their children) at teardown, even if the test failed."""
    with reap_cli_processes(tmp_path / "cli-pids") as pid_dir:
        yield pid_dir


@pytest.fixture
def client(data_dir) -> TestClient:
    return TestClient(create_app(frontend_dist=None))


def fake_participant(pid: str, name: str, **options) -> str:
    """A `[[participant]]` block for the Fake Adapter with the given options."""
    lines = ["[[participant]]", f'id = "{pid}"', f'display_name = "{name}"', 'adapter = "fake"']
    if options:
        lines.append("[participant.options]")
        lines += [f"{key} = {json.dumps(value)}" for key, value in options.items()]
    return "\n".join(lines) + "\n\n"


def run_discussion(client: TestClient, question: str, settings: dict) -> list[dict]:
    """Send `start` and collect every server message until `discussion_finished`."""
    received: list[dict] = []
    with client.websocket_connect("/ws/discussion") as ws:
        ws.send_json({"type": "start", "question": question, "settings": settings})
        while True:
            msg = ws.receive_json()
            received.append(msg)
            if msg["type"] in ("discussion_finished", "error"):
                break
    return received
