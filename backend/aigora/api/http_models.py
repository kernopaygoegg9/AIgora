"""Response bodies of the HTTP API (spec "HTTP API").

TypeScript twin: `frontend/src/contracts/http.ts` (checked by tests/test_ws_messages.py).

- GET /api/participants      -> list[ParticipantInfo] (enabled participants, in file order)
- GET /api/options           -> OptionsResponse
- GET /api/discussions       -> list[DiscussionSummary] (newest first)
- GET /api/discussions/{id}  -> aigora.record.DiscussionRecord (404 if unknown)
- GET /api/avatars/{file}    -> image (falls back to default.png)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from aigora.api.messages import Capabilities
from aigora.domain import JudgeId, ModeId, Outcome, SpeakingOrderId


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelOption(_Model):
    id: str  # what to send as the participant's model
    label: str


class ParticipantInfo(_Model):
    id: str
    display_name: str
    adapter: str
    model: str | None  # as in participants.toml; null = adapter default
    avatar: str  # filename under /api/avatars/
    capabilities: Capabilities
    available: bool
    unavailable_reason: str | None = None
    models: list[ModelOption]  # models it can switch to; empty when unavailable or not listable
    free_text_model: bool  # may a model name outside `models` be typed in?
    models_error: str | None = None  # why `models` could not be loaded


class ModeOption(_Model):
    id: ModeId
    name: str
    uses_settings: list[str]  # DiscussionSettings fields this mode uses


class JudgeOption(_Model):
    id: JudgeId
    name: str
    available: bool
    unavailable_reason: str | None = None


class SpeakingOrderOption(_Model):
    id: SpeakingOrderId
    name: str
    implemented: bool


class DefaultSettings(_Model):
    """`[defaults]` of participants.toml, named like DiscussionSettings."""

    mode: ModeId
    judge: JudgeId
    speaking_order: SpeakingOrderId
    moderator_id: str
    max_rounds: int
    turn_timeout_seconds: float
    jev_threshold: float


class OptionsResponse(_Model):
    modes: list[ModeOption]
    judges: list[JudgeOption]
    speaking_orders: list[SpeakingOrderOption]
    defaults: DefaultSettings


class DiscussionSummary(_Model):
    id: str
    question: str
    mode: ModeId
    created_at: str
    outcome: Outcome | None  # null while in progress


HTTP_MODELS: dict[str, type[BaseModel]] = {
    m.__name__: m
    for m in (
        ModelOption,
        ParticipantInfo,
        ModeOption,
        JudgeOption,
        SpeakingOrderOption,
        DefaultSettings,
        OptionsResponse,
        DiscussionSummary,
    )
}
