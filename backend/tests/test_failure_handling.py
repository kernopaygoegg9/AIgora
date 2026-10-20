"""Failure handling (失敗處理) through the WebSocket API: failed / timed-out turns,
removal after 2 failed rounds in a row, too few participants, moderator handoff."""

from __future__ import annotations

import json

from conftest import fake_participant, run_discussion


def consensus(*ids: str, **settings) -> dict:
    return {"mode": "consensus", "participant_ids": list(ids), "judge": "stance_vote", **settings}


def of_type(messages: list[dict], type_: str) -> list[dict]:
    return [m for m in messages if m["type"] == type_]


def saved_record(data_dir, messages: list[dict]) -> dict:
    discussion_id = messages[0]["discussion_id"]
    return json.loads((data_dir / f"{discussion_id}.json").read_text(encoding="utf-8"))


def test_a_turn_over_the_timeout_fails_as_timeout_and_the_others_still_answer(client, write_participants):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False)
        + fake_participant("fake-b", "Fake B", stream=False)
        + fake_participant("fake-slow", "Fake Slow", stream=False, delay_seconds=30)
    )

    messages = run_discussion(
        client, "Q?", {"mode": "ask", "participant_ids": ["fake-a", "fake-b", "fake-slow"], "turn_timeout_seconds": 0.5}
    )

    failed = of_type(messages, "turn_failed")
    assert [(f["participant_id"], f["kind"]) for f in failed] == [("fake-slow", "timeout")]
    assert "0.5" in failed[0]["reason"]
    assert sorted(c["participant_id"] for c in of_type(messages, "turn_completed")) == ["fake-a", "fake-b"]
    finished = messages[-1]
    assert finished["outcome"] == "completed"
    statuses = {a["participant_id"]: a["status"] for a in finished["result"]["answers"]}
    assert statuses == {"fake-a": "ok", "fake-b": "ok", "fake-slow": "timeout"}


def test_an_adapter_failure_is_reported_with_its_reason_and_kind(client, write_participants):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False)
        + fake_participant(
            "fake-b", "Fake B", stream=False, fail_rounds=[1], fail_kind="quota", fail_reason="out of quota"
        )
    )

    messages = run_discussion(client, "Q?", {"mode": "ask", "participant_ids": ["fake-a", "fake-b"]})

    failed = of_type(messages, "turn_failed")
    assert [(f["participant_id"], f["kind"], f["reason"]) for f in failed] == [("fake-b", "quota", "out of quota")]
    assert of_type(messages, "participant_removed") == []


def test_failing_two_rounds_in_a_row_removes_the_participant_and_the_others_continue(
    client, write_participants, data_dir
):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, drafts=["Draft one"])
        + fake_participant("fake-b", "Fake B", stream=False)
        + fake_participant("fake-c", "Fake C", stream=False, fail_rounds=[1, 2], fail_reason="c is broken")
    )

    messages = run_discussion(client, "Q?", consensus("fake-a", "fake-b", "fake-c"))

    removed = of_type(messages, "participant_removed")
    assert [(r["participant_id"], r["round"]) for r in removed] == [("fake-c", 2)]
    assert "c is broken" in removed[0]["reason"]
    types = [m["type"] for m in messages]
    # Removed right after round 2's turns, before the judge looks at the round.
    assert types.index("participant_removed") < types.index("judge_result")
    judge = of_type(messages, "judge_result")[0]
    assert judge["detail"]["stances"] == {"fake-a": "AGREE", "fake-b": "AGREE"}
    assert messages[-1]["outcome"] == "consensus"

    record = saved_record(data_dir, messages)
    assert [(r["participant_id"], r["round"]) for r in record["removed_participants"]] == [("fake-c", 2)]
    assert record["removed_participants"][0]["reason"] == removed[0]["reason"]
    assert record["moderator_changes"] == []


def test_a_successful_round_in_between_resets_the_failure_count(client, write_participants, data_dir):
    disagree = ["First take", "Not yet\nSTANCE: DISAGREE"]
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, replies=disagree)
        + fake_participant("fake-b", "Fake B", stream=False, replies=disagree)
        + fake_participant("fake-c", "Fake C", stream=False, fail_rounds=[1, 3])
    )

    messages = run_discussion(client, "Q?", consensus("fake-a", "fake-b", "fake-c", max_rounds=4))

    assert [f["round"] for f in of_type(messages, "turn_failed")] == [1, 3]
    assert of_type(messages, "participant_removed") == []
    assert messages[-1]["outcome"] == "no_consensus"
    assert saved_record(data_dir, messages)["removed_participants"] == []


def test_fewer_than_two_participants_left_ends_the_discussion_as_insufficient(client, write_participants, data_dir):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False)
        + fake_participant("fake-b", "Fake B", stream=False, fail_rounds=[1, 2])
    )

    messages = run_discussion(client, "Q?", consensus("fake-a", "fake-b"))

    assert [r["participant_id"] for r in of_type(messages, "participant_removed")] == ["fake-b"]
    # No judge, no draft for round 2: the round completes (saved) and the discussion ends.
    assert [j["round"] for j in of_type(messages, "judge_result")] == []
    assert [d["round"] for d in of_type(messages, "draft_created")] == [1]
    assert [m["type"] for m in messages[-2:]] == ["round_completed", "discussion_finished"]
    finished = messages[-1]
    assert finished["outcome"] == "insufficient_participants"
    assert finished["result"] is None
    assert "少於 2" in finished["reason"]

    record = saved_record(data_dir, messages)
    assert record["outcome"] == "insufficient_participants"
    assert [r["participant_id"] for r in record["removed_participants"]] == ["fake-b"]
    assert len(record["rounds"]) == 2


def draft_calls(messages: list[dict]) -> list[tuple[int, str]]:
    return [(m["round"], m["participant_id"]) for m in of_type(messages, "turn_started") if m["purpose"] == "draft"]


def test_a_moderator_whose_turn_fails_hands_over_to_the_next_active_participant(
    client, write_participants, data_dir
):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, drafts=["A's draft"])
        + fake_participant("fake-b", "Fake B", stream=False, drafts=["B's draft"], fail_rounds=[1])
        + fake_participant("fake-c", "Fake C", stream=False, drafts=["C's draft"])
    )

    messages = run_discussion(client, "Q?", consensus("fake-a", "fake-b", "fake-c", moderator_id="fake-b"))

    types = [m["type"] for m in messages]
    changes = of_type(messages, "moderator_changed")
    # One failed turn is enough to hand over (no removal yet); it happens before the draft.
    assert [(c["participant_id"], c["round"]) for c in changes] == [("fake-c", 1)]
    assert of_type(messages, "participant_removed") == []
    assert types.index("turn_failed") < types.index("moderator_changed") < types.index("draft_created")
    assert draft_calls(messages) == [(1, "fake-c")]
    assert messages[-1]["outcome"] == "consensus"
    assert messages[-1]["result"]["text"] == "C's draft"

    record = saved_record(data_dir, messages)
    assert record["moderator_changes"] == [{"round": 1, "participant_id": "fake-c"}]


def test_a_failing_moderator_hands_over_once_and_is_later_removed(client, write_participants, data_dir):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, fail_rounds=[1, 2], fail_purposes=["turn"])
        + fake_participant(
            "fake-b", "Fake B", stream=False, drafts=["B's draft"],
            replies=["First take", "Not yet\nSTANCE: DISAGREE", "Fine\nSTANCE: AGREE"],
        )
        + fake_participant("fake-c", "Fake C", stream=False)
    )

    messages = run_discussion(client, "Q?", consensus("fake-a", "fake-b", "fake-c"))

    # fake-a's round-1 turn failed: fake-b takes over at once and writes every draft;
    # removing fake-a after round 2 changes nothing more.
    changes = of_type(messages, "moderator_changed")
    assert [(c["participant_id"], c["round"]) for c in changes] == [("fake-b", 1)]
    assert [(r["participant_id"], r["round"]) for r in of_type(messages, "participant_removed")] == [("fake-a", 2)]
    assert draft_calls(messages) == [(1, "fake-b"), (2, "fake-b")]
    finished = messages[-1]
    assert finished["outcome"] == "consensus"
    assert finished["result"]["text"] == "B's draft"

    record = saved_record(data_dir, messages)
    assert record["moderator_changes"] == [{"round": 1, "participant_id": "fake-b"}]


def test_a_failed_moderator_call_hands_over_to_the_next_participant_who_retries_it(
    client, write_participants, data_dir
):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, drafts=["A's draft"])
        + fake_participant("fake-b", "Fake B", stream=False)
        + fake_participant("fake-c", "Fake C", stream=False, fail_rounds=[1], fail_purposes=["draft"])
    )

    messages = run_discussion(client, "Q?", consensus("fake-a", "fake-b", "fake-c", moderator_id="fake-c"))

    failed = of_type(messages, "turn_failed")
    assert [(f["round"], f["participant_id"], f["purpose"]) for f in failed] == [(1, "fake-c", "draft")]
    # The list wraps around: after the last participant comes the first.
    assert [(c["participant_id"], c["round"]) for c in of_type(messages, "moderator_changed")] == [("fake-a", 1)]
    assert draft_calls(messages) == [(1, "fake-c"), (1, "fake-a")]
    assert [(d["round"], d["text"]) for d in of_type(messages, "draft_created")] == [(1, "A's draft")]
    # A failed extra call is not a failed round: nobody is removed.
    assert of_type(messages, "participant_removed") == []
    assert messages[-1]["outcome"] == "consensus"
    assert messages[-1]["result"]["text"] == "A's draft"

    record = saved_record(data_dir, messages)
    assert record["moderator_changes"] == [{"round": 1, "participant_id": "fake-a"}]
    assert record["rounds"][0]["draft"] == "A's draft"


def test_every_moderator_failing_the_draft_leaves_the_round_without_one(client, write_participants):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, fail_rounds=[1], fail_purposes=["draft"])
        + fake_participant("fake-b", "Fake B", stream=False, fail_rounds=[1], fail_purposes=["draft"])
    )

    messages = run_discussion(client, "Q?", consensus("fake-a", "fake-b", max_rounds=2))

    # Each tries once; the second failure still hands over, but nobody retries again.
    assert draft_calls(messages) == [(1, "fake-a"), (1, "fake-b")]
    assert [c["participant_id"] for c in of_type(messages, "moderator_changed")] == ["fake-b", "fake-a"]
    assert of_type(messages, "draft_created") == []
    assert messages[-1]["outcome"] == "no_consensus"
