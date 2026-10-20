"""Interfaces for the replaceable parts of a discussion (spec "Implementation Decisions").

- `DiscussionMode` (討論模式): `ask`, `consensus`.
- `ConsensusJudge` (共識裁定方式): `stance_vote` (A), `jev` (B).
- `SpeakingOrder` (發言順序): `parallel`; `sequential` is interface only in v1.

The engine owns execution (calls, parallelism, timeouts, failure counting,
removal, interjection queue, stop, events, saving). These objects only make
decisions from a read-only `DiscussionView`, so adding a mode / judge / order
never touches the engine. The engine (ticket 03) builds the view and may add
fields to it; it must keep the ones below.

Flow of one consensus round, as driven by the engine:

    for batch in speaking_order.schedule(active_ids, round):   # turns
        run batch in parallel, each with mode.round_instructions(view, pid)
    loop:
        decision = await mode.after_round(view, last_extra_results)
        ContinueRound -> next round
        ExtraCalls    -> run the calls (e.g. moderator draft, confirmations),
                         then call after_round again with their results
        Finish        -> discussion_finished(outcome, result)

The consensus mode consults its `ConsensusJudge` inside `after_round`; the
mode reports judge outcomes through `Decision.judge_report` /
`Decision.confirmation_report`, which the engine turns into `judge_result` /
`confirmation_result` messages and stores in the record.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from aigora.adapters.base import Availability
from aigora.api.messages import ConfirmationAnswer, DiscussionResult, DiscussionSettings, JudgeDetail
from aigora.domain import (
    JudgeId,
    JudgeOutcome,
    ModeId,
    Outcome,
    SpeakingOrderId,
    Stance,
    TurnPurpose,
    TurnStatus,
)

# --- read-only discussion state --------------------------------------------------


@dataclass(frozen=True)
class TurnView:
    participant_id: str
    status: TurnStatus
    text: str | None
    stance: Stance | None  # parsed from the last line; None = no / unparseable stance
    error: str | None = None


@dataclass(frozen=True)
class RoundView:
    number: int  # 1-based
    turns: Sequence[TurnView]
    draft: str | None = None  # moderator's consensus draft written after this round
    interjections: Sequence[str] = ()  # user interjections that apply from this round


@dataclass(frozen=True)
class DiscussionView:
    question: str
    settings: DiscussionSettings
    participant_names: Mapping[str, str]  # id -> display name, all participants of the discussion
    active_participant_ids: Sequence[str]  # still in the discussion, in settings order
    moderator_id: str | None
    rounds: Sequence[RoundView]  # completed rounds plus the current one (last)
    # Reasons from participants who disagreed in the last confirmation (judge B),
    # carried into the next round's instructions.
    pending_disagreements: Mapping[str, str] = field(default_factory=dict)

    @property
    def current_round(self) -> RoundView | None:
        return self.rounds[-1] if self.rounds else None


# --- discussion mode ---------------------------------------------------------------


@dataclass(frozen=True)
class ExtraCall:
    """One extra call to a participant outside the normal turns."""

    participant_id: str
    purpose: TurnPurpose  # "draft", "final_result", "no_consensus_summary", "confirmation"
    instructions: str  # appended to the prompt by the Prompt Builder


@dataclass(frozen=True)
class ExtraCallResult:
    call: ExtraCall
    status: TurnStatus
    text: str | None
    stance: Stance | None
    error: str | None = None


@dataclass(frozen=True)
class JudgeReport:
    judge: JudgeId
    outcome: JudgeOutcome
    detail: JudgeDetail


@dataclass(frozen=True)
class ConfirmationReport:
    answers: Sequence[ConfirmationAnswer]


@dataclass(frozen=True)
class ContinueRound:
    judge_report: JudgeReport | None = None
    confirmation_report: ConfirmationReport | None = None


@dataclass(frozen=True)
class ExtraCalls:
    """Run these calls (in parallel), then ask the mode again with their results.

    A finished `draft` call becomes the round's draft (`draft_created`)."""

    calls: Sequence[ExtraCall]
    judge_report: JudgeReport | None = None
    confirmation_report: ConfirmationReport | None = None


@dataclass(frozen=True)
class Finish:
    outcome: Outcome
    result: DiscussionResult | None
    reason: str | None = None
    judge_report: JudgeReport | None = None
    confirmation_report: ConfirmationReport | None = None


Decision = ContinueRound | ExtraCalls | Finish


class DiscussionMode(ABC):
    id: ClassVar[ModeId]
    name: ClassVar[str]  # shown in the settings panel, e.g. "提問"
    # Which `DiscussionSettings` fields this mode uses (the settings panel shows
    # only these besides the participants), e.g. {"participant_ids", "speaking_order"}.
    uses_settings: ClassVar[frozenset[str]]

    @abstractmethod
    def round_instructions(self, view: DiscussionView, participant_id: str) -> str | None:
        """Instructions for `participant_id` in the current round (e.g. "take a stance on the
        draft; end with STANCE: ..."), or None for none."""

    @abstractmethod
    async def after_round(
        self, view: DiscussionView, extra_results: Sequence[ExtraCallResult] | None
    ) -> Decision:
        """Called when the round's turns are done (`extra_results` None), and again after
        each `ExtraCalls` with their results."""


# --- consensus judge ----------------------------------------------------------------


@dataclass(frozen=True)
class NotReached:
    detail: JudgeDetail
    # Disagreeing participants' reasons (judge B confirmation), carried into the next round.
    disagreements: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class NeedsConfirmation:
    """Judge B: ask every active participant whether consensus has been reached."""

    question: str
    detail: JudgeDetail


@dataclass(frozen=True)
class Reached:
    detail: JudgeDetail
    # "draft": the round's draft is the consensus result (judge A).
    # "moderator_final": ask the moderator to write the final result (judge B).
    result_source: str = "draft"


Evaluation = NotReached | NeedsConfirmation | Reached


class ConsensusJudge(ABC):
    id: ClassVar[JudgeId]
    name: ClassVar[str]

    @abstractmethod
    def availability(self, env: Mapping[str, str]) -> Availability:
        """`env` holds backend-only settings from `.env` (e.g. TYPESAFE_API_KEY)."""

    @abstractmethod
    async def evaluate(self, view: DiscussionView, threshold: float) -> Evaluation:
        """Called after a round (from round 2) once its draft exists."""

    @abstractmethod
    async def handle_confirmation(
        self, view: DiscussionView, answers: Sequence[ConfirmationAnswer]
    ) -> Reached | NotReached:
        """Judge B: the confirmation answers -> reached, or not reached with the reasons."""


# --- speaking order -----------------------------------------------------------------


class SpeakingOrder(ABC):
    id: ClassVar[SpeakingOrderId]
    name: ClassVar[str]
    implemented: ClassVar[bool] = True  # sequential is False in v1

    @abstractmethod
    def schedule(self, participant_ids: Sequence[str], round_number: int) -> list[list[str]]:
        """Ordered batches. Turns in one batch run in parallel and see only earlier batches
        and earlier rounds. Parallel: one batch with everyone. Sequential: one per
        participant, rotating the first speaker every round."""
