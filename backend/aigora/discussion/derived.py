"""提問轉共識討論: a consensus discussion that starts from a finished ask (提問).

The new discussion keeps the ask's question and participants; the ask's answers
become its round 1 as they are (no participant is called for round 1), so the
mode goes straight to the moderator's first draft. The ask's record is only read.

`derived_engine` passes the ask's round 1 to the engine as its prefilled round 1
(`DiscussionEngine(first_round=...)`); the engine replays it through the ordinary
events (`round_started`, `turn_started`, then `turn_completed` / `turn_failed`), so
the live page shows it like any other round; every later round is the engine's own.
"""

from __future__ import annotations

from typing import Any

from aigora.discussion.engine import DiscussionEngine
from aigora.discussion.store import DiscussionStore
from aigora.record import DiscussionRecord


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


def derived_engine(*, source: DiscussionRecord, **kwargs: Any) -> DiscussionEngine:
    """A discussion engine that continues the finished ask `source`: same question, and the
    ask's round 1 as its prefilled round 1. `kwargs`: the other `DiscussionEngine` arguments."""
    return DiscussionEngine(
        question=source.question, derived_from=source.id, first_round=source.rounds[0], **kwargs
    )
