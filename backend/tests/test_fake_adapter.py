"""Fake Adapter: a real adapter whose behaviour is scripted through `options`."""

import asyncio
import time
from pathlib import Path

import pytest

from aigora.adapters.base import Completed, Delta, Failed, TurnRequest, get_adapter
from aigora.config import ParticipantConfig


def participant(**options) -> ParticipantConfig:
    return ParticipantConfig(id="fake-a", display_name="Fake A", adapter="fake", options=options)


def request(p: ParticipantConfig, round: int = 1, purpose: str = "turn", prompt: str = "Q?") -> TurnRequest:
    return TurnRequest(
        participant=p,
        prompt=prompt,
        workspace=Path("."),
        timeout_seconds=5,
        round=round,
        purpose=purpose,
    )


async def run(p: ParticipantConfig, **kwargs) -> list:
    adapter = get_adapter("fake")
    return [event async for event in adapter.run_turn(request(p, **kwargs))]


def joined_deltas(events) -> str:
    return "".join(e.text for e in events if isinstance(e, Delta))


async def test_scripted_reply_per_round_with_the_last_one_repeating():
    p = participant(replies=["first", "second\nSTANCE: AGREE"], stream=False)
    assert (await run(p, round=1))[-1] == Completed("first")
    assert (await run(p, round=2))[-1] == Completed("second\nSTANCE: AGREE")
    assert (await run(p, round=5))[-1] == Completed("second\nSTANCE: AGREE")


async def test_unscripted_reply_names_the_participant_and_agrees_from_round_two():
    p = participant(stream=False)
    first = (await run(p, round=1))[-1]
    later = (await run(p, round=2))[-1]
    assert isinstance(first, Completed) and "Fake A" in first.text and "STANCE" not in first.text
    assert isinstance(later, Completed) and later.text.endswith("STANCE: AGREE")


async def test_streaming_sends_deltas_that_add_up_to_the_completed_text():
    p = participant(replies=["hello streaming world"], stream=True, chunk_chars=5, chunk_delay_seconds=0)
    events = await run(p)
    deltas = [e for e in events if isinstance(e, Delta)]
    assert [d.text for d in deltas] == ["hello", " stre", "aming", " worl", "d"]
    assert events[-1] == Completed("hello streaming world")


async def test_non_streaming_sends_only_the_completed_text():
    events = await run(participant(replies=["all at once"], stream=False))
    assert events == [Completed("all at once")]


async def test_delay_before_replying():
    p = participant(replies=["late"], stream=False, delay_seconds=0.3)
    started = time.monotonic()
    await run(p)
    assert time.monotonic() - started >= 0.3


async def test_fails_in_the_configured_rounds_with_the_configured_kind():
    p = participant(stream=False, fail_rounds=[2], fail_kind="quota", fail_reason="out of credits")
    assert isinstance((await run(p, round=1))[-1], Completed)
    assert (await run(p, round=2))[-1] == Failed("quota", "out of credits")
    assert isinstance((await run(p, round=3))[-1], Completed)


async def test_failure_after_streaming_part_of_the_reply():
    p = participant(replies=["partial reply"], fail_rounds=[1], chunk_chars=4, chunk_delay_seconds=0)
    events = await run(p)
    assert joined_deltas(events) != ""
    assert isinstance(events[-1], Failed) and events[-1].kind == "crashed"


async def test_failures_apply_only_to_normal_turns_unless_configured():
    p = participant(stream=False, fail_rounds=[1])
    assert isinstance((await run(p, purpose="draft"))[-1], Completed)
    p = participant(stream=False, fail_rounds=[1], fail_purposes=["draft"])
    assert isinstance((await run(p, purpose="draft"))[-1], Failed)
    assert isinstance((await run(p, purpose="turn"))[-1], Completed)


async def test_scripted_replies_for_extra_calls():
    p = participant(
        stream=False,
        drafts=["draft one", "draft two"],
        confirmations=["yes\nSTANCE: AGREE"],
        final="the consensus",
        summary="positions and disagreements",
    )
    assert (await run(p, round=1, purpose="draft"))[-1] == Completed("draft one")
    assert (await run(p, round=2, purpose="draft"))[-1] == Completed("draft two")
    assert (await run(p, round=2, purpose="confirmation"))[-1] == Completed("yes\nSTANCE: AGREE")
    assert (await run(p, round=3, purpose="final_result"))[-1] == Completed("the consensus")
    assert (await run(p, round=3, purpose="no_consensus_summary"))[-1] == Completed(
        "positions and disagreements"
    )


async def test_echo_prompt_replies_with_the_prompt_it_received():
    p = participant(stream=False, echo_prompt=True)
    assert (await run(p, prompt="full prompt text"))[-1] == Completed("full prompt text")


async def test_availability_is_configurable():
    adapter = get_adapter("fake")
    assert (await adapter.check_availability(participant())).available
    down = await adapter.check_availability(participant(available=False, unavailable_reason="not logged in"))
    assert not down.available and down.reason == "not logged in"


async def test_unavailable_participant_fails_its_turns_as_not_available():
    events = await run(participant(available=False, stream=False))
    assert isinstance(events[-1], Failed) and events[-1].kind == "not_available"


def test_capabilities_follow_options():
    adapter = get_adapter("fake")
    assert adapter.capabilities(participant()).streaming
    assert adapter.capabilities(participant()).web_access
    caps = adapter.capabilities(participant(stream=False, web_access=False))
    assert not caps.streaming and not caps.web_access


async def test_cancelling_a_turn_stops_it_promptly():
    p = participant(replies=["never"], stream=False, delay_seconds=30)
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(run(p), timeout=0.2)
    assert time.monotonic() - started < 2


@pytest.mark.parametrize(
    "options",
    [
        {"replies": "not a list"},
        {"fail_kind": "exploded"},
        {"fail_rounds": [0]},
        {"stream": "yes"},
        {"delay_seconds": -1},
        {"no_such_option": 1},
    ],
)
def test_invalid_options_are_rejected(options):
    with pytest.raises(ValueError):
        get_adapter("fake").validate_options(options)
