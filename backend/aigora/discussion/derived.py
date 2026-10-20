"""提問轉共識討論: a consensus discussion that starts from a finished ask (提問).

The new discussion keeps the ask's question and participants; the ask's answers
become its round 1 as they are (no participant is called for round 1), so the
mode goes straight to the moderator's first draft. The ask's record is only read.

`DerivedDiscussionEngine` replays round 1 through the ordinary events
(`round_started`, `turn_started`, then `turn_completed` / `turn_failed`), so the
live page shows it like any other round; every later round is the engine's own.
"""

from __future__ import annotations

from typing import Any

from aigora.api import messages as m
from aigora.discussion.engine import DiscussionEngine
from aigora.discussion.store import DiscussionStore
from aigora.record import DiscussionRecord, RecordRound


class SourceError(ValueError):
    """The discussion to convert does not exist or cannot be converted (sent back as `error`)."""


def load_source(store: DiscussionStore, discussion_id: str) -> DiscussionRecord:
    """The finished ask with this id, or SourceError."""
    record = store.read(discussion_id)
    if record is None:
        raise SourceError(f"找不到討論 `{discussion_id}`")
    if record.settings.mode != "ask":
        raise SourceError(f"討論 `{discussion_id}` 不是提問，無法轉成共識討論")
    if record.outcome != "completed" or not record.rounds:
        raise SourceError(f"提問 `{discussion_id}` 沒有正常結束，無法轉成共識討論")
    return record


class DerivedDiscussionEngine(DiscussionEngine):
    """A discussion engine whose round 1 is the source ask's round 1."""

    def __init__(self, *, source: DiscussionRecord, **kwargs: Any):
        super().__init__(question=source.question, **kwargs)
        self.record.derived_from = source.id
        self._first_round = source.rounds[0]

    async def _run_round(self, number: int) -> None:
        if number != 1:
            await super()._run_round(number)
            return
        active = set(self.active_participant_ids())
        turns = [t.model_copy() for t in self._first_round.turns if t.participant_id in active]
        self.record.rounds.append(RecordRound(number=1, turns=turns))
        self._schedule_order[1] = [t.participant_id for t in turns]
        await self._emit(m.RoundStarted, round=1)
        for turn in turns:
            ids = {"round": 1, "participant_id": turn.participant_id, "purpose": "turn"}
            await self._emit(m.TurnStarted, **ids)
            if turn.status == "ok":
                await self._emit(m.TurnCompleted, **ids, text=turn.text or "", stance=turn.stance)
            else:
                kind = "timeout" if turn.status == "timeout" else "unknown"
                await self._emit(m.TurnFailed, **ids, reason=turn.error or "發言失敗", kind=kind)
