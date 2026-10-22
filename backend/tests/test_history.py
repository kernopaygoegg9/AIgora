"""History (歷史清單): GET /api/discussions and GET /api/discussions/{id} over the discussion store."""

from __future__ import annotations

from conftest import fake_participant, run_discussion

from aigora.api.messages import DiscussionSettings
from aigora.discussion.store import DiscussionStore
from aigora.record import DiscussionRecord

ASK = {"mode": "ask", "participant_ids": ["fake-a", "fake-b"]}


def _participants(write_participants):
    write_participants(
        fake_participant("fake-a", "Fake A", replies=["Answer from A"], chunk_delay_seconds=0)
        + fake_participant("fake-b", "Fake B", replies=["Answer from B"], chunk_delay_seconds=0)
    )


def test_a_finished_ask_is_listed_with_question_mode_start_time_and_outcome(
    client, write_participants
):
    _participants(write_participants)
    messages = run_discussion(client, "Tabs or spaces?", ASK)
    discussion_id = messages[0]["discussion_id"]

    response = client.get("/api/discussions")

    assert response.status_code == 200
    [summary] = response.json()
    assert summary["id"] == discussion_id
    assert summary["question"] == "Tabs or spaces?"
    assert summary["mode"] == "ask"
    assert summary["outcome"] == "completed"
    assert summary["created_at"].startswith("20")


def _in_progress_record(discussion_id: str, created_at: str, question: str) -> DiscussionRecord:
    return DiscussionRecord(
        id=discussion_id,
        question=question,
        created_at=created_at,
        settings=DiscussionSettings(
            mode="consensus",
            participant_ids=["fake-a", "fake-b"],
            judge="stance_vote",
            moderator_id="fake-a",
            speaking_order="parallel",
            max_rounds=5,
            turn_timeout_seconds=300,
            jev_threshold=0.8,
        ),
        participants=[],
    )


def test_list_is_newest_first_and_includes_discussions_still_in_progress(
    client, write_participants, data_dir
):
    _participants(write_participants)
    finished_id = run_discussion(client, "Finished ask", ASK)[0]["discussion_id"]
    store = DiscussionStore(data_dir)
    store.save(_in_progress_record("20000101-000000-aaaaaa", "2000-01-01T00:00:00+00:00", "Oldest"))
    store.save(
        _in_progress_record("29990101-000000-bbbbbb", "2999-01-01T00:00:00+00:00", "Still running")
    )

    summaries = client.get("/api/discussions").json()

    assert [s["question"] for s in summaries] == ["Still running", "Finished ask", "Oldest"]
    assert summaries[0]["outcome"] is None
    assert summaries[0]["mode"] == "consensus"
    assert summaries[1]["id"] == finished_id


def test_one_discussion_returns_the_full_record(client, write_participants):
    _participants(write_participants)
    discussion_id = run_discussion(client, "Tabs or spaces?", ASK)[0]["discussion_id"]

    response = client.get(f"/api/discussions/{discussion_id}")

    assert response.status_code == 200
    record = response.json()
    assert record["schema_version"] == 2
    assert record["id"] == discussion_id
    assert record["question"] == "Tabs or spaces?"
    assert record["settings"]["participant_ids"] == ["fake-a", "fake-b"]
    assert [p["display_name"] for p in record["participants"]] == ["Fake A", "Fake B"]
    assert [[t["text"] for t in r["turns"]] for r in record["rounds"]] == [
        ["Answer from A", "Answer from B"]
    ]
    assert record["outcome"] == "completed"
    assert record["result"]["kind"] == "answers"
    assert record["finished_at"] is not None
    assert {
        "interjections",
        "removed_participants",
        "moderator_changes",
        "derived_from",
    } <= record.keys()


def test_unknown_discussion_is_404(client):
    assert client.get("/api/discussions/20990101-000000-abcdef").status_code == 404
    assert client.get("/api/discussions/..%2F..%2Fparticipants").status_code == 404
