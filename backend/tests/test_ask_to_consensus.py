"""提問轉共識討論 through the WebSocket API: `start` with `from_discussion_id`."""

from __future__ import annotations

import json

from conftest import fake_participant, run_discussion


def of_type(messages: list[dict], type_: str) -> list[dict]:
    return [m for m in messages if m["type"] == type_]


def saved_record(data_dir, discussion_id: str) -> dict:
    return json.loads((data_dir / f"{discussion_id}.json").read_text(encoding="utf-8"))


def derive(client, from_id: str, question: str = "ignored?", **settings) -> list[dict]:
    """Send `start` with `from_discussion_id` and collect messages until finished / error."""
    received: list[dict] = []
    with client.websocket_connect("/ws/discussion") as ws:
        ws.send_json(
            {
                "type": "start",
                "question": question,
                "settings": {
                    "mode": "consensus",
                    "participant_ids": ["ignored"],
                    "judge": "stance_vote",
                    **settings,
                },
                "from_discussion_id": from_id,
            }
        )
        while True:
            msg = ws.receive_json()
            received.append(msg)
            if msg["type"] in ("discussion_finished", "error"):
                break
    return received


def ask(client, *ids: str, question: str = "What is best?") -> list[dict]:
    return run_discussion(client, question, {"mode": "ask", "participant_ids": list(ids)})


def test_round_one_is_the_asks_answers_and_the_moderator_drafts_first(
    client, write_participants, data_dir
):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, replies=["A's ask answer"])
        + fake_participant("fake-b", "Fake B", stream=False, replies=["B's ask answer"])
    )
    asked = ask(client, "fake-a", "fake-b")
    ask_id = asked[0]["discussion_id"]
    # From now on a normal round-1 call would answer differently: it must not happen.
    write_participants(
        fake_participant(
            "fake-a",
            "Fake A",
            stream=False,
            drafts=["Draft one"],
            replies=["CALLED AGAIN", "ok\nSTANCE: AGREE"],
        )
        + fake_participant(
            "fake-b", "Fake B", stream=False, replies=["CALLED AGAIN", "ok\nSTANCE: AGREE"]
        )
    )

    messages = derive(client, ask_id)

    started = messages[0]
    assert started["type"] == "discussion_started"
    assert started["question"] == "What is best?"
    assert started["derived_from"] == ask_id
    assert started["settings"]["mode"] == "consensus"
    assert started["settings"]["participant_ids"] == ["fake-a", "fake-b"]
    round_one = [
        (m["participant_id"], m["text"])
        for m in of_type(messages, "turn_completed")
        if m["round"] == 1 and m["purpose"] == "turn"
    ]
    assert round_one == [("fake-a", "A's ask answer"), ("fake-b", "B's ask answer")]
    assert [(d["round"], d["text"]) for d in of_type(messages, "draft_created")] == [
        (1, "Draft one")
    ]
    finished = messages[-1]
    assert finished["type"] == "discussion_finished"
    assert finished["outcome"] == "consensus"
    assert finished["result"]["text"] == "Draft one"


def test_the_new_record_points_at_the_ask_and_the_ask_record_is_unchanged(
    client, write_participants, data_dir
):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False)
        + fake_participant("fake-b", "Fake B", stream=False)
    )
    ask_id = ask(client, "fake-a", "fake-b")[0]["discussion_id"]
    before = (data_dir / f"{ask_id}.json").read_text(encoding="utf-8")

    messages = derive(client, ask_id)

    new_id = messages[0]["discussion_id"]
    assert new_id != ask_id
    record = saved_record(data_dir, new_id)
    assert record["derived_from"] == ask_id
    assert record["settings"]["mode"] == "consensus"
    asked = saved_record(data_dir, ask_id)
    assert [
        (t["participant_id"], t["text"], t["started_at"]) for t in record["rounds"][0]["turns"]
    ] == [(t["participant_id"], t["text"], t["started_at"]) for t in asked["rounds"][0]["turns"]]
    assert record["rounds"][0]["draft"]
    assert (data_dir / f"{ask_id}.json").read_text(encoding="utf-8") == before


def test_a_failed_ask_answer_stays_failed_in_round_one(client, write_participants, data_dir):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False)
        + fake_participant("fake-b", "Fake B", stream=False)
        + fake_participant("fake-c", "Fake C", stream=False, fail_rounds=[1], fail_reason="boom")
    )
    ask_id = ask(client, "fake-a", "fake-b", "fake-c")[0]["discussion_id"]

    messages = derive(client, ask_id)

    failed = [m for m in of_type(messages, "turn_failed") if m["round"] == 1]
    assert [(f["participant_id"], f["reason"]) for f in failed] == [("fake-c", "boom")]
    assert messages[-1]["outcome"] == "consensus"


def test_an_unknown_discussion_is_an_error(client, write_participants):
    write_participants(fake_participant("fake-a", "Fake A") + fake_participant("fake-b", "Fake B"))

    messages = derive(client, "20200101-000000-abcdef")

    assert [m["type"] for m in messages] == ["error"]
    assert "20200101-000000-abcdef" in messages[0]["message"]


def test_a_discussion_that_is_not_an_ask_is_an_error(client, write_participants):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False)
        + fake_participant("fake-b", "Fake B", stream=False)
    )
    consensus_id = run_discussion(
        client,
        "Q?",
        {"mode": "consensus", "participant_ids": ["fake-a", "fake-b"], "judge": "stance_vote"},
    )[0]["discussion_id"]

    messages = derive(client, consensus_id)

    assert [m["type"] for m in messages] == ["error"]
    assert "提問" in messages[0]["message"]


def test_converting_needs_the_consensus_mode(client, write_participants):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False)
        + fake_participant("fake-b", "Fake B", stream=False)
    )
    ask_id = ask(client, "fake-a", "fake-b")[0]["discussion_id"]

    messages = derive(client, ask_id, mode="ask")

    assert [m["type"] for m in messages] == ["error"]
