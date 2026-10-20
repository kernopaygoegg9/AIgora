"""Jev Client: asks TypeSafe's Jev (System One, a Noul question) for the probability that a
discussion has reached consensus. The HTTP layer is replaced by a mock transport, so no
real TypeSafe call is made; the real-API test is marked `real_ai` and skipped by default."""

from __future__ import annotations

import json

import httpx2
import pytest
from typesafe_sdk import RetryPolicy

from aigora.env import TYPESAFE_API_KEY, backend_env
from aigora.jev_client import JevError, TypeSafeJevClient

TRANSCRIPT = {
    "question": "Is tea better than coffee?",
    "participants": ["Alpha", "Beta"],
    "rounds": [
        {"number": 1, "turns": [{"participant": "Alpha", "text": "Tea."}, {"participant": "Beta", "text": "Tea."}]},
    ],
}


def _client(handler, **options) -> TypeSafeJevClient:
    return TypeSafeJevClient(
        "sk-test-key",
        transport=httpx2.MockTransport(handler),
        compression=False,
        retry=RetryPolicy(max_retries=0),
        **options,
    )


def _noul_response(value: float) -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "model": "jev-latest",
            "usage": {"input_tokens": 10, "output_tokens": 1},
            "answers": {"consensus": {"type": "noul", "noul": value}},
        },
    )


async def test_returns_the_noul_probability_that_consensus_is_reached():
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return _noul_response(0.87)

    probability = await _client(handler).consensus_probability(TRANSCRIPT)

    assert probability == 0.87
    request = seen[0]
    assert request.method == "POST"
    assert request.headers["authorization"] == "Bearer sk-test-key"
    body = json.loads(request.content)
    # The whole discussion is the state; one Noul question asks whether consensus is reached.
    assert body["state"] == TRANSCRIPT
    question = body["questions"]["consensus"]
    assert question["type"] == "noul"
    assert "consensus" in question["instructions"].lower()


async def test_an_api_error_becomes_a_jev_error_without_the_key():
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(401, json={"error": {"message": "bad key"}})

    with pytest.raises(JevError) as error:
        await _client(handler).consensus_probability(TRANSCRIPT)
    assert "sk-test-key" not in str(error.value)


async def test_a_missing_answer_becomes_a_jev_error():
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={"model": "jev-latest", "usage": {}, "answers": {}})

    with pytest.raises(JevError):
        await _client(handler).consensus_probability(TRANSCRIPT)


@pytest.mark.real_ai
async def test_the_real_jev_returns_a_probability_between_0_and_1():
    key = backend_env().get(TYPESAFE_API_KEY, "").strip()
    if not key:
        pytest.skip(f"{TYPESAFE_API_KEY} is not set in .env or the environment")

    probability = await TypeSafeJevClient(key).consensus_probability(TRANSCRIPT)

    assert 0.0 <= probability <= 1.0
