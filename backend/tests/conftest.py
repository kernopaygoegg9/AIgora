"""Shared fixtures for API tests: a participants file of Fake Adapter participants and a
throwaway discussion record folder, wired in through the backend's environment variables."""

from __future__ import annotations

import json
from collections.abc import Callable
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


@pytest.fixture
def client(data_dir) -> TestClient:
    return TestClient(create_app())


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
