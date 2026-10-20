"""GET /api/discussions and GET /api/discussions/{discussion_id}: the discussion store over HTTP."""

from aigora.api.not_implemented import not_implemented


async def list_discussions():
    raise not_implemented()


async def get_discussion(discussion_id: str):
    raise not_implemented()
