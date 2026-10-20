import type { DiscussionSummary } from '../contracts/http'
import type { DiscussionRecord } from '../contracts/record'

/** GET /api/discussions: every saved discussion, newest first (outcome null = in progress). */
export async function fetchDiscussions(): Promise<DiscussionSummary[]> {
  const response = await fetch('/api/discussions')
  if (!response.ok) throw new Error(`無法取得討論列表（HTTP ${response.status}）`)
  return (await response.json()) as DiscussionSummary[]
}

/** GET /api/discussions/{id}: the full discussion record. */
export async function fetchDiscussion(id: string): Promise<DiscussionRecord> {
  const response = await fetch(`/api/discussions/${encodeURIComponent(id)}`)
  if (response.status === 404) throw new Error('找不到這場討論')
  if (!response.ok) throw new Error(`無法取得討論紀錄（HTTP ${response.status}）`)
  return (await response.json()) as DiscussionRecord
}
