"""Consensus judges (共識裁定方式). Look one up with `get_judge(id)`.

A new judge is a `ConsensusJudge` subclass registered in `JUDGES`; the engine
does not change.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from aigora.adapters.base import Availability
from aigora.api.messages import ConfirmationAnswer, JudgeDetail
from aigora.discussion.interfaces import (
    ConsensusJudge,
    DiscussionView,
    Evaluation,
    NeedsConfirmation,
    NotReached,
    Reached,
)
from aigora.env import TYPESAFE_API_KEY, backend_env, has_typesafe_key
from aigora.jev_client import JevError, create_jev_client

log = logging.getLogger("aigora.judges")


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


CONFIRMATION_QUESTION = (
    "Has this discussion reached consensus: do you accept the latest consensus draft (with the "
    "replies in this round) as the group's answer to the question? If you do not, explain briefly "
    "what is still unresolved. The last line of your reply must be exactly `STANCE: AGREE` "
    "(consensus has been reached) or `STANCE: DISAGREE` (it has not)."
)


class JevJudge(ConsensusJudge):
    """方式 B (Jev 判斷 + 反問確認): from round 2, Jev gives the probability that the whole
    discussion has reached consensus. Below the threshold: not reached. At or above it:
    every active participant is asked to confirm; all agreeing -> reached (the moderator
    writes the final result), anyone disagreeing -> not reached with their reasons.
    A Jev failure counts as not reached (probability null) so the discussion goes on."""

    id = "jev"
    name = "Jev 判斷 + 反問確認"

    def availability(self, env: Mapping[str, str]) -> Availability:
        if has_typesafe_key(dict(env)):
            return Availability(True)
        return Availability(False, f".env 沒有設定 {TYPESAFE_API_KEY}")

    async def evaluate(self, view: DiscussionView, threshold: float) -> Evaluation:
        try:
            # Looked up at call time so tests can replace `create_jev_client`.
            probability: float | None = await create_jev_client(backend_env()).consensus_probability(
                transcript_of(view)
            )
        except JevError as exc:
            log.warning("Jev failed: %s", exc)
            probability = None
        detail = JudgeDetail(probability=probability, threshold=threshold)
        if probability is not None and probability >= threshold:
            return NeedsConfirmation(question=CONFIRMATION_QUESTION, detail=detail)
        return NotReached(detail=detail)

    async def handle_confirmation(
        self, view: DiscussionView, answers: Sequence[ConfirmationAnswer]
    ) -> Reached | NotReached:
        current = view.current_round
        # The detail of this round's `confirm` verdict (Jev's probability).
        evaluated = current.judge_detail if current else None
        detail = evaluated or JudgeDetail(threshold=view.settings.jev_threshold)
        disagreements = {a.participant_id: a.reason for a in answers if not a.agree}
        if answers and not disagreements:
            return Reached(detail=detail, result_source="moderator_final")
        return NotReached(detail=detail, disagreements=disagreements)


def transcript_of(view: DiscussionView) -> dict[str, Any]:
    """The discussion as Jev's state: question, participants, and every round's replies and draft."""
    names = view.participant_names
    return {
        "question": view.question,
        "participants": [names.get(pid, pid) for pid in view.active_participant_ids],
        "rounds": [
            {
                "number": r.number,
                "turns": [
                    {"participant": names.get(t.participant_id, t.participant_id), "text": t.text}
                    for t in r.turns
                    if t.status == "ok" and t.text
                ],
                "draft": r.draft,
            }
            for r in view.rounds
        ],
    }


JUDGES: dict[str, type[ConsensusJudge]] = {StanceVoteJudge.id: StanceVoteJudge, JevJudge.id: JevJudge}


def get_judge(judge_id: str) -> ConsensusJudge:
    """Raises KeyError for an unknown or not yet implemented judge."""
    return JUDGES[judge_id]()
