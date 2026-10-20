// Discussion record JSON (GET /api/discussions/{id}). Python twin:
// `backend/aigora/record.py` (checked by backend/tests/test_ws_messages.py;
// keep one field per line).
import type {
  ConfirmationAnswer,
  DiscussionResult,
  DiscussionSettings,
  JudgeDetail,
  JudgeId,
  JudgeOutcome,
  Outcome,
  ParticipantSnapshot,
  Stance,
  TurnStatus,
} from './messages'

export interface RecordTurn {
  participant_id: string
  status: TurnStatus
  text: string | null
  stance: Stance | null
  started_at: string
  ended_at: string | null
  error: string | null
}

export interface RecordJudge {
  judge: JudgeId
  outcome: JudgeOutcome
  detail: JudgeDetail
}

export interface RecordRound {
  number: number
  turns: RecordTurn[]
  draft?: string | null
  // the round's final verdict
  judge?: RecordJudge | null
  // every verdict of the round in order (judge B: `confirm`, then the final one); older records lack it
  judge_history?: RecordJudge[]
  confirmations?: ConfirmationAnswer[] | null
}

export interface RecordInterjection {
  text: string
  at: string
  applies_to_round: number
}

export interface RecordRemoval {
  participant_id: string
  round: number
  reason: string
}

export interface RecordModeratorChange {
  round: number
  participant_id: string
}

export interface DiscussionRecord {
  schema_version: number
  id: string
  question: string
  created_at: string
  finished_at?: string | null
  settings: DiscussionSettings
  participants: ParticipantSnapshot[]
  derived_from?: string | null
  rounds: RecordRound[]
  interjections: RecordInterjection[]
  removed_participants: RecordRemoval[]
  moderator_changes: RecordModeratorChange[]
  outcome: Outcome | null
  result?: DiscussionResult | null
}
