// HTTP API response bodies. Python twin: `backend/aigora/api/http_models.py`
// (checked by backend/tests/test_ws_messages.py; keep one field per line).
//
// GET /api/participants      -> ParticipantInfo[]
// GET /api/options           -> OptionsResponse
// GET /api/discussions       -> DiscussionSummary[] (newest first)
// GET /api/discussions/{id}  -> DiscussionRecord (./record.ts)
// GET /api/avatars/{file}    -> image
import type { Capabilities, JudgeId, ModeId, Outcome, SpeakingOrderId } from './messages'

export interface ParticipantInfo {
  id: string
  display_name: string
  adapter: string
  model: string | null
  avatar: string
  capabilities: Capabilities
  available: boolean
  unavailable_reason?: string | null
}

export interface ModeOption {
  id: ModeId
  name: string
  uses_settings: string[]
}

export interface JudgeOption {
  id: JudgeId
  name: string
  available: boolean
  unavailable_reason?: string | null
}

export interface SpeakingOrderOption {
  id: SpeakingOrderId
  name: string
  implemented: boolean
}

export interface DefaultSettings {
  mode: ModeId
  judge: JudgeId
  speaking_order: SpeakingOrderId
  moderator_id: string
  max_rounds: number
  turn_timeout_seconds: number
  jev_threshold: number
}

export interface OptionsResponse {
  modes: ModeOption[]
  judges: JudgeOption[]
  speaking_orders: SpeakingOrderOption[]
  defaults: DefaultSettings
}

export interface DiscussionSummary {
  id: string
  question: string
  mode: ModeId
  created_at: string
  outcome: Outcome | null
}

export function avatarUrl(avatar: string): string {
  return `/api/avatars/${encodeURIComponent(avatar)}`
}
