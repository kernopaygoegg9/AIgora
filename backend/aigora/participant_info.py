"""What the API shows about a participant: capabilities, availability, models, snapshot."""

from __future__ import annotations

import asyncio
import json
import time

from aigora.adapters.base import Availability, ModelChoices, get_adapter
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


MODEL_CACHE_SECONDS = 300.0

# (adapter id, options as JSON) -> (time.monotonic() when listed, result). Only error-free
# results are kept, so starting Ollama or fixing the codex config shows up on the next request.
_model_cache: dict[tuple[str, str], tuple[float, ModelChoices]] = {}
# Listings still running, per cache key: callers asking meanwhile share one adapter call.
# A task is dropped as soon as it finishes, so a failed listing is not kept either.
_in_flight: dict[tuple[str, str], asyncio.Task[ModelChoices]] = {}


def clear_model_cache() -> None:
    _model_cache.clear()
    _in_flight.clear()


async def _list_models(key: tuple[str, str], participant: ParticipantConfig) -> ModelChoices:
    try:
        choices = await get_adapter(participant.adapter).list_models(participant)
    except Exception as exc:  # noqa: BLE001 - shown to the user as the reason
        return ModelChoices(error=f"{participant.adapter}: {exc or type(exc).__name__}")
    if choices.error is None:
        _model_cache[key] = (time.monotonic(), choices)
    return choices


async def model_choices_of(participant: ParticipantConfig) -> ModelChoices:
    """The adapter's model list, cached per (adapter, options). Never raises."""
    key = (participant.adapter, json.dumps(participant.options, sort_keys=True, default=str))
    cached = _model_cache.get(key)
    if cached is not None and time.monotonic() - cached[0] < MODEL_CACHE_SECONDS:
        return cached[1]
    task = _in_flight.get(key)
    if task is None or task.get_loop() is not asyncio.get_running_loop():
        task = asyncio.create_task(_list_models(key, participant))
        _in_flight[key] = task

        def forget(done: asyncio.Task[ModelChoices]) -> None:
            if _in_flight.get(key) is done:
                del _in_flight[key]

        task.add_done_callback(forget)
    # Shielded: one caller giving up does not cancel the listing the others wait for.
    return await asyncio.shield(task)


def snapshot_of(participant: ParticipantConfig) -> ParticipantSnapshot:
    return ParticipantSnapshot(
        id=participant.id,
        display_name=participant.display_name,
        adapter=participant.adapter,
        model=participant.model,
        avatar=participant.avatar,
        capabilities=capabilities_of(participant),
    )
