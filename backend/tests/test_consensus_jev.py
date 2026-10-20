"""Consensus discussion with judge B (jev: Jev 判斷 + 反問確認) through the WebSocket API.

Jev is replaced by a fake client with fixed probabilities (spec "Testing Decisions");
the participants are Fake Adapter participants."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest

from aigora.discussion import judges
from aigora.jev_client import JevError
from conftest import fake_participant, run_discussion

KEY = "sk-test-secret-jev"


def consensus_b(*ids: str, **settings) -> dict:
    return {"mode": "consensus", "participant_ids": list(ids), "judge": "jev", **settings}


def of_type(messages: list[dict], type_: str) -> list[dict]:
    return [m for m in messages if m["type"] == type_]


def calls(messages: list[dict], purpose: str) -> list[tuple[int, str]]:
    return [(m["round"], m["participant_id"]) for m in of_type(messages, "turn_started") if m["purpose"] == purpose]


def saved_record(data_dir, messages: list[dict]) -> dict:
    return json.loads((data_dir / f"{messages[0]['discussion_id']}.json").read_text(encoding="utf-8"))


class FakeJev:
    """Returns the given probabilities, one per call (the last repeats); `None` raises JevError."""

    def __init__(self, probabilities: list[float | None]):
        self.probabilities = probabilities
        self.transcripts: list[Mapping[str, Any]] = []

    async def consensus_probability(self, transcript: Mapping[str, Any]) -> float:
        self.transcripts.append(transcript)
        value = self.probabilities[min(len(self.transcripts), len(self.probabilities)) - 1]
        if value is None:
            raise JevError("fake: Jev is down")
        return value


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text(f"TYPESAFE_API_KEY={KEY}\n", encoding="utf-8")
    monkeypatch.setenv("AIGORA_ENV_FILE", str(path))
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    return path


@pytest.fixture
def fake_jev(env_file, monkeypatch):
    """Install a fake Jev client; call with the probabilities to return."""
    created: list[FakeJev] = []
    keys: list[str] = []

    def install(*probabilities: float | None) -> FakeJev:
        jev = FakeJev(list(probabilities))
        created.append(jev)

        def create(env: Mapping[str, str]) -> FakeJev:
            keys.append(env.get("TYPESAFE_API_KEY", ""))
            return jev

        monkeypatch.setattr(judges, "create_jev_client", create)
        return jev

    install.keys = keys  # type: ignore[attr-defined]
    return install


def test_below_the_threshold_the_discussion_continues_with_the_next_round(client, write_participants, fake_jev):
    jev = fake_jev(0.3)
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False) + fake_participant("fake-b", "Fake B", stream=False)
    )

    messages = run_discussion(client, "Q?", consensus_b("fake-a", "fake-b", max_rounds=3, jev_threshold=0.8))

    results = of_type(messages, "judge_result")
    assert [(j["round"], j["judge"], j["outcome"]) for j in results] == [(2, "jev", "not_reached"), (3, "jev", "not_reached")]
    assert results[0]["detail"]["probability"] == 0.3
    assert results[0]["detail"]["threshold"] == 0.8
    assert of_type(messages, "confirmation_result") == []
    assert calls(messages, "confirmation") == []
    assert calls(messages, "draft") == [(1, "fake-a"), (2, "fake-a")]
    assert messages[-1]["outcome"] == "no_consensus"
    # Jev saw the whole discussion: the question, the turns and the drafts.
    transcript = jev.transcripts[0]
    assert transcript["question"] == "Q?"
    assert [r["number"] for r in transcript["rounds"]] == [1, 2]
    assert transcript["rounds"][0]["draft"]
    assert {t["participant"] for t in transcript["rounds"][1]["turns"]} == {"Fake A", "Fake B"}
    # The key read from .env reaches the Jev client (and only the backend).
    assert fake_jev.keys[0] == KEY
    assert KEY not in json.dumps(messages)


def test_at_the_threshold_everyone_is_asked_and_unanimous_agreement_ends_with_the_moderators_final_result(
    client, write_participants, fake_jev, data_dir
):
    fake_jev(0.8)
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, final="The final consensus text.")
        + fake_participant("fake-b", "Fake B", stream=False)
    )

    messages = run_discussion(client, "Q?", consensus_b("fake-a", "fake-b", jev_threshold=0.8))

    results = of_type(messages, "judge_result")
    assert [(j["round"], j["outcome"]) for j in results] == [(2, "confirm"), (2, "reached")]
    assert results[0]["detail"]["probability"] == 0.8
    assert sorted(calls(messages, "confirmation")) == [(2, "fake-a"), (2, "fake-b")]
    confirmations = of_type(messages, "confirmation_result")
    assert len(confirmations) == 1 and confirmations[0]["round"] == 2
    assert {a["participant_id"]: a["agree"] for a in confirmations[0]["answers"]} == {"fake-a": True, "fake-b": True}
    assert calls(messages, "final_result") == [(2, "fake-a")]
    types = [m["type"] for m in messages]
    assert types.index("confirmation_result") < types.index("discussion_finished")

    finished = messages[-1]
    assert finished["type"] == "discussion_finished"
    assert finished["outcome"] == "consensus"
    assert finished["result"] == {"kind": "consensus", "text": "The final consensus text.", "answers": None}

    record = saved_record(data_dir, messages)
    round2 = record["rounds"][1]
    assert round2["judge"] == {
        "judge": "jev", "outcome": "reached", "detail": {"stances": None, "probability": 0.8, "threshold": 0.8},
    }
    assert [(c["participant_id"], c["agree"]) for c in round2["confirmations"]] == [("fake-a", True), ("fake-b", True)]
    assert record["rounds"][0]["confirmations"] is None
    assert record["outcome"] == "consensus"
    assert record["result"]["text"] == "The final consensus text."


def test_a_disagreeing_answer_carries_its_reason_into_the_next_rounds_prompt(client, write_participants, fake_jev, data_dir):
    fake_jev(0.9, 0.1)
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False)
        + fake_participant("fake-b", "Fake B", stream=False,
                           confirmations=["No: we still differ on the price cap.\nSTANCE: DISAGREE"])
        + fake_participant("echo", "Echo", stream=False, echo_prompt=True)
    )

    messages = run_discussion(client, "Q?", consensus_b("fake-a", "fake-b", "echo", max_rounds=3))

    results = of_type(messages, "judge_result")
    assert [(j["round"], j["outcome"]) for j in results] == [(2, "confirm"), (2, "not_reached"), (3, "not_reached")]
    answers = {a["participant_id"]: a for a in of_type(messages, "confirmation_result")[0]["answers"]}
    assert answers["fake-a"]["agree"] is True
    assert answers["fake-b"]["agree"] is False
    assert "price cap" in answers["fake-b"]["reason"]
    assert "STANCE" not in answers["fake-b"]["reason"]
    # The echo participant's confirmation is its prompt, without a stance: counts as disagreeing.
    assert answers["echo"]["agree"] is False
    assert calls(messages, "final_result") == []
    # Not reached: the moderator writes the next draft and round 3 runs.
    assert (2, "fake-a") in calls(messages, "draft")
    prompt3 = next(m["text"] for m in of_type(messages, "turn_completed")
                   if m["participant_id"] == "echo" and m["purpose"] == "turn" and m["round"] == 3)
    assert "we still differ on the price cap" in prompt3
    assert messages[-1]["outcome"] == "no_consensus"

    record = saved_record(data_dir, messages)
    assert record["rounds"][1]["judge"]["outcome"] == "not_reached"
    assert {c["participant_id"]: c["agree"] for c in record["rounds"][1]["confirmations"]} == {
        "fake-a": True, "fake-b": False, "echo": False,
    }


def test_disagreeing_reasons_reach_only_the_next_round_not_later_ones(client, write_participants, fake_jev):
    fake_jev(0.9, 0.1)  # round 2: confirmation (fake-b disagrees); round 3 and later: below the threshold
    write_participants(
        fake_participant("echo", "Echo", stream=False, echo_prompt=True)
        + fake_participant("fake-b", "Fake B", stream=False,
                           confirmations=["No: we still differ on the price cap.\nSTANCE: DISAGREE"])
    )

    messages = run_discussion(client, "Q?", consensus_b("echo", "fake-b", moderator_id="echo", max_rounds=4))

    def instructions(round_: int, purpose: str) -> str:
        # Echo replies with its prompt; this call's own instructions are the last section.
        text = next(m["text"] for m in of_type(messages, "turn_completed")
                    if m["participant_id"] == "echo" and m["purpose"] == purpose and m["round"] == round_)
        return text.rsplit("## Instructions for this round", 1)[1]

    assert [(j["round"], j["outcome"]) for j in of_type(messages, "judge_result")] == [
        (2, "confirm"), (2, "not_reached"), (3, "not_reached"), (4, "not_reached"),
    ]
    assert "price cap" in instructions(2, "draft")
    assert "price cap" in instructions(3, "turn")
    # Round 3 had no confirmation: its draft and round 4 no longer carry round 2's reasons.
    assert "price cap" not in instructions(3, "draft")
    assert "price cap" not in instructions(4, "turn")


def test_when_jev_fails_the_round_counts_as_not_reached_and_the_discussion_goes_on(client, write_participants, fake_jev):
    fake_jev(None)
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False) + fake_participant("fake-b", "Fake B", stream=False)
    )

    messages = run_discussion(client, "Q?", consensus_b("fake-a", "fake-b", max_rounds=2))

    results = of_type(messages, "judge_result")
    assert [(j["round"], j["outcome"]) for j in results] == [(2, "not_reached")]
    assert results[0]["detail"]["probability"] is None
    assert messages[-1]["outcome"] == "no_consensus"


def test_judge_b_cannot_start_without_a_typesafe_key(client, write_participants, env_file):
    env_file.write_text("# no key\n", encoding="utf-8")
    write_participants(fake_participant("fake-a", "Fake A") + fake_participant("fake-b", "Fake B"))

    messages = run_discussion(client, "Q?", consensus_b("fake-a", "fake-b"))

    assert [m["type"] for m in messages] == ["error"]
    assert "TYPESAFE_API_KEY" in messages[0]["message"]


def test_with_a_key_the_options_list_judge_b_as_available_without_sending_the_key(client, write_participants, env_file):
    write_participants(fake_participant("fake-a", "Fake A") + fake_participant("fake-b", "Fake B"))

    response = client.get("/api/options")

    jev = {j["id"]: j for j in response.json()["judges"]}["jev"]
    assert jev == {"id": "jev", "name": "Jev 判斷 + 反問確認", "available": True, "unavailable_reason": None}
    assert KEY not in response.text


def test_a_moderator_failing_the_final_result_hands_over_and_the_next_one_writes_it(client, write_participants, fake_jev):
    fake_jev(0.95)
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, fail_rounds=[2], fail_purposes=["final_result"])
        + fake_participant("fake-b", "Fake B", stream=False, final="B's final result.")
    )

    messages = run_discussion(client, "Q?", consensus_b("fake-a", "fake-b"))

    assert calls(messages, "final_result") == [(2, "fake-a"), (2, "fake-b")]
    assert [(c["round"], c["participant_id"]) for c in of_type(messages, "moderator_changed")] == [(2, "fake-b")]
    assert messages[-1]["outcome"] == "consensus"
    assert messages[-1]["result"]["text"] == "B's final result."
