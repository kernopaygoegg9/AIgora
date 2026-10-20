"""Discussion modes (討論模式). Look one up with `get_mode(id)`.

A new mode is a `DiscussionMode` subclass registered in `MODES`; the engine
does not change.
"""

from __future__ import annotations

from collections.abc import Sequence

from aigora.api.messages import DiscussionResult, ResultAnswer
from aigora.discussion.interfaces import (
    ContinueRound,
    Decision,
    DiscussionMode,
    DiscussionView,
    ExtraCall,
    ExtraCallResult,
    ExtraCalls,
    Finish,
    JudgeReport,
    NeedsConfirmation,
    NotReached,
    Reached,
)
from aigora.discussion.judges import get_judge


class AskMode(DiscussionMode):
    """提問: one round, everyone answers, then the discussion ends with all answers."""

    id = "ask"
    name = "提問"
    uses_settings = frozenset({"participant_ids", "speaking_order", "turn_timeout_seconds"})

    def round_instructions(self, view: DiscussionView, participant_id: str) -> str | None:
        return None

    async def after_round(
        self, view: DiscussionView, extra_results: Sequence[ExtraCallResult] | None
    ) -> Decision:
        round_ = view.current_round
        answers = [
            ResultAnswer(participant_id=t.participant_id, status=t.status, text=t.text)
            for t in (round_.turns if round_ else ())
        ]
        return Finish(outcome="completed", result=DiscussionResult(kind="answers", answers=answers))


STANCE_FORMAT = (
    "The last line of your reply must be exactly `STANCE: AGREE` (you accept the draft as the "
    "consensus) or `STANCE: DISAGREE` (it still needs changes)."
)


class ConsensusMode(DiscussionMode):
    """共識討論: round 1 is a free answer; after every round the moderator writes a
    consensus draft (extra call `draft`); from round 2 everyone, the moderator included,
    takes a stance on the previous draft and the consensus judge decides. At the round
    limit the moderator writes the final positions and remaining disagreements
    (extra call `no_consensus_summary`) and the discussion ends with `no_consensus`."""

    id = "consensus"
    name = "共識討論"
    uses_settings = frozenset(
        {
            "participant_ids",
            "speaking_order",
            "turn_timeout_seconds",
            "moderator_id",
            "judge",
            "max_rounds",
            "jev_threshold",
        }
    )

    def round_instructions(self, view: DiscussionView, participant_id: str) -> str | None:
        current = view.current_round
        if current is None or current.number == 1:
            return None  # round 1: free answer, no stance
        previous = view.rounds[-2]
        if previous.draft:
            parts = [
                f"Read the moderator's consensus draft after round {previous.number} above. Respond to "
                "it and to the other participants: say what you accept and what should change."
            ]
        else:
            parts = ["There is no consensus draft for this round. Continue the discussion and respond to the others."]
        parts.append(STANCE_FORMAT)
        own = next((t for t in previous.turns if t.participant_id == participant_id), None)
        if previous.number >= 2 and own is not None and own.status == "ok" and own.stance is None:
            parts.append(
                "Reminder: your previous reply did not end with a valid stance line, so it was counted "
                "as DISAGREE. End this reply with `STANCE: AGREE` or `STANCE: DISAGREE` on its own last line."
            )
        return "\n\n".join(parts)

    async def after_round(
        self, view: DiscussionView, extra_results: Sequence[ExtraCallResult] | None
    ) -> Decision:
        current = view.current_round
        assert current is not None
        if extra_results is not None:
            return self._after_extra_calls(view, extra_results)

        judge = get_judge(view.settings.judge)
        report: JudgeReport | None = None
        if current.number >= 2:
            evaluation = await judge.evaluate(view, view.settings.jev_threshold)
            if isinstance(evaluation, Reached):
                draft = view.rounds[-2].draft
                return Finish(
                    outcome="consensus",
                    result=DiscussionResult(kind="consensus", text=draft),
                    judge_report=JudgeReport(judge=judge.id, outcome="reached", detail=evaluation.detail),
                )
            if isinstance(evaluation, NeedsConfirmation):
                raise NotImplementedError("confirmation questions are added with judge B (ticket 08)")
            assert isinstance(evaluation, NotReached)
            report = JudgeReport(judge=judge.id, outcome="not_reached", detail=evaluation.detail)

        moderator = view.moderator_id
        assert moderator is not None, "consensus discussions always have a moderator"
        if current.number >= view.settings.max_rounds:
            call = ExtraCall(moderator, "no_consensus_summary", self._summary_instructions(view))
        else:
            call = ExtraCall(moderator, "draft", self._draft_instructions(current.number))
        return ExtraCalls(calls=[call], judge_report=report)

    def _after_extra_calls(self, view: DiscussionView, results: Sequence[ExtraCallResult]) -> Decision:
        result = results[0]
        if result.call.purpose == "no_consensus_summary":
            reason = f"到達輪數上限（{view.settings.max_rounds} 輪）仍未取得共識"
            if result.status != "ok":
                reason += f"；主持人未能寫出最終立場與分歧點：{result.error or result.status}"
            return Finish(
                outcome="no_consensus",
                result=DiscussionResult(kind="no_consensus", text=result.text if result.status == "ok" else None),
                reason=reason,
            )
        return ContinueRound()

    @staticmethod
    def _draft_instructions(round_number: int) -> str:
        return (
            f"You are the moderator. Write the consensus draft after round {round_number}: one answer to "
            "the question that keeps what the participants agree on and resolves their disagreements as "
            "fairly as you can. Everyone, you included, will take a stance on it next round. Write only "
            "the draft itself, without a stance line."
        )

    @staticmethod
    def _summary_instructions(view: DiscussionView) -> str:
        return (
            f"You are the moderator. The discussion reached its limit of {view.settings.max_rounds} rounds "
            "without consensus. Write two sections: 1. each participant's final position, by name; "
            "2. the key points that are still in disagreement. Do not add a stance line."
        )


MODES: dict[str, type[DiscussionMode]] = {AskMode.id: AskMode, ConsensusMode.id: ConsensusMode}


def get_mode(mode_id: str) -> DiscussionMode:
    """Raises KeyError for an unknown mode."""
    return MODES[mode_id]()
