// Display labels for history / record views (terms from GLOSSARY.md).
import type { JudgeId, JudgeOutcome, ModeId, Outcome, Stance } from '../../contracts/messages'

export const MODE_LABELS: Record<ModeId, string> = { ask: '提問', consensus: '共識討論' }

export const JUDGE_LABELS: Record<JudgeId, string> = {
  stance_vote: '主持人 + 全員表態',
  jev: 'Jev 判斷 + 反問確認',
}

export const JUDGE_OUTCOME_LABELS: Record<JudgeOutcome, string> = {
  not_reached: '未達成共識',
  confirm: '需反問確認',
  reached: '已達成共識',
}

export const OUTCOME_LABELS: Record<Outcome, string> = {
  completed: '已完成',
  consensus: '達成共識',
  no_consensus: '未達共識',
  stopped: '已停止',
  insufficient_participants: '參與者不足',
  error: '發生錯誤',
}

export function outcomeLabel(outcome: Outcome | null): string {
  return outcome ? OUTCOME_LABELS[outcome] : '進行中'
}

export function stanceLabel(stance: Stance | null | undefined): string {
  if (stance === 'AGREE') return '同意'
  if (stance === 'DISAGREE') return '不同意'
  return '無法解析'
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString('zh-TW', { hour12: false })
}
