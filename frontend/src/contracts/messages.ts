// WebSocket message types (spec "WebSocket 訊息").
//
// FROZEN after ticket 02. Tickets that need a new message type or field must
// stop and report instead of editing this file. (ui-redesign ticket 10
// deliberately added `models` / `extra_participants` to the start settings and
// the snapshot: spec "參與者與模型選擇".) The Python twin is
// `backend/aigora/api/messages.py` (read its docstring for the additions
// beyond the spec table); `backend/tests/test_ws_messages.py` checks that both
// define the same types and fields, so keep the one-field-per-line layout.

// --- vocabulary (see GLOSSARY.md) ---------------------------------------------

export type ModeId = 'ask' | 'consensus'
export type JudgeId = 'stance_vote' | 'jev'
export type SpeakingOrderId = 'parallel' | 'sequential'
export type Stance = 'AGREE' | 'DISAGREE'
export type FailureKind = 'not_available' | 'auth' | 'quota' | 'timeout' | 'crashed' | 'unknown'
export type TurnPurpose = 'turn' | 'draft' | 'final_result' | 'no_consensus_summary' | 'confirmation'
export type TurnStatus = 'ok' | 'failed' | 'timeout'
export type JudgeOutcome = 'not_reached' | 'confirm' | 'reached'
export type Outcome =
  | 'completed'
  | 'consensus'
  | 'no_consensus'
  | 'stopped'
  | 'insufficient_participants'
  | 'error'

// --- shared shapes --------------------------------------------------------------

/**
 * A participant that exists only in one discussion (臨時參與者), copied from the
 * configured participant `template_id`. `model` null: the template's model.
 * Its `id` (`^[a-z0-9][a-z0-9_-]{0,63}$`) also goes into `participant_ids`.
 */
export interface ExtraParticipant {
  id: string
  template_id: string
  model: string | null
}

/**
 * Settings sent with `start`; omitted / null fields are filled from `[defaults]`.
 * `models`: participant id -> model for this discussion. `extra_participants`:
 * definitions of the extra ids in `participant_ids`. Omitting both behaves like v1.
 */
export interface StartSettings {
  mode: ModeId
  participant_ids: string[]
  judge?: JudgeId | null
  moderator_id?: string | null
  speaking_order?: SpeakingOrderId | null
  max_rounds?: number | null
  turn_timeout_seconds?: number | null
  jev_threshold?: number | null
  models?: Record<string, string> | null
  extra_participants?: ExtraParticipant[] | null
}

/**
 * Full settings snapshot, locked when the discussion starts. The server always sends
 * `models` / `extra_participants` (empty in v1 records); optional here so code and
 * tests written against v1 still type-check.
 */
export interface DiscussionSettings {
  mode: ModeId
  participant_ids: string[]
  judge: JudgeId
  moderator_id: string | null
  speaking_order: SpeakingOrderId
  max_rounds: number
  turn_timeout_seconds: number
  jev_threshold: number
  models?: Record<string, string>
  extra_participants?: ExtraParticipant[]
}

export interface Capabilities {
  web_access: boolean
  streaming: boolean
}

/** `model`: the model actually used; `display_name`: unique within the discussion. */
export interface ParticipantSnapshot {
  id: string
  display_name: string
  adapter: string
  model: string | null
  /** Filename, served at /api/avatars/{avatar}. */
  avatar: string
  capabilities: Capabilities
}

/** Judge A fills `stances` (null = unparseable); judge B fills `probability` and `threshold`. */
export interface JudgeDetail {
  stances?: Record<string, Stance | null> | null
  probability?: number | null
  threshold?: number | null
}

export interface ConfirmationAnswer {
  participant_id: string
  agree: boolean
  reason: string
}

export interface ResultAnswer {
  participant_id: string
  status: TurnStatus
  text: string | null
}

/** `answers`: an ask's turns. `consensus`: the consensus text. `no_consensus`: final positions + disagreements. */
export interface DiscussionResult {
  kind: 'answers' | 'consensus' | 'no_consensus'
  text?: string | null
  answers?: ResultAnswer[] | null
}

// --- client -> server -----------------------------------------------------------

export interface StartMessage {
  type: 'start'
  question: string
  settings: StartSettings
  from_discussion_id?: string | null
}

export interface InterjectMessage {
  type: 'interject'
  text: string
}

export interface StopMessage {
  type: 'stop'
}

export type ClientMessage = StartMessage | InterjectMessage | StopMessage

// --- server -> client -----------------------------------------------------------

export interface ServerMessageBase {
  discussion_id: string
  seq: number
}

export interface DiscussionStartedMessage extends ServerMessageBase {
  type: 'discussion_started'
  question: string
  derived_from?: string | null
  settings: DiscussionSettings
  participants: ParticipantSnapshot[]
}

export interface RoundStartedMessage extends ServerMessageBase {
  type: 'round_started'
  round: number
}

export interface TurnStartedMessage extends ServerMessageBase {
  type: 'turn_started'
  round: number
  participant_id: string
  purpose?: TurnPurpose
}

export interface TurnDeltaMessage extends ServerMessageBase {
  type: 'turn_delta'
  round: number
  participant_id: string
  purpose?: TurnPurpose
  /** Appended to the text streamed so far. */
  text: string
}

export interface TurnCompletedMessage extends ServerMessageBase {
  type: 'turn_completed'
  round: number
  participant_id: string
  purpose?: TurnPurpose
  /** Full text. */
  text: string
  stance?: Stance | null
}

export interface TurnFailedMessage extends ServerMessageBase {
  type: 'turn_failed'
  round: number
  participant_id: string
  purpose?: TurnPurpose
  reason: string
  kind: FailureKind
}

export interface ParticipantRemovedMessage extends ServerMessageBase {
  type: 'participant_removed'
  participant_id: string
  reason: string
  round?: number | null
}

export interface ModeratorChangedMessage extends ServerMessageBase {
  type: 'moderator_changed'
  participant_id: string
  round?: number | null
}

export interface DraftCreatedMessage extends ServerMessageBase {
  type: 'draft_created'
  round: number
  text: string
}

export interface JudgeResultMessage extends ServerMessageBase {
  type: 'judge_result'
  round: number
  judge: JudgeId
  outcome: JudgeOutcome
  detail: JudgeDetail
}

export interface ConfirmationResultMessage extends ServerMessageBase {
  type: 'confirmation_result'
  round: number
  answers: ConfirmationAnswer[]
}

export interface InterjectionQueuedMessage extends ServerMessageBase {
  type: 'interjection_queued'
  text: string
  applies_to_round: number
}

export interface RoundCompletedMessage extends ServerMessageBase {
  type: 'round_completed'
  round: number
}

export interface DiscussionFinishedMessage extends ServerMessageBase {
  type: 'discussion_finished'
  outcome: Outcome
  result?: DiscussionResult | null
  reason?: string | null
}

export interface ErrorMessage {
  type: 'error'
  /** Null when no discussion has started yet. */
  discussion_id?: string | null
  seq: number
  message: string
}

export type ServerMessage =
  | DiscussionStartedMessage
  | RoundStartedMessage
  | TurnStartedMessage
  | TurnDeltaMessage
  | TurnCompletedMessage
  | TurnFailedMessage
  | ParticipantRemovedMessage
  | ModeratorChangedMessage
  | DraftCreatedMessage
  | JudgeResultMessage
  | ConfirmationResultMessage
  | InterjectionQueuedMessage
  | RoundCompletedMessage
  | DiscussionFinishedMessage
  | ErrorMessage
