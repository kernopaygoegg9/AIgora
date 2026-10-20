"""Consensus judges (共識裁定方式). Look one up with `get_judge(id)`.

A new judge is a `ConsensusJudge` subclass registered in `JUDGES`; the engine
does not change. `jev` (B) is added by ticket 08.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from aigora.adapters.base import Availability
from aigora.api.messages import ConfirmationAnswer, JudgeDetail
from aigora.discussion.interfaces import (
    ConsensusJudge,
    DiscussionView,
    Evaluation,
    NotReached,
    Reached,
)


class StanceVoteJudge(ConsensusJudge):
    """方式 A (主持人 + 全員表態): reached when every active participant's turn in the
    current round ends with `STANCE: AGREE` on the previous round's draft. A failed turn
    or an unparseable stance counts as disagreeing."""

    id = "stance_vote"
    name = "主持人 + 全員表態"

    def availability(self, env: Mapping[str, str]) -> Availability:
        return Availability(True)

    async def evaluate(self, view: DiscussionView, threshold: float) -> Evaluation:
        current = view.current_round
        turns = {t.participant_id: t for t in (current.turns if current else ())}
        stances = {
            pid: (turns[pid].stance if pid in turns and turns[pid].status == "ok" else None)
            for pid in view.active_participant_ids
        }
        previous = view.rounds[-2] if len(view.rounds) >= 2 else None
        detail = JudgeDetail(stances=stances)
        if previous and previous.draft and stances and all(s == "AGREE" for s in stances.values()):
            return Reached(detail=detail, result_source="draft")
        return NotReached(detail=detail)

    async def handle_confirmation(
        self, view: DiscussionView, answers: Sequence[ConfirmationAnswer]
    ) -> Reached | NotReached:
        raise NotImplementedError("stance_vote never asks for a confirmation")


JUDGES: dict[str, type[ConsensusJudge]] = {StanceVoteJudge.id: StanceVoteJudge}


def get_judge(judge_id: str) -> ConsensusJudge:
    """Raises KeyError for an unknown or not yet implemented judge."""
    return JUDGES[judge_id]()
