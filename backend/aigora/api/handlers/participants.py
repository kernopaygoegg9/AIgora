"""GET /api/participants: id, display name, adapter, model, avatar, capabilities, availability."""

from __future__ import annotations

import asyncio

from fastapi import HTTPException

from aigora.api.http_models import ParticipantInfo
from aigora.api.messages import Capabilities
from aigora.config import ConfigError, ParticipantConfig, load_participants, participants_file_path
from aigora.participant_info import availability_of, capabilities_of


async def _info(participant: ParticipantConfig) -> ParticipantInfo:
    availability = await availability_of(participant)
    try:
        capabilities = capabilities_of(participant)
    except Exception:  # noqa: BLE001 - adapter not built yet; availability already says why
        capabilities = Capabilities(web_access=False, streaming=False)
    return ParticipantInfo(
        id=participant.id,
        display_name=participant.display_name,
        adapter=participant.adapter,
        model=participant.model,
        avatar=participant.avatar,
        capabilities=capabilities,
        available=availability.available,
        unavailable_reason=None if availability.available else availability.reason,
    )


async def list_participants() -> list[ParticipantInfo]:
    """Enabled participants in file order; availability checks run concurrently."""
    try:
        config = load_participants(participants_file_path())
    except ConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from None
    return list(await asyncio.gather(*(_info(p) for p in config.enabled_participants())))
