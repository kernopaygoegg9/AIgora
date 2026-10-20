"""Discussion modes (討論模式). Look one up with `get_mode(id)`.

A new mode is a `DiscussionMode` subclass registered in `MODES`; the engine
does not change. `consensus` (ticket 04) adds its class here.
"""

from __future__ import annotations

from collections.abc import Sequence

from aigora.api.messages import DiscussionResult, ResultAnswer
from aigora.discussion.interfaces import (
    Decision,
    DiscussionMode,
    DiscussionView,
    ExtraCallResult,
    Finish,
)


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


MODES: dict[str, type[DiscussionMode]] = {AskMode.id: AskMode}


def get_mode(mode_id: str) -> DiscussionMode:
    """Raises KeyError for an unknown mode."""
    return MODES[mode_id]()
