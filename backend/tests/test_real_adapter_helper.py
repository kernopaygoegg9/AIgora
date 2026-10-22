"""The shared real-Adapter test helper, exercised with the Fake Adapter (not `real_ai`)."""

import pytest
from real_adapter import RealTurnResult, assert_canary_not_leaked, run_real_turn

from aigora.adapters.base import get_adapter
from aigora.config import ParticipantConfig


def participant(**options) -> ParticipantConfig:
    options.setdefault("chunk_delay_seconds", 0)
    return ParticipantConfig(id="fake-a", display_name="Fake A", adapter="fake", options=options)


async def test_a_completed_turn_returns_the_final_and_streamed_text(tmp_path):
    p = participant(replies=["hello streaming world"], chunk_chars=5)

    result = await run_real_turn(get_adapter("fake"), p, "Q?", tmp_path)

    assert result.text == "hello streaming world"
    assert result.streamed == "hello streaming world"


async def test_a_turn_that_ends_in_failed_fails_the_test(tmp_path):
    p = participant(fail_rounds=[1], fail_kind="crashed", fail_reason="CLI did not start")

    with pytest.raises(pytest.fail.Exception, match="CLI did not start"):
        await run_real_turn(get_adapter("fake"), p, "Q?", tmp_path)


async def test_an_unavailable_adapter_skips_the_test(tmp_path):
    p = participant(available=False, unavailable_reason="not logged in")

    with pytest.raises(pytest.skip.Exception, match="not logged in"):
        await run_real_turn(get_adapter("fake"), p, "Q?", tmp_path)


async def test_a_canary_cannot_pass_when_the_cli_fails_without_output(tmp_path):
    # The old gemini canary passed here: no output means no leaked secret.
    p = participant(fail_rounds=[1], fail_kind="not_available", stream=False)

    with pytest.raises(pytest.fail.Exception):
        result = await run_real_turn(get_adapter("fake"), p, "read the canary", tmp_path)
        assert_canary_not_leaked("SECRET", result)


def test_the_canary_check_looks_at_the_final_text():
    with pytest.raises(AssertionError):
        assert_canary_not_leaked("SECRET", RealTurnResult(text="it is SECRET", streamed=""))


def test_the_canary_check_looks_at_the_streamed_text():
    with pytest.raises(AssertionError):
        assert_canary_not_leaked("SECRET", RealTurnResult(text="", streamed="it is SECRET"))


def test_the_canary_check_passes_when_the_secret_appears_nowhere():
    assert_canary_not_leaked("SECRET", RealTurnResult(text="I cannot", streamed="I cannot"))
