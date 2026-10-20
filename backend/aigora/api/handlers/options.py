"""GET /api/options: discussion modes, consensus judges (with availability), speaking orders, defaults."""

from __future__ import annotations

from collections.abc import Mapping

from fastapi import HTTPException

from aigora.api.http_models import DefaultSettings, JudgeOption, ModeOption, OptionsResponse, SpeakingOrderOption
from aigora.config import ConfigError, Defaults, load_participants, participants_file_path
from aigora.discussion.judges import JUDGES
from aigora.discussion.modes import MODES
from aigora.discussion.orders import SPEAKING_ORDERS
from aigora.domain import JUDGE_IDS, MODE_IDS, SPEAKING_ORDER_IDS
from aigora.env import TYPESAFE_API_KEY, backend_env, has_typesafe_key

# Shown for identifiers whose class is not registered yet.
_PENDING_ORDER_NAMES = {"sequential": "依序"}  # interface only in v1
_PENDING_JUDGE_NAMES = {"jev": "Jev 判斷 + 反問確認"}  # ticket 08 registers JevJudge in JUDGES


def _mode_options() -> list[ModeOption]:
    return [
        ModeOption(id=mode_id, name=MODES[mode_id].name, uses_settings=sorted(MODES[mode_id].uses_settings))
        for mode_id in MODE_IDS
        if mode_id in MODES
    ]


def _judge_option(judge_id: str, env: Mapping[str, str]) -> JudgeOption:
    judge = JUDGES.get(judge_id)
    if judge is not None:
        availability = judge().availability(env)
        available, reason, name = availability.available, availability.reason, judge.name
    elif judge_id == "jev":
        # Until ticket 08 registers judge B: unavailable without a key, and (not built) even with one.
        name = _PENDING_JUDGE_NAMES[judge_id]
        available = False
        reason = f".env 沒有設定 {TYPESAFE_API_KEY}" if not has_typesafe_key(env) else "方式 B 尚未提供"
    else:
        name, available, reason = judge_id, False, "尚未提供"
    return JudgeOption(
        id=judge_id, name=name, available=available, unavailable_reason=None if available else reason
    )


def _speaking_order_options() -> list[SpeakingOrderOption]:
    options = []
    for order_id in SPEAKING_ORDER_IDS:
        order = SPEAKING_ORDERS.get(order_id)
        options.append(
            SpeakingOrderOption(
                id=order_id,
                name=order.name if order else _PENDING_ORDER_NAMES[order_id],
                implemented=bool(order and order.implemented),
            )
        )
    return options


def _default_settings(d: Defaults) -> DefaultSettings:
    return DefaultSettings(
        mode=d.mode,
        judge=d.judge,
        speaking_order=d.speaking_order,
        moderator_id=d.moderator,
        max_rounds=d.max_rounds,
        turn_timeout_seconds=d.turn_timeout_seconds,
        jev_threshold=d.jev_threshold,
    )


async def get_options() -> OptionsResponse:
    try:
        config = load_participants(participants_file_path())
    except ConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from None
    env = backend_env()
    return OptionsResponse(
        modes=_mode_options(),
        judges=[_judge_option(judge_id, env) for judge_id in JUDGE_IDS],
        speaking_orders=_speaking_order_options(),
        defaults=_default_settings(config.defaults),
    )
