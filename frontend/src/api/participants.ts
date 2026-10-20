import type { ParticipantInfo } from '../contracts/http'

/** GET /api/participants: enabled participants with capabilities and availability. */
export async function fetchParticipants(): Promise<ParticipantInfo[]> {
  const response = await fetch('/api/participants')
  if (!response.ok) throw new Error(`無法取得參與者清單（HTTP ${response.status}）`)
  return (await response.json()) as ParticipantInfo[]
}
