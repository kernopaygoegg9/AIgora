"""WebSocket message types (spec "WebSocket 訊息").

FROZEN after ticket 02. Tickets that need a new message type or field must
stop and report instead of editing this file. (ui-redesign ticket 10 deliberately
added `models` / `extra_participants` to the start settings and the snapshot:
spec "參與者與模型選擇".) The TypeScript twin is
`frontend/src/contracts/messages.ts`; `tests/test_ws_messages.py` checks that
both define the same types and fields.

One WebSocket connection per discussion. Every message is a JSON object with
`type`. Server messages also carry `discussion_id` and a per-connection
increasing `seq` (starting at 1).

Additions beyond the spec table (all compatible supersets):
- `discussion_started.question` / `.derived_from`: the question and the ask
  it was converted from, so the client never has to remember them.
- `turn_*.purpose`: extra calls requested by the discussion mode (moderator
  draft, final result, no-consensus summary, judge-B confirmation) reuse the
  turn messages with `purpose != "turn"`, so they can stream and fail like
  normal turns. Their results are still announced by `draft_created`,
  `confirmation_result` and `discussion_finished`.
- `participant_removed.round` / `moderator_changed.round`: the round it
  happened in (mirrors the discussion record).
- `discussion_finished.reason`: a human-readable explanation (e.g. why
  participants were insufficient); null when there is nothing to add.
- `error.discussion_id` is null when no discussion has started yet.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from aigora.domain import (
    FailureKind,
    JudgeId,
    JudgeOutcome,
    ModeId,
    Outcome,
    SpeakingOrderId,
    Stance,
    TurnPurpose,
    TurnStatus,
)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- shared shapes -------------------------------------------------------------


class ExtraParticipant(_Model):
    """A participant that exists only in one discussion (臨時參與者), copied from the
    configured participant `template_id` (adapter, display name, avatar, options).
    `model` null: the template's model. Its `id` also goes into `participant_ids`."""

    id: str
    template_id: str
    model: str | None


class StartSettings(_Model):
    """Settings sent with `start`. Omitted (null) fields are filled from `[defaults]`.

    `models`: participant id -> the model to use in this discussion (configured or extra).
    `extra_participants`: definitions of the extra ids in `participant_ids`.
    Omitting both behaves exactly like v1."""

    mode: ModeId
    participant_ids: list[str] = Field(min_length=1)
    judge: JudgeId | None = None
    moderator_id: str | None = None
    speaking_order: SpeakingOrderId | None = None
    max_rounds: int | None = Field(default=None, ge=1)
    turn_timeout_seconds: float | None = Field(default=None, gt=0)
    jev_threshold: float | None = Field(default=None, ge=0, le=1)
    models: dict[str, str] | None = None
    extra_participants: list[ExtraParticipant] | None = None


class DiscussionSettings(_Model):
    """The full settings snapshot, locked when the discussion starts.

    `models` / `extra_participants` are the resolved requests (trimmed models; only the
    extra participants that take part); empty in v1 records."""

    mode: ModeId
    participant_ids: list[str]
    judge: JudgeId
    moderator_id: str | None  # null only when the mode does not use a moderator
    speaking_order: SpeakingOrderId
    max_rounds: int
    turn_timeout_seconds: float
    jev_threshold: float
    models: dict[str, str] = {}
    extra_participants: list[ExtraParticipant] = []


class Capabilities(_Model):
    web_access: bool
    streaming: bool


class ParticipantSnapshot(_Model):
    """`model`: the model actually used (after `models` overrides); `display_name`: the
    name used in this discussion (made unique, see `build_participants`)."""

    id: str
    display_name: str
    adapter: str
    model: str | None
    avatar: str  # filename, served at /api/avatars/{avatar}
    capabilities: Capabilities


class JudgeDetail(_Model):
    """Judge A fills `stances` (participant id -> stance; null = unparseable);
    judge B fills `probability` and `threshold`."""

    stances: dict[str, Stance | None] | None = None
    probability: float | None = None
    threshold: float | None = None


class ConfirmationAnswer(_Model):
    participant_id: str
    agree: bool
    reason: str


class ResultAnswer(_Model):
    """One participant's turn in an ask's result."""

    participant_id: str
    status: TurnStatus
    text: str | None


class DiscussionResult(_Model):
    """`answers`: an ask's turns. `consensus`: the consensus text.
    `no_consensus`: the moderator's final positions + remaining disagreements."""

    kind: Literal["answers", "consensus", "no_consensus"]
    text: str | None = None
    answers: list[ResultAnswer] | None = None


SHARED_MODELS: dict[str, type[BaseModel]] = {
    model.__name__: model
    for model in (
        ExtraParticipant,
        StartSettings,
        DiscussionSettings,
        Capabilities,
        ParticipantSnapshot,
        JudgeDetail,
        ConfirmationAnswer,
        ResultAnswer,
        DiscussionResult,
    )
}


# --- client -> server ----------------------------------------------------------


class StartMessage(_Model):
    type: Literal["start"] = "start"
    question: str = Field(min_length=1)
    settings: StartSettings
    from_discussion_id: str | None = None  # convert a finished ask into a consensus discussion


class InterjectMessage(_Model):
    type: Literal["interject"] = "interject"
    text: str = Field(min_length=1)


class StopMessage(_Model):
    type: Literal["stop"] = "stop"


ClientMessage = Annotated[StartMessage | InterjectMessage | StopMessage, Field(discriminator="type")]


# --- server -> client ----------------------------------------------------------


class _ServerMessage(_Model):
    discussion_id: str
    seq: int


class DiscussionStarted(_ServerMessage):
    type: Literal["discussion_started"] = "discussion_started"
    question: str
    derived_from: str | None = None
    settings: DiscussionSettings
    participants: list[ParticipantSnapshot]


class RoundStarted(_ServerMessage):
    type: Literal["round_started"] = "round_started"
    round: int


class TurnStarted(_ServerMessage):
    type: Literal["turn_started"] = "turn_started"
    round: int
    participant_id: str
    purpose: TurnPurpose = "turn"


class TurnDelta(_ServerMessage):
    type: Literal["turn_delta"] = "turn_delta"
    round: int
    participant_id: str
    purpose: TurnPurpose = "turn"
    text: str  # appended to the text streamed so far


class TurnCompleted(_ServerMessage):
    type: Literal["turn_completed"] = "turn_completed"
    round: int
    participant_id: str
    purpose: TurnPurpose = "turn"
    text: str  # full text
    stance: Stance | None = None


class TurnFailed(_ServerMessage):
    type: Literal["turn_failed"] = "turn_failed"
    round: int
    participant_id: str
    purpose: TurnPurpose = "turn"
    reason: str
    kind: FailureKind


class ParticipantRemoved(_ServerMessage):
    type: Literal["participant_removed"] = "participant_removed"
    participant_id: str
    reason: str
    round: int | None = None


class ModeratorChanged(_ServerMessage):
    type: Literal["moderator_changed"] = "moderator_changed"
    participant_id: str
    round: int | None = None


class DraftCreated(_ServerMessage):
    type: Literal["draft_created"] = "draft_created"
    round: int
    text: str


class JudgeResult(_ServerMessage):
    type: Literal["judge_result"] = "judge_result"
    round: int
    judge: JudgeId
    outcome: JudgeOutcome
    detail: JudgeDetail


class ConfirmationResult(_ServerMessage):
    type: Literal["confirmation_result"] = "confirmation_result"
    round: int
    answers: list[ConfirmationAnswer]


class InterjectionQueued(_ServerMessage):
    type: Literal["interjection_queued"] = "interjection_queued"
    text: str
    applies_to_round: int


class RoundCompleted(_ServerMessage):
    type: Literal["round_completed"] = "round_completed"
    round: int


class DiscussionFinished(_ServerMessage):
    type: Literal["discussion_finished"] = "discussion_finished"
    outcome: Outcome
    result: DiscussionResult | None = None
    reason: str | None = None


class ErrorMessage(_ServerMessage):
    type: Literal["error"] = "error"
    discussion_id: str | None = None  # type: ignore[assignment]
    message: str


ServerMessage = Annotated[
    DiscussionStarted
    | RoundStarted
    | TurnStarted
    | TurnDelta
    | TurnCompleted
    | TurnFailed
    | ParticipantRemoved
    | ModeratorChanged
    | DraftCreated
    | JudgeResult
    | ConfirmationResult
    | InterjectionQueued
    | RoundCompleted
    | DiscussionFinished
    | ErrorMessage,
    Field(discriminator="type"),
]


def _types(*models: type[BaseModel]) -> dict[str, type[BaseModel]]:
    return {model.model_fields["type"].default: model for model in models}


CLIENT_MESSAGE_TYPES: dict[str, type[BaseModel]] = _types(StartMessage, InterjectMessage, StopMessage)
SERVER_MESSAGE_TYPES: dict[str, type[BaseModel]] = _types(
    DiscussionStarted,
    RoundStarted,
    TurnStarted,
    TurnDelta,
    TurnCompleted,
    TurnFailed,
    ParticipantRemoved,
    ModeratorChanged,
    DraftCreated,
    JudgeResult,
    ConfirmationResult,
    InterjectionQueued,
    RoundCompleted,
    DiscussionFinished,
    ErrorMessage,
)

_client_adapter: TypeAdapter[Any] = TypeAdapter(ClientMessage)
_server_adapter: TypeAdapter[Any] = TypeAdapter(ServerMessage)


def parse_client_message(data: Any) -> StartMessage | InterjectMessage | StopMessage:
    """Validate a decoded JSON message from the browser (raises pydantic.ValidationError)."""
    return _client_adapter.validate_python(data)


def parse_server_message(data: Any) -> BaseModel:
    """Validate a decoded server message (used by tests)."""
    return _server_adapter.validate_python(data)


def to_wire(message: BaseModel) -> dict[str, Any]:
    """The JSON-ready dict to send, e.g. `await websocket.send_json(to_wire(msg))`."""
    return message.model_dump(mode="json")
