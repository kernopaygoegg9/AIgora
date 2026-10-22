// Global discussion store. HOT FILE: created empty by ticket 01; ticket 02
// filled in the WebSocket event handling. FROZEN: other tickets must not edit
// it (stop and report if it is not enough).
//
// The store holds no discussion logic: it only applies server messages
// (`applyMessage`) or a saved record (`loadRecord`) to state that pages render.
// Sending messages / owning the WebSocket lives in `src/api/discussionSocket.ts`.
import { defineStore } from 'pinia'

import type {
  ConfirmationAnswer,
  DiscussionResult,
  DiscussionSettings,
  FailureKind,
  JudgeDetail,
  JudgeId,
  JudgeOutcome,
  Outcome,
  ParticipantSnapshot,
  ServerMessage,
  Stance,
  TurnPurpose,
} from '../contracts/messages'
import type { DiscussionRecord } from '../contracts/record'

export type DiscussionStatus = 'idle' | 'running' | 'finished'
export type TurnStateStatus = 'running' | 'ok' | 'failed' | 'timeout'

export interface TurnState {
  round: number
  participantId: string
  /** 'turn' for normal turns; extra calls (moderator draft etc.) live in `RoundState.extraCalls`. */
  purpose: TurnPurpose
  status: TurnStateStatus
  /** Streamed text so far, or the full text once completed. */
  text: string
  stance: Stance | null
  failure: { kind: FailureKind; reason: string } | null
}

export interface JudgeState {
  judge: JudgeId
  outcome: JudgeOutcome
  detail: JudgeDetail
}

export interface RoundState {
  number: number
  status: 'running' | 'completed'
  /** Normal turns, in the order they started. */
  turns: TurnState[]
  /** Extra calls made after the turns (purpose != 'turn'), in the order they started. */
  extraCalls: TurnState[]
  draft: string | null
  judge: JudgeState | null
  confirmations: ConfirmationAnswer[] | null
}

export interface RemovedParticipant {
  participantId: string
  reason: string
  round: number | null
}

export interface ModeratorChange {
  participantId: string
  round: number | null
}

export interface Interjection {
  text: string
  appliesToRound: number
}

interface State {
  discussionId: string | null
  /** True when showing a saved record (history); live messages are then ignored. */
  readOnly: boolean
  status: DiscussionStatus
  lastSeq: number
  question: string
  derivedFrom: string | null
  settings: DiscussionSettings | null
  participants: ParticipantSnapshot[]
  activeParticipantIds: string[]
  moderatorId: string | null
  moderatorChanges: ModeratorChange[]
  removed: RemovedParticipant[]
  interjections: Interjection[]
  rounds: RoundState[]
  outcome: Outcome | null
  result: DiscussionResult | null
  finishReason: string | null
  /** `error` messages, oldest first. */
  errors: string[]
}

function initialState(): State {
  return {
    discussionId: null,
    readOnly: false,
    status: 'idle',
    lastSeq: 0,
    question: '',
    derivedFrom: null,
    settings: null,
    participants: [],
    activeParticipantIds: [],
    moderatorId: null,
    moderatorChanges: [],
    removed: [],
    interjections: [],
    rounds: [],
    outcome: null,
    result: null,
    finishReason: null,
    errors: [],
  }
}

function newRound(number: number): RoundState {
  return {
    number,
    status: 'running',
    turns: [],
    extraCalls: [],
    draft: null,
    judge: null,
    confirmations: null,
  }
}

function newTurn(round: number, participantId: string, purpose: TurnPurpose): TurnState {
  return { round, participantId, purpose, status: 'running', text: '', stance: null, failure: null }
}

export const useDiscussionStore = defineStore('discussion', {
  state: initialState,

  getters: {
    currentRound(state): RoundState | null {
      return state.rounds.length ? state.rounds[state.rounds.length - 1] : null
    },
    participantById(state) {
      return (id: string): ParticipantSnapshot | undefined =>
        state.participants.find((p) => p.id === id)
    },
    roundByNumber(state) {
      return (n: number): RoundState | undefined => state.rounds.find((r) => r.number === n)
    },
  },

  actions: {
    reset() {
      this.$patch((s) => Object.assign(s, initialState()))
    },

    applyMessages(messages: ServerMessage[]) {
      for (const message of messages) this.applyMessage(message)
    },

    applyMessage(msg: ServerMessage) {
      if (this.readOnly) return

      if (msg.type === 'error') {
        if (msg.discussion_id && this.discussionId && msg.discussion_id !== this.discussionId)
          return
        this.errors.push(msg.message)
        return
      }

      if (msg.type === 'discussion_started') {
        this.reset()
        this.discussionId = msg.discussion_id
        this.lastSeq = msg.seq
        this.status = 'running'
        this.question = msg.question
        this.derivedFrom = msg.derived_from ?? null
        this.settings = msg.settings
        this.participants = msg.participants
        this.activeParticipantIds = [...msg.settings.participant_ids]
        this.moderatorId = msg.settings.moderator_id
        return
      }

      if (msg.discussion_id !== this.discussionId) return
      if (msg.seq <= this.lastSeq) return // duplicate / out of date
      this.lastSeq = msg.seq

      switch (msg.type) {
        case 'round_started':
          this.ensureRound(msg.round).status = 'running'
          break
        case 'turn_started': {
          const turn = this.ensureTurn(msg.round, msg.participant_id, msg.purpose ?? 'turn', true)
          Object.assign(turn, { status: 'running', text: '', stance: null, failure: null })
          break
        }
        case 'turn_delta': {
          const turn = this.ensureTurn(msg.round, msg.participant_id, msg.purpose ?? 'turn')
          turn.status = 'running'
          turn.text += msg.text
          break
        }
        case 'turn_completed': {
          const turn = this.ensureTurn(msg.round, msg.participant_id, msg.purpose ?? 'turn')
          Object.assign(turn, {
            status: 'ok',
            text: msg.text,
            stance: msg.stance ?? null,
            failure: null,
          })
          break
        }
        case 'turn_failed': {
          const turn = this.ensureTurn(msg.round, msg.participant_id, msg.purpose ?? 'turn')
          turn.status = msg.kind === 'timeout' ? 'timeout' : 'failed'
          turn.failure = { kind: msg.kind, reason: msg.reason }
          break
        }
        case 'participant_removed':
          this.activeParticipantIds = this.activeParticipantIds.filter(
            (id) => id !== msg.participant_id,
          )
          this.removed.push({
            participantId: msg.participant_id,
            reason: msg.reason,
            round: msg.round ?? this.currentRound?.number ?? null,
          })
          break
        case 'moderator_changed':
          this.moderatorId = msg.participant_id
          this.moderatorChanges.push({
            participantId: msg.participant_id,
            round: msg.round ?? this.currentRound?.number ?? null,
          })
          break
        case 'draft_created':
          this.ensureRound(msg.round).draft = msg.text
          break
        case 'judge_result':
          this.ensureRound(msg.round).judge = {
            judge: msg.judge,
            outcome: msg.outcome,
            detail: msg.detail,
          }
          break
        case 'confirmation_result':
          this.ensureRound(msg.round).confirmations = msg.answers
          break
        case 'interjection_queued':
          this.interjections.push({ text: msg.text, appliesToRound: msg.applies_to_round })
          break
        case 'round_completed':
          this.ensureRound(msg.round).status = 'completed'
          break
        case 'discussion_finished':
          this.status = 'finished'
          this.outcome = msg.outcome
          this.result = msg.result ?? null
          this.finishReason = msg.reason ?? null
          break
      }
    },

    /** Show a saved discussion record (history, read-only). Call `reset()` before going live again. */
    loadRecord(record: DiscussionRecord) {
      this.reset()
      const removedIds = new Set(record.removed_participants.map((r) => r.participant_id))
      const lastChange = record.moderator_changes[record.moderator_changes.length - 1]
      Object.assign(this, {
        discussionId: record.id,
        readOnly: true,
        status: 'finished',
        question: record.question,
        derivedFrom: record.derived_from ?? null,
        settings: record.settings,
        participants: record.participants,
        activeParticipantIds: record.settings.participant_ids.filter((id) => !removedIds.has(id)),
        moderatorId: lastChange ? lastChange.participant_id : record.settings.moderator_id,
        moderatorChanges: record.moderator_changes.map((c) => ({
          participantId: c.participant_id,
          round: c.round,
        })),
        removed: record.removed_participants.map((r) => ({
          participantId: r.participant_id,
          reason: r.reason,
          round: r.round,
        })),
        interjections: record.interjections.map((i) => ({
          text: i.text,
          appliesToRound: i.applies_to_round,
        })),
        rounds: record.rounds.map((r): RoundState => ({
          number: r.number,
          status: 'completed',
          turns: r.turns.map((t): TurnState => ({
            round: r.number,
            participantId: t.participant_id,
            purpose: 'turn',
            status: t.status,
            text: t.text ?? '',
            stance: t.stance,
            failure:
              t.status === 'ok'
                ? null
                : { kind: t.status === 'timeout' ? 'timeout' : 'unknown', reason: t.error ?? '' },
          })),
          extraCalls: [],
          draft: r.draft ?? null,
          judge: r.judge ?? null,
          confirmations: r.confirmations ?? null,
        })),
        outcome: record.outcome,
        result: record.result ?? null,
      } satisfies Partial<State>)
    },

    // --- internal helpers (not for pages) ---

    ensureRound(number: number): RoundState {
      let round = this.rounds.find((r) => r.number === number)
      if (!round) {
        round = newRound(number)
        this.rounds.push(round)
        this.rounds.sort((a, b) => a.number - b.number)
        round = this.rounds.find((r) => r.number === number)!
      }
      return round
    },

    ensureTurn(
      roundNumber: number,
      participantId: string,
      purpose: TurnPurpose,
      starting = false,
    ): TurnState {
      const round = this.ensureRound(roundNumber)
      const list = purpose === 'turn' ? round.turns : round.extraCalls
      // Normal turns: one entry per participant per round. Extra calls: one entry per
      // call (each turn_started opens a new one), later messages update the latest.
      let turn =
        purpose === 'turn'
          ? list.find((t) => t.participantId === participantId)
          : starting
            ? undefined
            : [...list]
                .reverse()
                .find((t) => t.participantId === participantId && t.purpose === purpose)
      if (!turn) {
        list.push(newTurn(roundNumber, participantId, purpose))
        turn = list[list.length - 1]
      }
      return turn
    },
  },
})
