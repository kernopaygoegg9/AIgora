"""GET /api/options: discussion modes, consensus judges (with availability), speaking orders, defaults."""

from __future__ import annotations

from fastapi import HTTPException

from aigora.api.http_models import DefaultSettings, JudgeOption, ModeOption, OptionsResponse, SpeakingOrderOption
from aigora.config import ConfigError, Defaults, load_participants, participants_file_path
from aigora.discussion.modes import MODES
from aigora.discussion.orders import SPEAKING_ORDERS
from aigora.domain import MODE_IDS, SPEAKING_ORDER_IDS
from aigora.env import TYPESAFE_API_KEY, backend_env, has_typesafe_key


# Modes / orders whose class is not registered yet. TODO(ticket 04): consensus
# registers `ConsensusMode` in MODES; its own `uses_settings` then wins.
_PENDING_MODES: dict[str, tuple[str, frozenset[str]]] = {
    "consensus": (
        "共識討論",
        frozenset({
            "participant_ids", "speaking_order", "turn_timeout_seconds",
            "moderator_id", "judge", "max_rounds", "jev_threshold",
        }),
    ),
}
_PENDING_ORDER_NAMES = {"sequential": "依序"}  # interface only in v1


def _mode_options() -> list[ModeOption]:
    options = []
    for mode_id in MODE_IDS:
        if mode_id in MODES:
            name, uses = MODES[mode_id].name, MODES[mode_id].uses_settings
        else:
            name, uses = _PENDING_MODES[mode_id]
        options.append(ModeOption(id=mode_id, name=name, uses_settings=sorted(uses)))
    return options


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


def _judge_options(env: dict[str, str]) -> list[JudgeOption]:
    # TODO(ticket 04/08): once a judge registry exists, list it here and use each
    # judge's `availability(env)` instead of this table.
    jev_ok = has_typesafe_key(env)
    return [
        JudgeOption(id="stance_vote", name="主持人 + 全員表態", available=True),
        JudgeOption(
            id="jev",
            name="Jev 判斷 + 反問確認",
            available=jev_ok,
            unavailable_reason=None if jev_ok else f".env 沒有設定 {TYPESAFE_API_KEY}",
        ),
    ]


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
    return OptionsResponse(
        modes=_mode_options(),
        judges=_judge_options(backend_env()),
        speaking_orders=_speaking_order_options(),
        defaults=_default_settings(config.defaults),
    )
