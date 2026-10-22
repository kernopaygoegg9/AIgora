"""GET /api/avatars/{filename}: avatar images from `assets/avatars/`, falling back to `default.png`."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aigora.app import create_app

AVATARS = Path(__file__).resolve().parents[2] / "assets" / "avatars"


@pytest.fixture
def client():
    return TestClient(create_app(frontend_dist=None))


@pytest.mark.parametrize(
    "name", ["claude.png", "codex.png", "gemini.png", "ollama.png", "fake.png", "default.png"]
)
def test_known_avatar_is_served_as_png(client, name):
    response = client.get(f"/api/avatars/{name}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == (AVATARS / name).read_bytes()


@pytest.mark.parametrize("name", ["missing.png", "..\\..\\AGENTS.md", "..png", "default"])
def test_unknown_or_unsafe_avatar_falls_back_to_default(client, name):
    response = client.get(f"/api/avatars/{name}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == (AVATARS / "default.png").read_bytes()


def test_a_path_never_leaves_the_avatars_folder(client):
    response = client.get("/api/avatars/..%2F..%2FAGENTS.md")
    assert b"# AIgora" not in response.content
