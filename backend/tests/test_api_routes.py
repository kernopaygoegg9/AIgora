"""HTTP endpoints in the spec that are registered but not built yet answer "not implemented"."""

import pytest
from fastapi.testclient import TestClient

from aigora.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.mark.parametrize(
    "path",
    [
        "/api/avatars/claude.png",
    ],
)
def test_http_endpoint_is_registered_but_not_implemented(client, path):
    response = client.get(path)
    assert response.status_code == 501
    assert response.json() == {"detail": "not implemented"}
