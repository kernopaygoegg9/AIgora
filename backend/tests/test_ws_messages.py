"""WebSocket message contract: parsing client messages, serialising server messages,
and keeping the Python and TypeScript definitions in step."""

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from aigora.api import messages as m
from aigora.api.http_models import HTTP_MODELS
from aigora.record import RECORD_MODELS

REPO_ROOT = Path(__file__).resolve().parents[2]
TS_MESSAGES = REPO_ROOT / "frontend" / "src" / "contracts" / "messages.ts"

SPEC_CLIENT_TYPES = {"start", "interject", "stop"}
SPEC_SERVER_TYPES = {
    "discussion_started",
    "round_started",
    "turn_started",
    "turn_delta",
    "turn_completed",
    "turn_failed",
    "participant_removed",
    "moderator_changed",
    "draft_created",
    "judge_result",
    "confirmation_result",
    "interjection_queued",
    "round_completed",
    "discussion_finished",
    "error",
}


def test_every_spec_message_type_is_defined():
    assert set(m.CLIENT_MESSAGE_TYPES) == SPEC_CLIENT_TYPES
    assert set(m.SERVER_MESSAGE_TYPES) == SPEC_SERVER_TYPES


def test_parse_start_with_partial_settings():
    msg = m.parse_client_message(
        {
            "type": "start",
            "question": "Tabs or spaces?",
            "settings": {"mode": "consensus", "participant_ids": ["a", "b"], "max_rounds": 3},
        }
    )
    assert isinstance(msg, m.StartMessage)
    assert msg.settings.participant_ids == ["a", "b"]
    assert msg.settings.max_rounds == 3
    assert msg.settings.judge is None  # filled from participants.toml defaults by the engine
    assert msg.from_discussion_id is None


def test_parse_interject_and_stop():
    assert m.parse_client_message({"type": "interject", "text": "also consider X"}).text == "also consider X"
    assert isinstance(m.parse_client_message({"type": "stop"}), m.StopMessage)


@pytest.mark.parametrize(
    "data",
    [
        {"type": "nope"},
        {"question": "no type"},
        {"type": "start", "question": "", "settings": {"mode": "ask", "participant_ids": ["a"]}},
        {"type": "start", "question": "q", "settings": {"mode": "debate", "participant_ids": ["a"]}},
        {"type": "start", "question": "q", "settings": {"mode": "ask", "participant_ids": []}},
        {"type": "start", "question": "q", "settings": {"mode": "ask", "participant_ids": ["a"], "max_rounds": 0}},
        {"type": "start", "question": "q", "settings": {"mode": "ask", "participant_ids": ["a"], "jev_threshold": 2}},
        {"type": "interject", "text": ""},
        {"type": "stop", "extra": 1},
        "not an object",
    ],
)
def test_invalid_client_messages_are_rejected(data):
    with pytest.raises(ValidationError):
        m.parse_client_message(data)


def test_server_message_serialises_to_the_wire_format():
    msg = m.TurnCompleted(discussion_id="d1", seq=7, round=2, participant_id="a", text="ok\nSTANCE: AGREE",
                          stance="AGREE")
    assert m.to_wire(msg) == {
        "type": "turn_completed",
        "discussion_id": "d1",
        "seq": 7,
        "round": 2,
        "participant_id": "a",
        "purpose": "turn",
        "text": "ok\nSTANCE: AGREE",
        "stance": "AGREE",
    }


def test_server_messages_round_trip():
    msg = m.JudgeResult(
        discussion_id="d1", seq=3, round=2, judge="stance_vote", outcome="not_reached",
        detail=m.JudgeDetail(stances={"a": "AGREE", "b": None}),
    )
    assert m.parse_server_message(m.to_wire(msg)) == msg


def _ts_interfaces() -> dict[str, set[str]]:
    """`type` literal -> field names of each wire-message interface in messages.ts."""
    source = TS_MESSAGES.read_text(encoding="utf-8")
    bases = {
        name: set(re.findall(r"^\s+(\w+)\??:", body, re.MULTILINE))
        for name, body in re.findall(r"export interface (\w+) \{\n(.*?)\n\}", source, re.DOTALL)
    }
    found: dict[str, set[str]] = {}
    for name, extends, body in re.findall(
        r"export interface (\w+)(?: extends (\w+))? \{\n(.*?)\n\}", source, re.DOTALL
    ):
        literal = re.search(r"^\s+type: '(\w+)'", body, re.MULTILINE)
        if literal:
            fields = set(re.findall(r"^\s+(\w+)\??:", body, re.MULTILINE))
            if extends:
                fields |= bases[extends]
            found[literal.group(1)] = fields
    return found


def test_typescript_messages_match_python():
    ts = _ts_interfaces()
    py = {**m.CLIENT_MESSAGE_TYPES, **m.SERVER_MESSAGE_TYPES}
    assert set(ts) == set(py)
    for type_name, model in py.items():
        assert ts[type_name] == set(model.model_fields), type_name


@pytest.mark.parametrize(
    ("ts_file", "models"),
    [
        ("messages.ts", m.SHARED_MODELS),
        ("http.ts", HTTP_MODELS),
        ("record.ts", RECORD_MODELS),
    ],
)
def test_typescript_shared_shapes_match_python(ts_file, models):
    source = (TS_MESSAGES.parent / ts_file).read_text(encoding="utf-8")
    ts = {
        name: set(re.findall(r"^\s+(\w+)\??:", body, re.MULTILINE))
        for name, body in re.findall(r"export interface (\w+) \{\n(.*?)\n\}", source, re.DOTALL)
    }
    for name, model in models.items():
        assert name in ts, name
        assert ts[name] == set(model.model_fields), name
