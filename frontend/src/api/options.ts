import type { OptionsResponse } from '../contracts/http'

/** GET /api/options: modes, consensus judges (with availability), speaking orders, defaults. */
export async function fetchOptions(): Promise<OptionsResponse> {
  const response = await fetch('/api/options')
  if (!response.ok) throw new Error(`無法取得討論選項（HTTP ${response.status}）`)
  return (await response.json()) as OptionsResponse
}
