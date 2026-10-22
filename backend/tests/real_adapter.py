"""Shared helper for the real-Adapter tests (`test_*_real.py`, marked `real_ai`).

A canary only proves isolation when the turn really ran: a CLI that fails to
start produces no output, so "the secret is not in the output" would pass
vacuously. `run_real_turn` therefore fails the test unless the turn ends in
`Completed`, and skips it when the adapter is not available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from aigora.adapters.base import Adapter, AdapterEvent, Completed, Delta, TurnRequest
from aigora.config import ParticipantConfig


@dataclass(frozen=True)
class RealTurnResult:
    text: str  # the `Completed` text
    streamed: str  # all `Delta`s joined
    events: list[AdapterEvent] = field(default_factory=list)


async def run_real_turn(
    adapter: Adapter,
    participant: ParticipantConfig,
    prompt: str,
    workspace: Path,
    timeout_seconds: float = 300,
) -> RealTurnResult:
    availability = await adapter.check_availability(participant)
    if not availability.available:
        pytest.skip(f"{participant.adapter} not available: {availability.reason}")
    request = TurnRequest(
        participant=participant,
        prompt=prompt,
        workspace=workspace,
        timeout_seconds=timeout_seconds,
    )
    events = [event async for event in adapter.run_turn(request)]
    final = events[-1] if events else None
    if not isinstance(final, Completed):
        pytest.fail(f"the turn did not end in Completed: {final!r}")
    streamed = "".join(e.text for e in events if isinstance(e, Delta))
    return RealTurnResult(text=final.text, streamed=streamed, events=events)


def assert_canary_not_leaked(secret: str, result: RealTurnResult) -> None:
    assert secret not in result.text, "the canary secret leaked into the final text"
    assert secret not in result.streamed, "the canary secret leaked into the streamed text"
