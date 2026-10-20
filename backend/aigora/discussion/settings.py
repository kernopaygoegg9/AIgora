"""Turn the `start` message's settings into the locked `DiscussionSettings` snapshot,
and that snapshot into the discussion's participants (`build_participants`)."""

from __future__ import annotations

import dataclasses
import re
from collections import Counter

from aigora.api.messages import DiscussionSettings, ExtraParticipant, StartSettings
from aigora.config import ParticipantConfig, ParticipantsConfig
from aigora.discussion.engine import MIN_PARTICIPANTS
from aigora.discussion.judges import JUDGES
from aigora.discussion.modes import MODES
from aigora.discussion.orders import SPEAKING_ORDERS
from aigora.env import backend_env


EXTRA_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
MAX_MODEL_LENGTH = 100
_WHITESPACE = re.compile(r"\s")


class SettingsError(ValueError):
    """The requested settings cannot start a discussion (sent back as an `error` message)."""


def _model_name(raw: str, owner: str) -> str:
    """A requested model, trimmed: 1-100 characters without whitespace."""
    model = raw.strip()
    if not 1 <= len(model) <= MAX_MODEL_LENGTH or _WHITESPACE.search(model):
        raise SettingsError(f"`{owner}` 的模型不合法：需要 1–{MAX_MODEL_LENGTH} 個字元，而且不能有空白")
    return model


def _resolve_extras(requested: list[ExtraParticipant], config: ParticipantsConfig) -> list[ExtraParticipant]:
    """Validate the extra participants' ids, templates and models (models trimmed)."""
    configured = {p.id for p in config.participants}
    enabled = {p.id for p in config.enabled_participants()}
    seen: set[str] = set()
    resolved: list[ExtraParticipant] = []
    for extra in requested:
        if not EXTRA_ID_PATTERN.fullmatch(extra.id):
            raise SettingsError(f"臨時參與者 id `{extra.id}` 格式不合法（需要符合 {EXTRA_ID_PATTERN.pattern}）")
        if extra.id in configured or extra.id in seen:
            raise SettingsError(f"臨時參與者 id `{extra.id}` 和其他參與者重複")
        seen.add(extra.id)
        if extra.template_id not in enabled:
            raise SettingsError(f"臨時參與者 `{extra.id}` 的範本 `{extra.template_id}` 不存在或已停用")
        model = None if extra.model is None else _model_name(extra.model, extra.id)
        resolved.append(extra.model_copy(update={"model": model}))
    return resolved


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
    extras = _resolve_extras(requested.extra_participants or [], config)
    extra_ids = {e.id for e in extras}
    unknown = [pid for pid in ids if pid not in enabled and pid not in extra_ids]
    if unknown:
        raise SettingsError(f"未知或已停用的參與者：{', '.join(unknown)}")
    extras = [e for e in extras if e.id in ids]  # only the ones taking part are recorded

    models: dict[str, str] = {}
    for pid, raw in (requested.models or {}).items():
        if pid not in ids:
            raise SettingsError(f"指定了模型的參與者 `{pid}` 不在這場討論的參與者中")
        models[pid] = _model_name(raw, pid)
    if len(ids) < MIN_PARTICIPANTS:
        raise SettingsError(f"討論需要至少 {MIN_PARTICIPANTS} 個參與者（目前選了 {len(ids)} 個）")

    speaking_order = requested.speaking_order or d.speaking_order
    if speaking_order not in SPEAKING_ORDERS:
        raise SettingsError(f"發言順序 `{speaking_order}` 尚未提供")

    judge = requested.judge or d.judge
    if "judge" in mode.uses_settings and judge not in JUDGES:
        raise SettingsError(f"共識裁定方式 `{judge}` 尚未提供")
    if "judge" in mode.uses_settings:
        availability = JUDGES[judge]().availability(backend_env())
        if not availability.available:
            raise SettingsError(f"共識裁定方式 `{judge}` 目前不可用：{availability.reason}")

    moderator_id: str | None = None
    if "moderator_id" in mode.uses_settings:
        moderator_id = requested.moderator_id or (d.moderator if d.moderator in ids else ids[0])
        if moderator_id not in ids:
            raise SettingsError(f"主持人 `{moderator_id}` 不在這場討論的參與者中")

    return DiscussionSettings(
        mode=requested.mode,
        participant_ids=ids,
        judge=judge,
        moderator_id=moderator_id,
        speaking_order=speaking_order,
        max_rounds=requested.max_rounds or d.max_rounds,
        turn_timeout_seconds=requested.turn_timeout_seconds or d.turn_timeout_seconds,
        jev_threshold=requested.jev_threshold if requested.jev_threshold is not None else d.jev_threshold,
        models=models,
        extra_participants=extras,
    )


def build_participants(settings: DiscussionSettings, config: ParticipantsConfig) -> list[ParticipantConfig]:
    """The discussion's participants in `participant_ids` order: configured participants
    with their `models` override, extra participants copied from their template, and
    display names made unique for this discussion (the participants file is unchanged).

    Raises SettingsError when an extra participant's template is gone (e.g. a converted
    ask whose template was removed from the participants file since)."""
    extras = {e.id: e for e in settings.extra_participants}
    built: list[ParticipantConfig] = []
    for pid in settings.participant_ids:
        if pid in extras:
            extra = extras[pid]
            try:
                template = config.get(extra.template_id)
            except KeyError:
                raise SettingsError(f"臨時參與者 `{pid}` 的範本 `{extra.template_id}` 不存在或已停用") from None
            participant = dataclasses.replace(template, id=pid, model=extra.model or template.model)
        else:
            participant = config.get(pid)
        if pid in settings.models:
            participant = dataclasses.replace(participant, model=settings.models[pid])
        built.append(participant)
    return _unique_names(built)


def _unique_names(participants: list[ParticipantConfig]) -> list[ParticipantConfig]:
    """Duplicated names get "（模型）" (or "（預設模型）"); names still duplicated after
    that get " 2", " 3", ... in list order (the first keeps its name)."""
    counts = Counter(p.display_name for p in participants)
    names = [
        f"{p.display_name}（{p.model or '預設模型'}）" if counts[p.display_name] > 1 else p.display_name
        for p in participants
    ]
    counts = Counter(names)
    taken = set(names)
    seen: set[str] = set()
    unique: list[str] = []
    for name in names:
        if counts[name] > 1 and name in seen:
            n = 2
            while f"{name} {n}" in taken:
                n += 1
            taken.add(f"{name} {n}")
            unique.append(f"{name} {n}")
        else:
            unique.append(name)
        seen.add(name)
    return [
        p if p.display_name == name else dataclasses.replace(p, display_name=name)
        for p, name in zip(participants, unique, strict=True)
    ]
