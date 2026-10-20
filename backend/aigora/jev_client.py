"""Jev Client: the probability that a discussion has reached consensus, from TypeSafe's Jev.

Uses the official SDK (`typesafe-sdk`): one System One request whose state is the
discussion transcript and whose only question is a Noul ("all participants agree
on one answer"); the Noul value (0-1) is the probability. The threshold is not
decided here (consensus judge B does that).

The API key comes from the backend's `.env` / environment (`aigora.env`) and is
passed explicitly; it never leaves the backend. Tests replace the client with a
fake through `aigora.discussion.judges.create_jev_client`, or the HTTP layer with
the SDK's `transport` option.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from typesafe_sdk import AsyncTypeSafeClient, Noul, NoulCriteria, TypeSafeError

from aigora.env import TYPESAFE_API_KEY

# Seconds per HTTP operation (the SDK default of 10 s is short for a long transcript).
DEFAULT_TIMEOUT_SECONDS = 60.0

_QUESTION = "consensus"
CONSENSUS_NOUL = Noul(
    instructions=(
        "The state is a multi-participant discussion of `question`, round by round, with the "
        "moderator's consensus drafts. Have all participants reached consensus: do they all "
        "accept one answer to the question?"
    ),
    criteria=NoulCriteria(
        true="Every participant in the latest round accepts the same answer; no open disagreement remains.",
        false="At least one participant still disagrees with, or asks to change, the proposed answer.",
    ),
)


class JevError(Exception):
    """Jev could not give a probability (network, auth, quota, bad response)."""


class JevClient(Protocol):
    async def consensus_probability(self, transcript: Mapping[str, Any]) -> float:
        """0-1 probability that the discussion in `transcript` has reached consensus.
        Raises `JevError` when Jev cannot answer."""
        ...


class TypeSafeJevClient:
    def __init__(self, api_key: str, *, timeout: float = DEFAULT_TIMEOUT_SECONDS, **sdk_options: Any):
        # `sdk_options` are passed to `AsyncTypeSafeClient` (tests: transport, retry, compression).
        self._api_key = api_key
        self._timeout = timeout
        self._sdk_options = sdk_options

    async def consensus_probability(self, transcript: Mapping[str, Any]) -> float:
        try:
            async with AsyncTypeSafeClient(
                api_key=self._api_key, timeout=self._timeout, **self._sdk_options
            ) as client:
                response = await client.system_one(state=dict(transcript), questions={_QUESTION: CONSENSUS_NOUL})
        except TypeSafeError as exc:
            raise JevError(_safe_message(exc, self._api_key)) from None
        answer = response.nouls.get(_QUESTION)
        if answer is None:
            raise JevError("Jev 沒有回答「是否已取得共識」")
        return float(answer.noul)


def _safe_message(exc: Exception, api_key: str) -> str:
    text = f"{type(exc).__name__}: {exc}"
    return text.replace(api_key, "***") if api_key else text


def create_jev_client(env: Mapping[str, str]) -> JevClient:
    """The real client, with the key from `env` (`aigora.env.backend_env()`)."""
    key = env.get(TYPESAFE_API_KEY, "").strip()
    if not key:
        raise JevError(f".env 沒有設定 {TYPESAFE_API_KEY}")
    return TypeSafeJevClient(key)
