"""Discussion record JSON (spec "討論紀錄 JSON"): one file per discussion.

Written by the discussion store (ticket 03) after every round and at the end;
served by GET /api/discussions/{id}. TypeScript twin: `DiscussionRecord` in
`frontend/src/contracts/record.ts` (checked by tests/test_ws_messages.py).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from aigora.api.messages import (
    ConfirmationAnswer,
    DiscussionResult,
    DiscussionSettings,
    JudgeDetail,
    ParticipantSnapshot,
)
from aigora.domain import JudgeId, JudgeOutcome, Outcome, Stance, TurnStatus

SCHEMA_VERSION = 1


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RecordTurn(_Model):
    participant_id: str
    status: TurnStatus
    text: str | None
    stance: Stance | None
    started_at: str  # ISO 8601
    ended_at: str | None
    error: str | None


class RecordJudge(_Model):
    judge: JudgeId
    outcome: JudgeOutcome
    detail: JudgeDetail


class RecordRound(_Model):
    number: int
    turns: list[RecordTurn]
    draft: str | None = None
    judge: RecordJudge | None = None  # the round's final verdict
    # Every verdict of the round in order (judge B after a confirmation: `confirm`, then
    # `reached` / `not_reached`); the last one is `judge`.
    judge_history: list[RecordJudge] = []
    confirmations: list[ConfirmationAnswer] | None = None


class RecordInterjection(_Model):
    text: str
    at: str
    applies_to_round: int


class RecordRemoval(_Model):
    participant_id: str
    round: int
    reason: str


class RecordModeratorChange(_Model):
    round: int
    participant_id: str


class DiscussionRecord(_Model):
    schema_version: int = SCHEMA_VERSION
    id: str
    question: str
    created_at: str
    finished_at: str | None = None
    settings: DiscussionSettings
    participants: list[ParticipantSnapshot]
    derived_from: str | None = None
    rounds: list[RecordRound] = []
    interjections: list[RecordInterjection] = []
    removed_participants: list[RecordRemoval] = []
    moderator_changes: list[RecordModeratorChange] = []
    outcome: Outcome | None = None  # null while in progress
    result: DiscussionResult | None = None


RECORD_MODELS: dict[str, type[BaseModel]] = {
    m.__name__: m
    for m in (
        RecordTurn,
        RecordJudge,
        RecordRound,
        RecordInterjection,
        RecordRemoval,
        RecordModeratorChange,
        DiscussionRecord,
    )
}
