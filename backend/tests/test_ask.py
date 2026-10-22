"""Ask (提問) through the WebSocket API with Fake Adapter participants."""

from __future__ import annotations

import json
import time

from conftest import fake_participant, run_discussion


def test_ask_streams_one_round_from_every_participant_and_finishes(client, write_participants):
    write_participants(
        fake_participant(
            "fake-a", "Fake A", replies=["Answer from A"], chunk_chars=4, chunk_delay_seconds=0
        )
        + fake_participant(
            "fake-b", "Fake B", replies=["Answer from B"], chunk_chars=4, chunk_delay_seconds=0
        )
    )

    messages = run_discussion(
        client, "Tabs or spaces?", {"mode": "ask", "participant_ids": ["fake-a", "fake-b"]}
    )

    types = [m["type"] for m in messages]
    assert types[:2] == ["discussion_started", "round_started"]
    assert types[-2:] == ["round_completed", "discussion_finished"]
    assert [m["seq"] for m in messages] == list(range(1, len(messages) + 1))
    assert len({m["discussion_id"] for m in messages}) == 1

    started = messages[0]
    assert started["question"] == "Tabs or spaces?"
    assert started["settings"]["mode"] == "ask"
    assert started["settings"]["participant_ids"] == ["fake-a", "fake-b"]
    assert [p["display_name"] for p in started["participants"]] == ["Fake A", "Fake B"]

    for pid, text in (("fake-a", "Answer from A"), ("fake-b", "Answer from B")):
        own = [m for m in messages if m.get("participant_id") == pid]
        assert own[0]["type"] == "turn_started" and own[0]["round"] == 1
        deltas = [m for m in own if m["type"] == "turn_delta"]
        assert len(deltas) > 1
        assert "".join(d["text"] for d in deltas) == text
        assert own[-1]["type"] == "turn_completed"
        assert own[-1]["text"] == text

    finished = messages[-1]
    assert finished["outcome"] == "completed"
    assert finished["result"]["kind"] == "answers"
    assert finished["result"]["answers"] == [
        {"participant_id": "fake-a", "status": "ok", "text": "Answer from A"},
        {"participant_id": "fake-b", "status": "ok", "text": "Answer from B"},
    ]


def test_participants_in_one_batch_answer_in_parallel(client, write_participants):
    write_participants(
        fake_participant("slow-a", "Slow A", stream=False, delay_seconds=0.6)
        + fake_participant("slow-b", "Slow B", stream=False, delay_seconds=0.6)
        + fake_participant("slow-c", "Slow C", stream=False, delay_seconds=0.6)
    )

    started = time.monotonic()
    messages = run_discussion(
        client, "Q?", {"mode": "ask", "participant_ids": ["slow-a", "slow-b", "slow-c"]}
    )
    elapsed = time.monotonic() - started

    assert messages[-1]["outcome"] == "completed"
    assert 0.6 <= elapsed < 1.2  # about the slowest one (0.6 s), not the sum (1.8 s)
    types = [m["type"] for m in messages]
    # Everyone starts before anyone finishes.
    assert max(i for i, t in enumerate(types) if t == "turn_started") < types.index(
        "turn_completed"
    )


def test_prompt_names_the_participants_and_asks_for_the_question_language_and_cited_urls(
    client, write_participants
):
    write_participants(
        fake_participant("echo", "Echo Bot", stream=False, echo_prompt=True)
        + fake_participant("other", "Other Bot", stream=False)
    )

    messages = run_discussion(
        client, "貓為什麼會呼嚕？", {"mode": "ask", "participant_ids": ["echo", "other"]}
    )

    prompt = next(
        m["text"]
        for m in messages
        if m["type"] == "turn_completed" and m["participant_id"] == "echo"
    )
    assert "貓為什麼會呼嚕？" in prompt
    assert "You are Echo Bot" in prompt
    assert "Other Bot" in prompt
    assert "same language as the question" in prompt
    assert "URL" in prompt


def test_finished_ask_is_saved_as_a_discussion_record(client, write_participants, data_dir):
    write_participants(
        fake_participant("fake-a", "Fake A", replies=["Answer from A"], web_access=False)
        + fake_participant("fake-b", "Fake B", replies=["Answer from B"], stream=False)
    )

    messages = run_discussion(
        client, "Tabs or spaces?", {"mode": "ask", "participant_ids": ["fake-a", "fake-b"]}
    )

    discussion_id = messages[0]["discussion_id"]
    files = list(data_dir.glob("*.json"))
    assert [f.name for f in files] == [f"{discussion_id}.json"]
    record = json.loads(files[0].read_text(encoding="utf-8"))

    assert set(record) == {
        "schema_version",
        "id",
        "question",
        "created_at",
        "finished_at",
        "settings",
        "participants",
        "derived_from",
        "rounds",
        "interjections",
        "removed_participants",
        "moderator_changes",
        "outcome",
        "result",
    }
    assert record["schema_version"] == 2
    assert record["id"] == discussion_id
    assert record["question"] == "Tabs or spaces?"
    assert record["created_at"] <= record["finished_at"]
    assert record["settings"] == messages[0]["settings"]
    assert record["settings"]["turn_timeout_seconds"] == 300  # filled from [defaults]
    assert record["participants"] == [
        {
            "id": "fake-a",
            "display_name": "Fake A",
            "adapter": "fake",
            "model": None,
            "avatar": "fake.png",
            "capabilities": {"web_access": False, "streaming": True},
        },
        {
            "id": "fake-b",
            "display_name": "Fake B",
            "adapter": "fake",
            "model": None,
            "avatar": "fake.png",
            "capabilities": {"web_access": True, "streaming": False},
        },
    ]
    assert record["derived_from"] is None
    assert len(record["rounds"]) == 1
    round_ = record["rounds"][0]
    assert round_["number"] == 1
    assert [(t["participant_id"], t["status"], t["text"], t["error"]) for t in round_["turns"]] == [
        ("fake-a", "ok", "Answer from A", None),
        ("fake-b", "ok", "Answer from B", None),
    ]
    for turn in round_["turns"]:
        assert turn["started_at"] <= turn["ended_at"]
    assert record["interjections"] == [] and record["removed_participants"] == []
    assert record["moderator_changes"] == []
    assert record["outcome"] == "completed"
    assert record["result"] == messages[-1]["result"]


def test_start_with_an_unknown_participant_is_rejected_with_an_error(
    client, write_participants, data_dir
):
    write_participants(fake_participant("fake-a", "Fake A"))

    messages = run_discussion(
        client, "Q?", {"mode": "ask", "participant_ids": ["fake-a", "nobody"]}
    )

    assert len(messages) == 1
    assert messages[0]["type"] == "error"
    assert messages[0]["discussion_id"] is None
    assert "nobody" in messages[0]["message"]
    assert not data_dir.exists() or not list(data_dir.iterdir())


def test_start_with_fewer_than_two_participants_is_rejected_with_an_error(
    client, write_participants, data_dir
):
    write_participants(fake_participant("fake-a", "Fake A"))

    for ids in (["fake-a"],):
        messages = run_discussion(client, "Q?", {"mode": "ask", "participant_ids": ids})

        assert [m["type"] for m in messages] == ["error"]
        assert "至少 2 個參與者" in messages[0]["message"]
    assert not data_dir.exists() or not list(data_dir.iterdir())


def test_participant_list_shows_enabled_participants_with_capabilities_and_availability(
    client, write_participants
):
    write_participants(
        fake_participant("fake-a", "Fake A", web_access=False)
        + fake_participant("fake-b", "Fake B", available=False, unavailable_reason="not logged in")
        + fake_participant("hidden", "Hidden").replace(
            'adapter = "fake"', 'adapter = "fake"\nenabled = false'
        )
    )

    response = client.get("/api/participants")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "fake-a",
            "display_name": "Fake A",
            "adapter": "fake",
            "model": None,
            "avatar": "fake.png",
            "capabilities": {"web_access": False, "streaming": True},
            "available": True,
            "unavailable_reason": None,
            "models": [],
            "free_text_model": False,
            "models_error": None,
        },
        {
            "id": "fake-b",
            "display_name": "Fake B",
            "adapter": "fake",
            "model": None,
            "avatar": "fake.png",
            "capabilities": {"web_access": True, "streaming": True},
            "available": False,
            "unavailable_reason": "not logged in",
            "models": [],
            "free_text_model": False,
            "models_error": None,
        },
    ]
