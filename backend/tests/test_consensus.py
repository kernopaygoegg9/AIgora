"""Consensus discussion (共識討論) with judge A (stance_vote) through the WebSocket API."""

from __future__ import annotations

import json

from conftest import fake_participant, run_discussion


def consensus(*ids: str, **settings) -> dict:
    return {"mode": "consensus", "participant_ids": list(ids), "judge": "stance_vote", **settings}


def of_type(messages: list[dict], type_: str) -> list[dict]:
    return [m for m in messages if m["type"] == type_]


def test_everyone_agreeing_on_the_draft_ends_with_that_draft_as_the_consensus(client, write_participants):
    write_participants(
        fake_participant("fake-a", "Fake A", drafts=["Draft one"], stream=False)
        + fake_participant("fake-b", "Fake B", stream=False)
    )

    messages = run_discussion(client, "Q?", consensus("fake-a", "fake-b"))

    types = [m["type"] for m in messages]
    drafts = of_type(messages, "draft_created")
    assert [(d["round"], d["text"]) for d in drafts] == [(1, "Draft one")]
    # The draft comes after round 1's turns and before round 1 completes.
    assert types.index("draft_created") < types.index("round_completed")
    # The moderator (default: first participant) wrote it in an extra call.
    draft_calls = [m for m in of_type(messages, "turn_started") if m["purpose"] == "draft"]
    assert [(c["round"], c["participant_id"]) for c in draft_calls] == [(1, "fake-a")]

    judges = of_type(messages, "judge_result")
    assert [(j["round"], j["judge"], j["outcome"]) for j in judges] == [(2, "stance_vote", "reached")]
    assert judges[0]["detail"]["stances"] == {"fake-a": "AGREE", "fake-b": "AGREE"}

    finished = messages[-1]
    assert finished["type"] == "discussion_finished"
    assert finished["outcome"] == "consensus"
    assert finished["result"] == {"kind": "consensus", "text": "Draft one", "answers": None}
    assert [m["round"] for m in of_type(messages, "round_completed")] == [1, 2]


def test_round_limit_without_consensus_ends_with_the_moderators_positions_and_disagreements(
    client, write_participants
):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, summary="A thinks X, B thinks Y; they differ on Z.")
        + fake_participant("fake-b", "Fake B", stream=False, replies=["First take", "Not yet\nSTANCE: DISAGREE"])
    )

    messages = run_discussion(client, "Q?", consensus("fake-a", "fake-b", max_rounds=3))

    assert [d["round"] for d in of_type(messages, "draft_created")] == [1, 2]
    judges = of_type(messages, "judge_result")
    assert [(j["round"], j["outcome"]) for j in judges] == [(2, "not_reached"), (3, "not_reached")]
    assert judges[0]["detail"]["stances"] == {"fake-a": "AGREE", "fake-b": "DISAGREE"}
    summary_calls = [m for m in of_type(messages, "turn_started") if m["purpose"] == "no_consensus_summary"]
    assert [(c["round"], c["participant_id"]) for c in summary_calls] == [(3, "fake-a")]
    assert not [m for m in of_type(messages, "turn_started") if m["purpose"] == "draft" and m["round"] == 3]

    finished = messages[-1]
    assert finished["type"] == "discussion_finished"
    assert finished["outcome"] == "no_consensus"
    assert finished["result"] == {
        "kind": "no_consensus", "text": "A thinks X, B thinks Y; they differ on Z.", "answers": None,
    }
    assert "3" in finished["reason"]
    assert [m["round"] for m in of_type(messages, "round_completed")] == [1, 2, 3]


def test_round_one_is_a_free_answer_and_later_rounds_ask_for_a_stance_on_the_draft(client, write_participants):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, drafts=["The shared draft text"])
        + fake_participant("echo", "Echo", stream=False, echo_prompt=True)
    )

    messages = run_discussion(client, "Q?", consensus("fake-a", "echo", max_rounds=2))

    prompts = {
        m["round"]: m["text"]
        for m in of_type(messages, "turn_completed")
        if m["participant_id"] == "echo" and m["purpose"] == "turn"
    }
    assert "STANCE" not in prompts[1]
    assert "The shared draft text" in prompts[2]
    assert "STANCE: AGREE" in prompts[2] and "STANCE: DISAGREE" in prompts[2]
    assert "did not end with a valid stance" not in prompts[2]


def test_an_unparseable_stance_counts_as_disagree_and_the_next_round_reminds_that_participant(
    client, write_participants
):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False)
        + fake_participant("echo", "Echo", stream=False, echo_prompt=True)
    )

    messages = run_discussion(client, "Q?", consensus("fake-a", "echo", max_rounds=3))

    judges = of_type(messages, "judge_result")
    assert judges[0]["round"] == 2 and judges[0]["outcome"] == "not_reached"
    assert judges[0]["detail"]["stances"] == {"fake-a": "AGREE", "echo": None}
    prompts = {
        (m["round"], m["participant_id"]): m["text"]
        for m in of_type(messages, "turn_completed")
        if m["participant_id"] == "echo" and m["purpose"] == "turn"
    }
    assert "did not end with a valid stance" in prompts[(3, "echo")]
    assert messages[-1]["outcome"] == "no_consensus"


def test_the_moderator_speaks_every_round_and_its_own_stance_counts(client, write_participants):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False)
        + fake_participant("fake-b", "Fake B", stream=False, replies=["First", "Mine needs work\nSTANCE: DISAGREE",
                                                                         "Fine now\nSTANCE: AGREE"],
                           drafts=["B draft 1", "B draft 2"])
    )

    messages = run_discussion(client, "Q?", consensus("fake-a", "fake-b", moderator_id="fake-b"))

    turns = [(m["round"], m["participant_id"]) for m in of_type(messages, "turn_started") if m["purpose"] == "turn"]
    assert (1, "fake-b") in turns and (2, "fake-b") in turns
    drafts = [(m["round"], m["participant_id"]) for m in of_type(messages, "turn_started") if m["purpose"] == "draft"]
    assert drafts == [(1, "fake-b"), (2, "fake-b")]
    judges = of_type(messages, "judge_result")
    assert [(j["round"], j["outcome"]) for j in judges] == [(2, "not_reached"), (3, "reached")]
    assert judges[0]["detail"]["stances"] == {"fake-a": "AGREE", "fake-b": "DISAGREE"}
    assert messages[-1]["outcome"] == "consensus"
    assert messages[-1]["result"]["text"] == "B draft 2"


def test_the_consensus_record_keeps_each_rounds_draft_and_judge_result(client, write_participants, data_dir):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, drafts=["Draft one"])
        + fake_participant("fake-b", "Fake B", stream=False)
    )

    messages = run_discussion(client, "Q?", consensus("fake-a", "fake-b"))

    record = json.loads((data_dir / f"{messages[0]['discussion_id']}.json").read_text(encoding="utf-8"))
    assert record["settings"]["mode"] == "consensus"
    assert record["settings"]["moderator_id"] == "fake-a"
    assert [r["draft"] for r in record["rounds"]] == ["Draft one", None]
    assert record["rounds"][0]["judge"] is None
    assert record["rounds"][1]["judge"] == {
        "judge": "stance_vote", "outcome": "reached",
        "detail": {"stances": {"fake-a": "AGREE", "fake-b": "AGREE"}, "probability": None, "threshold": None},
    }
    assert record["outcome"] == "consensus"
    assert record["result"] == {"kind": "consensus", "text": "Draft one", "answers": None}


def test_a_judge_that_is_not_available_is_rejected(client, write_participants, tmp_path, monkeypatch):
    # Judge B without a TypeSafe key (see test_consensus_jev.py for judge B itself).
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("AIGORA_ENV_FILE", str(env_file))
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    write_participants(fake_participant("fake-a", "Fake A") + fake_participant("fake-b", "Fake B"))

    messages = run_discussion(client, "Q?", {"mode": "consensus", "participant_ids": ["fake-a", "fake-b"],
                                             "judge": "jev"})

    assert [m["type"] for m in messages] == ["error"]
    assert "jev" in messages[0]["message"]
