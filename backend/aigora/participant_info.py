"""What the API shows about a participant: capabilities, availability, snapshot."""

from __future__ import annotations

from aigora.adapters.base import Availability, get_adapter
from aigora.api.messages import Capabilities, ParticipantSnapshot
from aigora.config import ParticipantConfig


def capabilities_of(participant: ParticipantConfig) -> Capabilities:
    caps = get_adapter(participant.adapter).capabilities(participant)
    return Capabilities(web_access=caps.web_access, streaming=caps.streaming)


async def availability_of(participant: ParticipantConfig) -> Availability:
    """Never raises: an adapter that blows up (or is not built yet) is reported unavailable."""
    try:
        return await get_adapter(participant.adapter).check_availability(participant)
    except Exception as exc:  # noqa: BLE001 - shown to the user as the reason
        return Availability(False, f"{participant.adapter}: {exc or type(exc).__name__}")


def snapshot_of(participant: ParticipantConfig) -> ParticipantSnapshot:
    return ParticipantSnapshot(
        id=participant.id,
        display_name=participant.display_name,
        adapter=participant.adapter,
        model=participant.model,
        avatar=participant.avatar,
        capabilities=capabilities_of(participant),
    )
