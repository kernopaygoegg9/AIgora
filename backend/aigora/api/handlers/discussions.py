"""GET /api/discussions and GET /api/discussions/{discussion_id}: the discussion store over HTTP."""

from __future__ import annotations

from fastapi import HTTPException

from aigora.api.http_models import DiscussionSummary
from aigora.discussion.store import DiscussionStore
from aigora.record import DiscussionRecord


async def list_discussions() -> list[DiscussionSummary]:
    """Every saved discussion, newest first; in-progress ones have `outcome` null."""
    return [
        DiscussionSummary(
            id=r.id, question=r.question, mode=r.settings.mode, created_at=r.created_at, outcome=r.outcome
        )
        for r in DiscussionStore().list()
    ]


async def get_discussion(discussion_id: str) -> DiscussionRecord:
    """The full discussion record JSON; 404 if there is no such discussion."""
    record = DiscussionStore().read(discussion_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"找不到討論 {discussion_id}")
    return record
