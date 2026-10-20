// The global discussion store turns a stream of server messages into discussion
// state. Runs in Node (no browser page): feeds hand-written message sequences.
import { expect, test } from '@playwright/test'
import { createPinia, setActivePinia } from 'pinia'

import type { ServerMessage } from '../src/contracts/messages'
import type { DiscussionRecord } from '../src/contracts/record'
import { useDiscussionStore } from '../src/stores/discussion'

const D = 'd-1'

function fresh() {
  setActivePinia(createPinia())
  return useDiscussionStore()
}

const participants = [
  { id: 'a', display_name: 'A', adapter: 'fake', model: null, avatar: 'fake.png', capabilities: { web_access: true, streaming: true } },
  { id: 'b', display_name: 'B', adapter: 'fake', model: null, avatar: 'fake.png', capabilities: { web_access: false, streaming: false } },
  { id: 'c', display_name: 'C', adapter: 'fake', model: 'm', avatar: 'fake.png', capabilities: { web_access: true, streaming: true } },
]

const settings = {
  mode: 'consensus' as const,
  participant_ids: ['a', 'b', 'c'],
  judge: 'jev' as const,
  moderator_id: 'a',
  speaking_order: 'parallel' as const,
  max_rounds: 5,
  turn_timeout_seconds: 300,
  jev_threshold: 0.8,
}

// A consensus discussion that exercises every server message type.
function consensusScript(): ServerMessage[] {
  type Body = ServerMessage extends infer M ? (M extends ServerMessage ? Omit<M, 'seq' | 'discussion_id'> : never) : never
  const body: Body[] = [
    { type: 'discussion_started', question: 'Tabs or spaces?', derived_from: null, settings, participants },
    { type: 'round_started', round: 1 },
    { type: 'turn_started', round: 1, participant_id: 'a', purpose: 'turn' },
    { type: 'turn_started', round: 1, participant_id: 'b', purpose: 'turn' },
    { type: 'turn_started', round: 1, participant_id: 'c', purpose: 'turn' },
    { type: 'turn_delta', round: 1, participant_id: 'a', purpose: 'turn', text: 'Spa' },
    { type: 'turn_delta', round: 1, participant_id: 'a', purpose: 'turn', text: 'ces.' },
    { type: 'turn_completed', round: 1, participant_id: 'a', purpose: 'turn', text: 'Spaces.', stance: null },
    { type: 'turn_completed', round: 1, participant_id: 'b', purpose: 'turn', text: 'Tabs.', stance: null },
    { type: 'turn_failed', round: 1, participant_id: 'c', purpose: 'turn', reason: 'took too long', kind: 'timeout' },
    { type: 'turn_started', round: 1, participant_id: 'a', purpose: 'draft' },
    { type: 'turn_delta', round: 1, participant_id: 'a', purpose: 'draft', text: 'Draft: spa' },
    { type: 'turn_completed', round: 1, participant_id: 'a', purpose: 'draft', text: 'Draft: spaces', stance: null },
    { type: 'draft_created', round: 1, text: 'Draft: spaces' },
    { type: 'round_completed', round: 1 },
    { type: 'interjection_queued', text: 'Think about Go.', applies_to_round: 2 },
    { type: 'round_started', round: 2 },
    { type: 'turn_started', round: 2, participant_id: 'a' },
    { type: 'turn_started', round: 2, participant_id: 'b' },
    { type: 'turn_started', round: 2, participant_id: 'c' },
    { type: 'turn_completed', round: 2, participant_id: 'a', text: 'OK\nSTANCE: AGREE', stance: 'AGREE' },
    { type: 'turn_completed', round: 2, participant_id: 'b', text: 'Fine\nSTANCE: AGREE', stance: 'AGREE' },
    { type: 'turn_failed', round: 2, participant_id: 'c', reason: 'boom', kind: 'crashed' },
    { type: 'participant_removed', participant_id: 'c', reason: 'failed 2 rounds in a row', round: 2 },
    { type: 'turn_failed', round: 2, participant_id: 'a', purpose: 'draft', reason: 'quota', kind: 'quota' },
    { type: 'moderator_changed', participant_id: 'b', round: 2 },
    { type: 'turn_started', round: 2, participant_id: 'b', purpose: 'draft' },
    { type: 'turn_completed', round: 2, participant_id: 'b', purpose: 'draft', text: 'Draft 2', stance: null },
    { type: 'draft_created', round: 2, text: 'Draft 2' },
    { type: 'judge_result', round: 2, judge: 'jev', outcome: 'confirm', detail: { probability: 0.91, threshold: 0.8 } },
    {
      type: 'confirmation_result',
      round: 2,
      answers: [
        { participant_id: 'a', agree: true, reason: 'yes' },
        { participant_id: 'b', agree: true, reason: 'sure' },
      ],
    },
    { type: 'round_completed', round: 2 },
    { type: 'discussion_finished', outcome: 'consensus', result: { kind: 'consensus', text: 'Use spaces.' }, reason: null },
  ]
  return body.map((m, i) => ({ ...m, discussion_id: D, seq: i + 1 }) as ServerMessage)
}

test('applies a whole consensus discussion', () => {
  const store = fresh()
  store.applyMessages(consensusScript())

  expect(store.discussionId).toBe(D)
  expect(store.status).toBe('finished')
  expect(store.question).toBe('Tabs or spaces?')
  expect(store.settings?.judge).toBe('jev')
  expect(store.participants.map((p) => p.id)).toEqual(['a', 'b', 'c'])
  expect(store.participantById('b')?.capabilities.web_access).toBe(false)
  expect(store.activeParticipantIds).toEqual(['a', 'b'])
  expect(store.moderatorId).toBe('b')
  expect(store.moderatorChanges).toEqual([{ participantId: 'b', round: 2 }])
  expect(store.removed).toEqual([{ participantId: 'c', reason: 'failed 2 rounds in a row', round: 2 }])
  expect(store.interjections).toEqual([{ text: 'Think about Go.', appliesToRound: 2 }])

  expect(store.rounds.map((r) => [r.number, r.status])).toEqual([
    [1, 'completed'],
    [2, 'completed'],
  ])
  const [r1, r2] = store.rounds
  expect(r1.turns.map((t) => [t.participantId, t.status, t.text, t.stance])).toEqual([
    ['a', 'ok', 'Spaces.', null],
    ['b', 'ok', 'Tabs.', null],
    ['c', 'timeout', '', null],
  ])
  expect(r1.turns[2].failure).toEqual({ kind: 'timeout', reason: 'took too long' })
  expect(r1.extraCalls.map((t) => [t.participantId, t.purpose, t.status, t.text])).toEqual([
    ['a', 'draft', 'ok', 'Draft: spaces'],
  ])
  expect(r1.draft).toBe('Draft: spaces')
  expect(r1.judge).toBeNull()

  expect(r2.turns.map((t) => [t.participantId, t.status, t.stance])).toEqual([
    ['a', 'ok', 'AGREE'],
    ['b', 'ok', 'AGREE'],
    ['c', 'failed', null],
  ])
  expect(r2.extraCalls.map((t) => [t.participantId, t.status])).toEqual([
    ['a', 'failed'],
    ['b', 'ok'],
  ])
  expect(r2.draft).toBe('Draft 2')
  expect(r2.judge).toEqual({ judge: 'jev', outcome: 'confirm', detail: { probability: 0.91, threshold: 0.8 } })
  expect(r2.confirmations?.map((a) => a.participant_id)).toEqual(['a', 'b'])

  expect(store.outcome).toBe('consensus')
  expect(store.result).toEqual({ kind: 'consensus', text: 'Use spaces.' })
  expect(store.currentRound?.number).toBe(2)
})

test('shows streaming text while a turn is in progress', () => {
  const store = fresh()
  store.applyMessages(consensusScript().slice(0, 7))
  expect(store.status).toBe('running')
  const turn = store.rounds[0].turns.find((t) => t.participantId === 'a')!
  expect(turn.status).toBe('running')
  expect(turn.text).toBe('Spaces.')
  expect(store.rounds[0].turns.find((t) => t.participantId === 'b')!.text).toBe('')
})

test('ignores repeated seq numbers and messages of another discussion', () => {
  const store = fresh()
  const script = consensusScript().slice(0, 7)
  store.applyMessages(script)
  store.applyMessage(script[6]) // same delta again
  store.applyMessage({ type: 'turn_delta', discussion_id: 'other', seq: 99, round: 1, participant_id: 'a', text: '!!' })
  expect(store.rounds[0].turns[0].text).toBe('Spaces.')
  expect(store.lastSeq).toBe(7)
})

test('a new discussion_started replaces the previous discussion', () => {
  const store = fresh()
  store.applyMessages(consensusScript())
  store.applyMessage({
    type: 'discussion_started',
    discussion_id: 'd-2',
    seq: 1,
    question: 'Next?',
    derived_from: D,
    settings: { ...settings, mode: 'ask', participant_ids: ['a', 'b'] },
    participants: participants.slice(0, 2),
  })
  expect(store.discussionId).toBe('d-2')
  expect(store.derivedFrom).toBe(D)
  expect(store.status).toBe('running')
  expect(store.rounds).toEqual([])
  expect(store.outcome).toBeNull()
  expect(store.activeParticipantIds).toEqual(['a', 'b'])
})

test('an ask finishes with every answer as the result', () => {
  const store = fresh()
  const msgs: ServerMessage[] = [
    { type: 'discussion_started', discussion_id: D, seq: 1, question: 'Q', settings: { ...settings, mode: 'ask' }, participants },
    { type: 'round_started', discussion_id: D, seq: 2, round: 1 },
    { type: 'turn_completed', discussion_id: D, seq: 3, round: 1, participant_id: 'a', text: 'A says' },
    { type: 'round_completed', discussion_id: D, seq: 4, round: 1 },
    {
      type: 'discussion_finished',
      discussion_id: D,
      seq: 5,
      outcome: 'completed',
      result: { kind: 'answers', answers: [{ participant_id: 'a', status: 'ok', text: 'A says' }] },
    },
  ]
  store.applyMessages(msgs)
  expect(store.rounds[0].turns).toHaveLength(1) // a turn_completed without turn_started still shows
  expect(store.rounds[0].turns[0].text).toBe('A says')
  expect(store.outcome).toBe('completed')
  expect(store.result?.answers?.[0].text).toBe('A says')
})

test('records errors, including ones before any discussion started', () => {
  const store = fresh()
  store.applyMessage({ type: 'error', discussion_id: null, seq: 1, message: 'unknown participant x' })
  expect(store.errors).toEqual(['unknown participant x'])
  expect(store.status).toBe('idle')
})

test('finishing as insufficient_participants keeps the reason', () => {
  const store = fresh()
  store.applyMessages([
    { type: 'discussion_started', discussion_id: D, seq: 1, question: 'Q', settings, participants },
    { type: 'discussion_finished', discussion_id: D, seq: 2, outcome: 'insufficient_participants', result: null, reason: 'only A is left' },
  ])
  expect(store.outcome).toBe('insufficient_participants')
  expect(store.finishReason).toBe('only A is left')
  expect(store.result).toBeNull()
})

test('reset returns to idle', () => {
  const store = fresh()
  store.applyMessages(consensusScript())
  store.reset()
  expect(store.status).toBe('idle')
  expect(store.discussionId).toBeNull()
  expect(store.rounds).toEqual([])
})

test('loads a saved discussion record read-only', () => {
  const store = fresh()
  const record: DiscussionRecord = {
    schema_version: 1,
    id: 'old',
    question: 'Tabs or spaces?',
    created_at: '2026-10-20T10:00:00Z',
    finished_at: '2026-10-20T10:05:00Z',
    settings,
    participants,
    derived_from: null,
    rounds: [
      {
        number: 1,
        turns: [
          { participant_id: 'a', status: 'ok', text: 'Spaces.', stance: null, started_at: 't', ended_at: 't', error: null },
          { participant_id: 'c', status: 'timeout', text: null, stance: null, started_at: 't', ended_at: 't', error: 'slow' },
        ],
        draft: 'Draft',
        judge: null,
        confirmations: null,
      },
      {
        number: 2,
        turns: [{ participant_id: 'a', status: 'ok', text: 'OK', stance: 'AGREE', started_at: 't', ended_at: 't', error: null }],
        draft: 'Draft 2',
        judge: { judge: 'stance_vote', outcome: 'reached', detail: { stances: { a: 'AGREE' } } },
      },
    ],
    interjections: [{ text: 'hey', at: 't', applies_to_round: 2 }],
    removed_participants: [{ participant_id: 'c', round: 2, reason: 'failed twice' }],
    moderator_changes: [{ round: 2, participant_id: 'b' }],
    outcome: 'consensus',
    result: { kind: 'consensus', text: 'Draft 2' },
  }
  store.loadRecord(record)
  expect(store.readOnly).toBe(true)
  expect(store.status).toBe('finished')
  expect(store.discussionId).toBe('old')
  expect(store.activeParticipantIds).toEqual(['a', 'b'])
  expect(store.moderatorId).toBe('b')
  expect(store.rounds[0].turns[1]).toMatchObject({ status: 'timeout', text: '', failure: { kind: 'timeout', reason: 'slow' } })
  expect(store.rounds[1].judge?.outcome).toBe('reached')
  expect(store.rounds[1].status).toBe('completed')
  expect(store.interjections).toEqual([{ text: 'hey', appliesToRound: 2 }])
  expect(store.removed).toEqual([{ participantId: 'c', reason: 'failed twice', round: 2 }])
  expect(store.outcome).toBe('consensus')

  // live messages do not change a read-only record
  store.applyMessage({ type: 'round_started', discussion_id: 'old', seq: 100, round: 3 })
  expect(store.rounds).toHaveLength(2)
})
