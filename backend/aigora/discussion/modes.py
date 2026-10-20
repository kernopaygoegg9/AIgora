"""Discussion modes (討論模式). Look one up with `get_mode(id)`.

A new mode is a `DiscussionMode` subclass registered in `MODES`; the engine
does not change.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from aigora.api.messages import ConfirmationAnswer, DiscussionResult, ResultAnswer
from aigora.discussion.interfaces import (
    ConfirmationReport,
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
from aigora.stance import strip_stance_line


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
    (extra call `no_consensus_summary`) and the discussion ends with `no_consensus`.

    Judge B may ask for a confirmation: every active participant gets an extra call
    `confirmation`; when all agree the moderator writes the final result (extra call
    `final_result`) and the discussion ends with `consensus`; otherwise the round goes on
    as not reached (draft or summary) and the disagreeing reasons reach the next round."""

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
        if view.pending_disagreements:
            parts.append(self._disagreements_note(view, view.pending_disagreements))
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
            return await self._after_extra_calls(view, extra_results)

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
                return ExtraCalls(
                    calls=[ExtraCall(pid, "confirmation", evaluation.question) for pid in view.active_participant_ids],
                    judge_report=JudgeReport(judge=judge.id, outcome="confirm", detail=evaluation.detail),
                )
            assert isinstance(evaluation, NotReached)
            report = JudgeReport(judge=judge.id, outcome="not_reached", detail=evaluation.detail)
        return ExtraCalls(calls=[self._moderator_call(view)], judge_report=report)

    def _moderator_call(self, view: DiscussionView, disagreements: Mapping[str, str] | None = None) -> ExtraCall:
        """Not reached: the next draft, or at the round limit the final positions.

        `disagreements`: this round's confirmation reasons (judge B), for the draft."""
        current = view.current_round
        assert current is not None
        moderator = view.moderator_id
        assert moderator is not None, "consensus discussions always have a moderator"
        if current.number >= view.settings.max_rounds:
            return ExtraCall(moderator, "no_consensus_summary", self._summary_instructions(view))
        instructions = self._draft_instructions(current.number)
        if disagreements:
            instructions += "\n\n" + self._disagreements_note(view, disagreements)
        return ExtraCall(moderator, "draft", instructions)

    def __init__(self) -> None:
        # (round, purpose) -> participants who already tried that moderator call.
        self._tried: dict[tuple[int, str], set[str]] = {}

    async def _after_extra_calls(self, view: DiscussionView, results: Sequence[ExtraCallResult]) -> Decision:
        assert view.current_round is not None
        if results[0].call.purpose == "confirmation":
            return await self._after_confirmations(view, results)
        result = results[0]
        tried = self._tried.setdefault((view.current_round.number, result.call.purpose), set())
        tried.add(result.call.participant_id)
        # A failed moderator call hands over to the next participant (the engine records
        # it); the new moderator retries the call once, unless it has already tried.
        moderator_call = result.call.purpose in ("draft", "final_result", "no_consensus_summary")
        if moderator_call and result.status != "ok" and view.moderator_id is not None and view.moderator_id not in tried:
            return ExtraCalls(calls=[ExtraCall(view.moderator_id, result.call.purpose, result.call.instructions)])
        if result.call.purpose == "final_result":
            if result.status == "ok":
                return Finish(outcome="consensus", result=DiscussionResult(kind="consensus", text=result.text))
            draft = view.rounds[-2].draft if len(view.rounds) >= 2 else None
            return Finish(
                outcome="consensus",
                result=DiscussionResult(kind="consensus", text=draft),
                reason=f"主持人未能寫出最終共識結果（{result.error or result.status}），以上一份共識草案作為結果",
            )
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

    async def _after_confirmations(self, view: DiscussionView, results: Sequence[ExtraCallResult]) -> Decision:
        judge = get_judge(view.settings.judge)
        answers = [_confirmation_answer(r) for r in results]
        verdict = await judge.handle_confirmation(view, answers)
        confirmation = ConfirmationReport(answers=answers)
        if isinstance(verdict, Reached):
            moderator = view.moderator_id
            assert moderator is not None, "consensus discussions always have a moderator"
            return ExtraCalls(
                calls=[ExtraCall(moderator, "final_result", self._final_instructions())],
                judge_report=JudgeReport(judge=judge.id, outcome="reached", detail=verdict.detail),
                confirmation_report=confirmation,
            )
        # Not reached: the round goes on like any other (draft, or the summary at the limit),
        # and the moderator sees the reasons. The engine hands them to the next round only
        # (`pending_disagreements`, from the reported answers).
        return ExtraCalls(
            calls=[self._moderator_call(view, verdict.disagreements)],
            judge_report=JudgeReport(judge=judge.id, outcome="not_reached", detail=verdict.detail),
            confirmation_report=confirmation,
        )

    @staticmethod
    def _disagreements_note(view: DiscussionView, disagreements: Mapping[str, str]) -> str:
        lines = [f"- {view.participant_names.get(pid, pid)}: {reason}" for pid, reason in disagreements.items()]
        return (
            "When asked whether consensus had been reached, these participants did not agree. "
            "Address their reasons:\n" + "\n".join(lines)
        )

    @staticmethod
    def _final_instructions() -> str:
        return (
            "You are the moderator. Every participant has confirmed that the discussion reached consensus. "
            "Write the final consensus result: the agreed answer to the question, complete and self-contained, "
            "based on the latest consensus draft and this round's replies. Do not add a stance line."
        )

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


def _confirmation_answer(result: ExtraCallResult) -> ConfirmationAnswer:
    """A confirmation call -> agree only with an ok reply ending in `STANCE: AGREE`."""
    if result.status != "ok":
        return ConfirmationAnswer(
            participant_id=result.call.participant_id, agree=False,
            reason=f"反問失敗：{result.error or result.status}",
        )
    reason = strip_stance_line(result.text or "")
    if result.stance is None:
        reason = (reason + "\n\n" if reason else "") + "（沒有有效的表態行，視為不同意）"
    return ConfirmationAnswer(
        participant_id=result.call.participant_id, agree=result.stance == "AGREE", reason=reason
    )


MODES: dict[str, type[DiscussionMode]] = {AskMode.id: AskMode, ConsensusMode.id: ConsensusMode}


def get_mode(mode_id: str) -> DiscussionMode:
    """Raises KeyError for an unknown mode."""
    return MODES[mode_id]()
