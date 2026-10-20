"""Shared vocabulary (identifiers and enums) used by the contracts. See GLOSSARY.md."""

from typing import Literal, get_args

# 討論模式
ModeId = Literal["ask", "consensus"]
# 共識裁定方式: A = stance_vote (主持人 + 全員表態), B = jev (Jev 判斷 + 反問確認)
JudgeId = Literal["stance_vote", "jev"]
# 發言順序 (sequential: interface only in v1)
SpeakingOrderId = Literal["parallel", "sequential"]

# 表態
Stance = Literal["AGREE", "DISAGREE"]

# Adapter failure kinds (also `turn_failed.kind`).
FailureKind = Literal["not_available", "auth", "quota", "timeout", "crashed", "unknown"]

# Why the engine calls a participant: a normal turn, or an extra call
# requested by the discussion mode.
TurnPurpose = Literal["turn", "draft", "final_result", "no_consensus_summary", "confirmation"]

# Turn status in the discussion record.
TurnStatus = Literal["ok", "failed", "timeout"]

# `judge_result.outcome`
JudgeOutcome = Literal["not_reached", "confirm", "reached"]

# `discussion_finished.outcome` and the record's `outcome`.
Outcome = Literal["completed", "consensus", "no_consensus", "stopped", "insufficient_participants", "error"]

MODE_IDS: tuple[str, ...] = get_args(ModeId)
JUDGE_IDS: tuple[str, ...] = get_args(JudgeId)
SPEAKING_ORDER_IDS: tuple[str, ...] = get_args(SpeakingOrderId)
FAILURE_KINDS: tuple[str, ...] = get_args(FailureKind)
TURN_PURPOSES: tuple[str, ...] = get_args(TurnPurpose)
OUTCOMES: tuple[str, ...] = get_args(Outcome)
