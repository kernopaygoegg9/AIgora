// Display labels for history / record views: the shared labels (../labels.ts) plus formatting.
export {
  JUDGE_LABELS,
  MODE_LABELS,
  OUTCOME_LABELS,
  agreeLabel,
  judgeOutcomeLabel,
  outcomeLabel,
  stanceLabel,
} from '../labels'

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return ''
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString('zh-TW', { hour12: false })
}
