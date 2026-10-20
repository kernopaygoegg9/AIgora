"""Every HTTP endpoint in the spec is registered and answers "not implemented"."""

import pytest
from fastapi.testclient import TestClient

from aigora.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.mark.parametrize(
    "path",
    [
        "/api/participants",
        "/api/options",
        "/api/discussions",
        "/api/discussions/some-id",
        "/api/avatars/claude.png",
    ],
)
def test_http_endpoint_is_registered_but_not_implemented(client, path):
    response = client.get(path)
    assert response.status_code == 501
    assert response.json() == {"detail": "not implemented"}


def test_discussion_websocket_is_registered_but_not_implemented(client):
    with client.websocket_connect("/ws/discussion") as ws:
        assert ws.receive_json() == {"type": "error", "message": "not implemented"}
