"""GET /api/participants: id, display name, adapter, model, avatar, capabilities, availability, models."""

from __future__ import annotations

import asyncio

from fastapi import HTTPException

from aigora.adapters.base import ModelChoices
from aigora.api.http_models import ModelOption, ParticipantInfo
from aigora.api.messages import Capabilities
from aigora.config import ConfigError, ParticipantConfig, load_participants, participants_file_path
from aigora.participant_info import availability_of, capabilities_of, model_choices_of


async def _info(participant: ParticipantConfig) -> ParticipantInfo:
    # Listing models runs alongside the availability check; an unavailable
    # participant gets no list (the listing is cancelled if still running).
    listing = asyncio.create_task(model_choices_of(participant))
    try:
        availability = await availability_of(participant)
        if availability.available:
            choices = await listing
        else:
            listing.cancel()
            choices = ModelChoices()
    finally:
        if not listing.done():
            listing.cancel()
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
        models=[ModelOption(id=m.id, label=m.label) for m in choices.models],
        free_text_model=choices.free_text,
        models_error=choices.error,
    )


async def list_participants() -> list[ParticipantInfo]:
    """Enabled participants in file order; availability checks and model lists run concurrently."""
    try:
        config = load_participants(participants_file_path())
    except ConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from None
    return list(await asyncio.gather(*(_info(p) for p in config.enabled_participants())))
