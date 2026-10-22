"""Interjections (插話) and stop (停止) through the WebSocket API."""

from __future__ import annotations

import asyncio
import json

from conftest import fake_participant

from aigora.api.messages import DiscussionSettings
from aigora.config import ParticipantConfig
from aigora.discussion.engine import DiscussionEngine
from aigora.discussion.modes import get_mode
from aigora.discussion.orders import get_speaking_order
from aigora.discussion.store import DiscussionStore


def consensus(*ids: str, **settings) -> dict:
    return {"mode": "consensus", "participant_ids": list(ids), "judge": "stance_vote", **settings}


def of_type(messages: list[dict], type_: str) -> list[dict]:
    return [m for m in messages if m["type"] == type_]


def receive_until(ws, received: list[dict], predicate) -> dict:
    """Receive (and keep) messages until one matches `predicate`; returns it."""
    while True:
        msg = ws.receive_json()
        received.append(msg)
        if predicate(msg):
            return msg
        assert msg["type"] not in ("discussion_finished", "error"), msg


def finished(msg: dict) -> bool:
    return msg["type"] in ("discussion_finished", "error")


def turn_texts(messages: list[dict], round_: int, purpose: str = "turn") -> dict[str, str]:
    return {
        m["participant_id"]: m["text"]
        for m in of_type(messages, "turn_completed")
        if m["round"] == round_ and m["purpose"] == purpose
    }


def test_an_interjection_is_queued_for_the_next_round_and_reaches_every_participant_from_then_on(
    client, write_participants, data_dir
):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, delay_seconds=0.3)
        + fake_participant("echo-1", "Echo One", stream=False, echo_prompt=True, delay_seconds=0.3)
        + fake_participant("echo-2", "Echo Two", stream=False, echo_prompt=True, delay_seconds=0.3)
    )
    received: list[dict] = []
    with client.websocket_connect("/ws/discussion") as ws:
        ws.send_json(
            {
                "type": "start",
                "question": "Q?",
                "settings": consensus("fake-a", "echo-1", "echo-2", max_rounds=3),
            }
        )
        receive_until(ws, received, lambda m: m["type"] == "turn_started" and m["round"] == 1)
        ws.send_json({"type": "interject", "text": "Please consider cost too."})
        queued = receive_until(ws, received, lambda m: m["type"] == "interjection_queued")
        receive_until(ws, received, finished)

    assert queued["text"] == "Please consider cost too."
    assert queued["applies_to_round"] == 2

    # Round 1 was already running: its prompts do not carry the interjection.
    for text in turn_texts(received, 1).values():
        assert "Please consider cost too." not in text
    # Every participant sees it from round 2 on.
    for round_ in (2, 3):
        texts = turn_texts(received, round_)
        for pid in ("echo-1", "echo-2"):
            assert "Please consider cost too." in texts[pid]

    assert received[-1]["type"] == "discussion_finished"
    record = json.loads(
        (data_dir / f"{received[-1]['discussion_id']}.json").read_text(encoding="utf-8")
    )
    [interjection] = record["interjections"]
    assert interjection["text"] == "Please consider cost too."
    assert interjection["applies_to_round"] == 2
    assert interjection["at"]


def test_stop_cancels_the_running_turns_and_ends_the_discussion_as_stopped_with_the_record_saved(
    client, write_participants, data_dir, tmp_path
):
    cancel_log = tmp_path / "cancelled.log"
    write_participants(
        fake_participant("quick", "Quick", stream=False)
        + fake_participant("slow-a", "Slow A", delay_seconds=30, cancel_log=cancel_log.as_posix())
        + fake_participant("slow-b", "Slow B", delay_seconds=30, cancel_log=cancel_log.as_posix())
    )
    received: list[dict] = []
    with client.websocket_connect("/ws/discussion") as ws:
        ws.send_json(
            {"type": "start", "question": "Q?", "settings": consensus("quick", "slow-a", "slow-b")}
        )
        receive_until(
            ws, received, lambda m: m["type"] == "turn_completed" and m["participant_id"] == "quick"
        )
        ws.send_json({"type": "stop"})
        receive_until(ws, received, finished)

    end = received[-1]
    assert end["type"] == "discussion_finished"
    assert end["outcome"] == "stopped"
    # The running turns were cancelled (the adapter saw it) and are reported as ended.
    assert sorted(cancel_log.read_text(encoding="utf-8").split()) == ["slow-a", "slow-b"]
    failed = of_type(received, "turn_failed")
    assert sorted((f["round"], f["participant_id"]) for f in failed) == [
        (1, "slow-a"),
        (1, "slow-b"),
    ]
    assert not of_type(received, "round_completed")

    record = json.loads((data_dir / f"{end['discussion_id']}.json").read_text(encoding="utf-8"))
    assert record["outcome"] == "stopped"
    assert record["finished_at"]
    [round_1] = record["rounds"]
    assert [(t["participant_id"], t["status"]) for t in round_1["turns"]] == [
        ("quick", "ok"),
        ("slow-a", "failed"),
        ("slow-b", "failed"),
    ]
    assert round_1["turns"][1]["error"]


def test_stop_during_the_moderators_draft_cancels_it_and_keeps_the_finished_turns(
    client, write_participants, data_dir, tmp_path
):
    cancel_log = tmp_path / "cancelled.log"
    # The moderator's short turn streams quickly enough; its long draft would take minutes.
    write_participants(
        fake_participant(
            "mod",
            "Mod",
            chunk_chars=1,
            chunk_delay_seconds=0.3,
            replies=["ok"],
            drafts=["a very slow draft " * 20],
            cancel_log=cancel_log.as_posix(),
        )
        + fake_participant("other", "Other", stream=False)
    )
    received: list[dict] = []
    with client.websocket_connect("/ws/discussion") as ws:
        ws.send_json({"type": "start", "question": "Q?", "settings": consensus("mod", "other")})
        receive_until(ws, received, lambda m: m["type"] == "turn_delta" and m["purpose"] == "draft")
        ws.send_json({"type": "stop"})
        receive_until(ws, received, finished)

    assert received[-1]["outcome"] == "stopped"
    assert cancel_log.read_text(encoding="utf-8").split() == ["mod"]
    assert [(f["participant_id"], f["purpose"]) for f in of_type(received, "turn_failed")] == [
        ("mod", "draft")
    ]
    assert not of_type(received, "draft_created")
    record = json.loads(
        (data_dir / f"{received[-1]['discussion_id']}.json").read_text(encoding="utf-8")
    )
    [round_1] = record["rounds"]
    assert [(t["participant_id"], t["status"]) for t in round_1["turns"]] == [
        ("mod", "ok"),
        ("other", "ok"),
    ]
    assert round_1["draft"] is None


async def test_an_interjection_after_stop_is_rejected_with_an_error(tmp_path):
    # Engine level: `stop()` then `interject()` with nothing in between, before the stop
    # has finished the discussion (over the socket this ordering is a race).
    participants = [
        ParticipantConfig(id=pid, display_name=pid, adapter="fake", options={"delay_seconds": 30})
        for pid in ("slow-a", "slow-b")
    ]
    settings = DiscussionSettings(
        mode="consensus",
        participant_ids=["slow-a", "slow-b"],
        judge="stance_vote",
        moderator_id="slow-a",
        speaking_order="parallel",
        max_rounds=3,
        turn_timeout_seconds=60,
        jev_threshold=0.8,
    )
    sent: list[dict] = []

    async def send(message: dict) -> None:
        sent.append(message)

    engine = DiscussionEngine(
        question="Q?",
        settings=settings,
        participants=participants,
        mode=get_mode("consensus"),
        order=get_speaking_order("parallel"),
        store=DiscussionStore(tmp_path),
        send=send,
    )
    run = asyncio.create_task(engine.run())
    while not any(m["type"] == "turn_started" for m in sent):
        await asyncio.sleep(0.01)

    await engine.stop()
    await engine.interject("Too late")
    record = await run

    assert of_type(sent, "interjection_queued") == []
    [error] = of_type(sent, "error")
    assert "停止" in error["message"]
    assert record.interjections == []
    assert sent[-1]["type"] == "discussion_finished" and sent[-1]["outcome"] == "stopped"
