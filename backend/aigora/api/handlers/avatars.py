"""GET /api/avatars/{filename}: avatar images from `assets/avatars/` (fallback `default.png`)."""

from aigora.api.not_implemented import not_implemented


async def get_avatar(filename: str):
    raise not_implemented()
