// Display labels shared by the live discussion page and the read-only record views.
// Wording follows GLOSSARY.md (討論模式、共識裁定方式、表態、取得共識).
import type { JudgeId, JudgeOutcome, ModeId, Outcome, Stance } from '../contracts/messages'

export const MODE_LABELS: Record<ModeId, string> = { ask: '提問', consensus: '共識討論' }

export const JUDGE_LABELS: Record<JudgeId, string> = {
  stance_vote: '主持人 + 全員表態',
  jev: 'Jev 判斷 + 反問確認',
}

// One judge verdict (`judge_result` / a record's `judge`), per consensus judge.
const JUDGE_OUTCOME_LABELS: Record<JudgeId, Record<JudgeOutcome, string>> = {
  stance_vote: {
    reached: '全員同意，取得共識',
    not_reached: '未取得共識',
    confirm: '需要反問確認',
  },
  jev: {
    reached: '反問全員同意，取得共識',
    not_reached: '未取得共識',
    confirm: '達到門檻，需要反問確認',
  },
}

export function judgeOutcomeLabel(judge: JudgeId, outcome: JudgeOutcome): string {
  return JUDGE_OUTCOME_LABELS[judge]?.[outcome] ?? outcome
}

export const OUTCOME_LABELS: Record<Outcome, string> = {
  completed: '已完成',
  consensus: '取得共識',
  no_consensus: '未取得共識',
  stopped: '已停止',
  insufficient_participants: '參與者不足',
  error: '發生錯誤',
}

export function outcomeLabel(outcome: Outcome | null): string {
  return outcome ? OUTCOME_LABELS[outcome] : '進行中'
}

/** A participant's 表態 on the draft; none (failed turn / no valid stance line) counts as disagreeing. */
export function stanceLabel(stance: Stance | null | undefined): string {
  if (stance === 'AGREE') return '同意'
  if (stance === 'DISAGREE') return '不同意'
  return '未表態（視為不同意）'
}

/** A confirmation answer (judge B's 反問確認). */
export function agreeLabel(agree: boolean): string {
  return agree ? '同意' : '不同意'
}
