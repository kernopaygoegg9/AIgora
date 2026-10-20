"""The built frontend is served with an index.html fallback, but never for /api or /ws paths."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from aigora.app import create_app


@pytest.fixture
def dist_client(tmp_path, data_dir) -> TestClient:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>AIgora</title>", encoding="utf-8")
    return TestClient(create_app(frontend_dist=dist))


def test_client_side_route_falls_back_to_index_html(dist_client):
    response = dist_client.get("/history/some-id")
    assert response.status_code == 200
    assert "AIgora" in response.text


@pytest.mark.parametrize(
    "path",
    ["/api/no-such-endpoint", "/api/discussions/..%2F..%2Fparticipants", "/ws/no-such-socket"],
)
def test_unknown_api_path_is_404_even_with_a_built_frontend(dist_client, path):
    assert dist_client.get(path).status_code == 404
