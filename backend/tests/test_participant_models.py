"""參與者與模型選擇 through the WebSocket / HTTP API: `models` overrides, extra participants
(臨時參與者) copied from a configured participant, unique display names, 提問轉共識討論
keeping them, and schema 1 records still loading."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from aigora.adapters.fake import FakeAdapter
from aigora.api.messages import DiscussionSettings, ExtraParticipant
from aigora.config import Defaults, ParticipantConfig, ParticipantsConfig
from aigora.discussion.settings import build_participants
from conftest import fake_participant, run_discussion

FIXTURES = Path(__file__).parent / "fixtures"
SCHEMA1_ID = "20260101-120000-a1b2c3"


def of_type(messages: list[dict], type_: str) -> list[dict]:
    return [m for m in messages if m["type"] == type_]


def saved_record(data_dir, messages: list[dict]) -> dict:
    discussion_id = messages[0]["discussion_id"]
    return json.loads((data_dir / f"{discussion_id}.json").read_text(encoding="utf-8"))


def ask(*ids: str, **settings) -> dict:
    return {"mode": "ask", "participant_ids": list(ids), **settings}


def consensus(*ids: str, **settings) -> dict:
    return {"mode": "consensus", "participant_ids": list(ids), "judge": "stance_vote", **settings}


def extra(pid: str, template_id: str, model: str | None = None) -> dict:
    return {"id": pid, "template_id": template_id, "model": model}


@pytest.fixture
def two_fakes(write_participants):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, drafts=["A's draft"])
        + fake_participant("fake-b", "Fake B", stream=False, drafts=["B's draft"])
    )


@pytest.fixture
def received_models(monkeypatch) -> dict[str, set[str | None]]:
    """participant id -> every `TurnRequest.participant.model` the Fake Adapter received."""
    seen: dict[str, set[str | None]] = {}
    original = FakeAdapter.run_turn

    def run_turn(self, request):
        seen.setdefault(request.participant.id, set()).add(request.participant.model)
        return original(self, request)

    monkeypatch.setattr(FakeAdapter, "run_turn", run_turn)
    return seen


# --- v1 behaviour ----------------------------------------------------------------


def test_without_the_new_fields_the_snapshot_has_empty_models_and_extras(client, two_fakes, data_dir):
    messages = run_discussion(client, "Q?", ask("fake-a", "fake-b"))

    started = messages[0]
    assert started["settings"]["models"] == {}
    assert started["settings"]["extra_participants"] == []
    assert [(p["id"], p["display_name"], p["model"]) for p in started["participants"]] == [
        ("fake-a", "Fake A", None),
        ("fake-b", "Fake B", None),
    ]
    assert messages[-1]["outcome"] == "completed"
    assert saved_record(data_dir, messages)["schema_version"] == 2


# --- models ------------------------------------------------------------------------


def test_a_model_override_reaches_the_adapter_the_snapshot_and_the_record(
    client, two_fakes, data_dir, received_models
):
    messages = run_discussion(client, "Q?", ask("fake-a", "fake-b", models={"fake-a": "  fast-model  "}))

    assert received_models == {"fake-a": {"fast-model"}, "fake-b": {None}}
    started = messages[0]
    assert started["settings"]["models"] == {"fake-a": "fast-model"}
    assert [p["model"] for p in started["participants"]] == ["fast-model", None]
    record = saved_record(data_dir, messages)
    assert record["settings"]["models"] == {"fake-a": "fast-model"}
    assert [p["model"] for p in record["participants"]] == ["fast-model", None]


# --- extra participants -------------------------------------------------------------


def test_an_extra_participant_speaks_and_is_recorded(client, two_fakes, data_dir, received_models):
    messages = run_discussion(
        client, "Q?", ask("fake-a", "x-1", extra_participants=[extra("x-1", "fake-b", "other-model")])
    )

    assert messages[-1]["outcome"] == "completed"
    assert received_models == {"fake-a": {None}, "x-1": {"other-model"}}
    assert [t["participant_id"] for t in of_type(messages, "turn_completed")] == ["fake-a", "x-1"]
    started = messages[0]
    assert started["settings"]["participant_ids"] == ["fake-a", "x-1"]
    assert started["settings"]["extra_participants"] == [extra("x-1", "fake-b", "other-model")]
    assert [(p["id"], p["display_name"], p["adapter"], p["model"]) for p in started["participants"]] == [
        ("fake-a", "Fake A", "fake", None),
        ("x-1", "Fake B", "fake", "other-model"),
    ]
    record = saved_record(data_dir, messages)
    assert record["settings"]["participant_ids"] == ["fake-a", "x-1"]
    assert [p["id"] for p in record["participants"]] == ["fake-a", "x-1"]
    assert [t["participant_id"] for t in record["rounds"][0]["turns"]] == ["fake-a", "x-1"]


def test_an_extra_participant_without_a_model_uses_its_templates_model_unless_overridden(
    client, write_participants, received_models
):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False).replace('adapter = "fake"', 'adapter = "fake"\nmodel = "base"')
        + fake_participant("fake-b", "Fake B", stream=False)
    )

    messages = run_discussion(
        client, "Q?",
        ask("fake-b", "x-1", "x-2", extra_participants=[extra("x-1", "fake-a"), extra("x-2", "fake-a")],
            models={"x-2": "picked"}),
    )

    assert messages[-1]["outcome"] == "completed"
    assert received_models["x-1"] == {"base"}
    assert received_models["x-2"] == {"picked"}


def test_an_extra_participant_can_moderate(client, two_fakes):
    messages = run_discussion(
        client, "Q?", consensus("fake-a", "x-1", moderator_id="x-1", extra_participants=[extra("x-1", "fake-b", "m")])
    )

    assert messages[0]["settings"]["moderator_id"] == "x-1"
    drafts = [(m["round"], m["participant_id"]) for m in of_type(messages, "turn_completed") if m["purpose"] == "draft"]
    assert drafts and all(pid == "x-1" for _, pid in drafts)
    assert messages[-1]["outcome"] == "consensus"
    assert messages[-1]["result"]["text"] == "B's draft"


def test_a_failing_moderator_hands_over_to_an_extra_participant(client, write_participants):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False, drafts=["A's draft"], fail_rounds=[1])
        + fake_participant("fake-b", "Fake B", stream=False, drafts=["B's draft"])
    )

    messages = run_discussion(
        client, "Q?",
        consensus("fake-a", "x-1", "fake-b", moderator_id="fake-a", extra_participants=[extra("x-1", "fake-b", "m")]),
    )

    assert [(c["participant_id"], c["round"]) for c in of_type(messages, "moderator_changed")] == [("x-1", 1)]
    assert messages[-1]["outcome"] == "consensus"


# --- invalid settings ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("settings", "fragment"),
    [
        (ask("fake-a", "X_1", extra_participants=[extra("X_1", "fake-a")]), "格式不合法"),
        (ask("fake-a", "-x", extra_participants=[extra("-x", "fake-a")]), "格式不合法"),
        (ask("fake-a", "x" * 65, extra_participants=[extra("x" * 65, "fake-a")]), "格式不合法"),
        (ask("fake-a", "fake-b", extra_participants=[extra("fake-b", "fake-a")]), "重複"),
        (ask("fake-a", "fake-off", extra_participants=[extra("fake-off", "fake-a")]), "重複"),
        (ask("fake-a", "x-1", extra_participants=[extra("x-1", "fake-a"), extra("x-1", "fake-b")]), "重複"),
        (ask("fake-a", "x-1", extra_participants=[extra("x-1", "nobody")]), "不存在或已停用"),
        (ask("fake-a", "x-1", extra_participants=[extra("x-1", "fake-off")]), "不存在或已停用"),
        (ask("fake-a", "fake-b", models={"fake-a": "has space"}), "模型不合法"),
        (ask("fake-a", "fake-b", models={"fake-a": "   "}), "模型不合法"),
        (ask("fake-a", "fake-b", models={"fake-a": "m" * 101}), "模型不合法"),
        (ask("fake-a", "x-1", extra_participants=[extra("x-1", "fake-a", "a\tb")]), "模型不合法"),
        (ask("fake-a", "fake-b", models={"fake-off": "m"}), "不在這場討論的參與者中"),
        (ask("fake-a", "x-1"), "未知或已停用的參與者"),
    ],
)
def test_invalid_models_or_extra_participants_are_rejected(client, write_participants, data_dir, settings, fragment):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False)
        + fake_participant("fake-b", "Fake B", stream=False)
        + fake_participant("fake-off", "Fake Off", stream=False).replace('adapter = "fake"', 'adapter = "fake"\nenabled = false')
    )

    messages = run_discussion(client, "Q?", settings)

    assert [m["type"] for m in messages] == ["error"]
    assert fragment in messages[0]["message"]
    assert not data_dir.exists() or list(data_dir.glob("*.json")) == []


def test_a_model_of_exactly_100_characters_is_accepted(client, two_fakes):
    messages = run_discussion(client, "Q?", ask("fake-a", "fake-b", models={"fake-a": "m" * 100}))

    assert messages[0]["participants"][0]["model"] == "m" * 100


# --- display names --------------------------------------------------------------------


def _config(*participants: ParticipantConfig) -> ParticipantsConfig:
    return ParticipantsConfig(defaults=Defaults(), participants=list(participants))


def _settings(ids: list[str], *, models=None, extras=()) -> DiscussionSettings:
    return DiscussionSettings(
        mode="ask", participant_ids=ids, judge="stance_vote", moderator_id=None, speaking_order="parallel",
        max_rounds=3, turn_timeout_seconds=60, jev_threshold=0.8,
        models=models or {}, extra_participants=[ExtraParticipant(**e) for e in extras],
    )


def test_duplicated_names_get_the_model_then_a_number():
    config = _config(
        ParticipantConfig("claude", "Claude", "claude"),
        ParticipantConfig("codex", "Codex", "codex", model="gpt"),
    )
    settings = _settings(
        ["claude", "x-1", "x-2", "codex", "x-3"],
        extras=[extra("x-1", "claude", "opus"), extra("x-2", "claude", "opus"), extra("x-3", "claude")],
    )

    built = build_participants(settings, config)

    assert [(p.id, p.display_name, p.model) for p in built] == [
        ("claude", "Claude（預設模型）", None),
        ("x-1", "Claude（opus）", "opus"),
        ("x-2", "Claude（opus） 2", "opus"),
        ("codex", "Codex", "gpt"),
        ("x-3", "Claude（預設模型） 2", None),
    ]
    assert config.get("claude").display_name == "Claude"  # the participants file is unchanged


def test_participants_address_each_other_by_the_unique_names(client, write_participants):
    write_participants(fake_participant("fake-a", "Fake A", stream=False, echo_prompt=True))

    messages = run_discussion(
        client, "Q?", ask("fake-a", "x-1", extra_participants=[extra("x-1", "fake-a", "m2")])
    )

    assert [p["display_name"] for p in messages[0]["participants"]] == ["Fake A（預設模型）", "Fake A（m2）"]
    prompts = {m["participant_id"]: m["text"] for m in of_type(messages, "turn_completed")}
    assert "You are Fake A（預設模型）, discussing the user's question with: Fake A（m2）." in prompts["fake-a"]
    assert "You are Fake A（m2）, discussing the user's question with: Fake A（預設模型）." in prompts["x-1"]


# --- 提問轉共識討論 ----------------------------------------------------------------------


def derive(client, from_id: str) -> list[dict]:
    received: list[dict] = []
    with client.websocket_connect("/ws/discussion") as ws:
        ws.send_json(
            {
                "type": "start",
                "question": "ignored?",
                "settings": {"mode": "consensus", "participant_ids": ["ignored"], "judge": "stance_vote"},
                "from_discussion_id": from_id,
            }
        )
        while True:
            msg = ws.receive_json()
            received.append(msg)
            if msg["type"] in ("discussion_finished", "error"):
                break
    return received


def test_converting_an_ask_keeps_its_models_and_extra_participants(client, two_fakes, received_models):
    asked = run_discussion(
        client, "Q?",
        ask("fake-a", "x-1", models={"fake-a": "fast"}, extra_participants=[extra("x-1", "fake-b", "other")]),
    )
    received_models.clear()

    messages = derive(client, asked[0]["discussion_id"])

    started = messages[0]
    assert started["type"] == "discussion_started"
    assert started["settings"]["participant_ids"] == ["fake-a", "x-1"]
    assert started["settings"]["models"] == {"fake-a": "fast"}
    assert started["settings"]["extra_participants"] == [extra("x-1", "fake-b", "other")]
    assert started["participants"] == asked[0]["participants"]
    assert received_models == {"fake-a": {"fast"}, "x-1": {"other"}}
    assert messages[-1]["outcome"] == "consensus"


def test_converting_an_ask_whose_template_was_removed_is_an_error(client, write_participants, data_dir):
    write_participants(
        fake_participant("fake-a", "Fake A", stream=False)
        + fake_participant("fake-b", "Fake B", stream=False)
        + fake_participant("fake-c", "Fake C", stream=False)
    )
    asked = run_discussion(client, "Q?", ask("fake-a", "fake-b", "x-1", extra_participants=[extra("x-1", "fake-c")]))
    write_participants(fake_participant("fake-a", "Fake A", stream=False) + fake_participant("fake-b", "Fake B", stream=False))

    messages = derive(client, asked[0]["discussion_id"])

    assert [m["type"] for m in messages] == ["error"]
    assert "fake-c" in messages[0]["message"]
    assert len(list(data_dir.glob("*.json"))) == 1  # only the ask


# --- schema 1 records ----------------------------------------------------------------------


@pytest.fixture
def schema1_record(data_dir) -> str:
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIXTURES / "record-schema1-ask.json", data_dir / f"{SCHEMA1_ID}.json")
    return SCHEMA1_ID


def test_a_schema_1_record_is_listed_and_readable(client, schema1_record):
    summaries = client.get("/api/discussions").json()
    assert [s["id"] for s in summaries] == [SCHEMA1_ID]
    assert summaries[0]["question"] == "Schema 1 question?"

    response = client.get(f"/api/discussions/{SCHEMA1_ID}")

    assert response.status_code == 200
    record = response.json()
    assert record["schema_version"] == 1
    assert record["settings"]["models"] == {}
    assert record["settings"]["extra_participants"] == []
    assert [p["model"] for p in record["participants"]] == [None, None]
    assert [[t["text"] for t in r["turns"]] for r in record["rounds"]] == [["Old answer from A", "Old answer from B"]]


def test_a_schema_1_ask_converts_like_in_v1(client, two_fakes, schema1_record, received_models):
    messages = derive(client, schema1_record)

    assert messages[0]["settings"]["participant_ids"] == ["fake-a", "fake-b"]
    assert messages[0]["settings"]["models"] == {}
    assert messages[0]["settings"]["extra_participants"] == []
    assert messages[-1]["outcome"] == "consensus"
