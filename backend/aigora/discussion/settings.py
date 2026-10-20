"""Turn the `start` message's settings into the locked `DiscussionSettings` snapshot."""

from __future__ import annotations

from aigora.api.messages import DiscussionSettings, StartSettings
from aigora.config import ParticipantsConfig
from aigora.discussion.modes import MODES
from aigora.discussion.orders import SPEAKING_ORDERS


class SettingsError(ValueError):
    """The requested settings cannot start a discussion (sent back as an `error` message)."""


def resolve_settings(requested: StartSettings, config: ParticipantsConfig) -> DiscussionSettings:
    """Fill omitted fields from `[defaults]` and validate against the participants file."""
    d = config.defaults
    if requested.mode not in MODES:
        raise SettingsError(f"討論模式 `{requested.mode}` 尚未提供")
    mode = MODES[requested.mode]

    enabled = {p.id for p in config.enabled_participants()}
    ids = list(requested.participant_ids)
    if len(set(ids)) != len(ids):
        raise SettingsError("參與者重複")
    unknown = [pid for pid in ids if pid not in enabled]
    if unknown:
        raise SettingsError(f"未知或已停用的參與者：{', '.join(unknown)}")

    speaking_order = requested.speaking_order or d.speaking_order
    if speaking_order not in SPEAKING_ORDERS:
        raise SettingsError(f"發言順序 `{speaking_order}` 尚未提供")

    moderator_id: str | None = None
    if "moderator_id" in mode.uses_settings:
        moderator_id = requested.moderator_id or (d.moderator if d.moderator in ids else ids[0])
        if moderator_id not in ids:
            raise SettingsError(f"主持人 `{moderator_id}` 不在這場討論的參與者中")

    return DiscussionSettings(
        mode=requested.mode,
        participant_ids=ids,
        judge=requested.judge or d.judge,
        moderator_id=moderator_id,
        speaking_order=speaking_order,
        max_rounds=requested.max_rounds or d.max_rounds,
        turn_timeout_seconds=requested.turn_timeout_seconds or d.turn_timeout_seconds,
        jev_threshold=requested.jev_threshold if requested.jev_threshold is not None else d.jev_threshold,
    )
