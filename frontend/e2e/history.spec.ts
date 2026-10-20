import { expect, test } from '@playwright/test'

import type { DiscussionSummary } from '../src/contracts/http'
import type { DiscussionRecord } from '../src/contracts/record'

// History (歷史清單) end to end: real backend with Fake Adapter participants, plus
// stubbed records for content that only later tickets produce (drafts, verdicts, ...).

test('a finished ask can be found in the history and opened read-only', async ({ page }) => {
  const question = `History check ${Date.now()}`
  await page.goto('/')
  await page.getByLabel('問題').fill(question)
  await page.getByRole('checkbox', { name: 'Fake A' }).check()
  await page.getByRole('checkbox', { name: 'Fake B' }).check()
  await page.getByRole('button', { name: '開始討論' }).click()
  await expect(page.getByTestId('discussion-status')).toHaveText('已結束')

  await page.getByRole('link', { name: '歷史' }).click()
  const row = page.getByTestId('history-item').filter({ hasText: question })
  await expect(row).toHaveCount(1)
  await expect(row).toContainText('提問')
  await expect(row.getByTestId('history-outcome')).toHaveText('已完成')
  // Newest first: the discussion just finished is on top.
  await expect(page.getByTestId('history-item').first()).toContainText(question)

  await row.getByRole('link').click()
  await expect(page).toHaveURL(/\/discussions\/\d{8}-\d{6}-[0-9a-f]{6}$/)
  const view = page.getByTestId('record-view')
  await expect(view.getByTestId('record-question')).toHaveText(question)
  await expect(view.getByTestId('record-outcome')).toHaveText('已完成')
  const card = (name: string) => view.getByTestId('turn-card').filter({ hasText: name })
  await expect(card('Fake A').getByTestId('turn-text')).toHaveText('Fake A: reply for round 1.')
  await expect(card('Fake B').getByTestId('turn-text')).toHaveText('Fake B: reply for round 1.')

  // Read-only: nothing to continue the discussion with.
  await expect(page.getByRole('textbox')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '開始討論' })).toHaveCount(0)

  // Back to a live discussion straight from the record: the ask form works again.
  await page.getByRole('link', { name: '討論', exact: true }).click()
  await expect(page.getByRole('checkbox', { name: 'Fake A' })).toBeVisible()
  await expect(page.getByTestId('record-view')).toHaveCount(0)
})

test('a discussion still in progress is listed as 進行中', async ({ page }) => {
  const summaries: DiscussionSummary[] = [
    { id: '29990101-000000-aaaaaa', question: 'Still going', mode: 'consensus', created_at: '2999-01-01T00:00:00.000+00:00', outcome: null },
  ]
  await page.route('**/api/discussions', (route) => route.fulfill({ json: summaries }))
  await page.goto('/history')
  const row = page.getByTestId('history-item').filter({ hasText: 'Still going' })
  await expect(row).toContainText('共識討論')
  await expect(row.getByTestId('history-outcome')).toHaveText('進行中')
})

const snapshot = (id: string, name: string) => ({
  id,
  display_name: name,
  adapter: 'fake',
  model: null,
  avatar: 'default.png',
  capabilities: { web_access: true, streaming: true },
})

const turn = (participant_id: string, text: string, extra: Partial<DiscussionRecord['rounds'][0]['turns'][0]> = {}) => ({
  participant_id,
  status: 'ok' as const,
  text,
  stance: null,
  started_at: '2026-10-20T10:00:00.000+00:00',
  ended_at: '2026-10-20T10:00:05.000+00:00',
  error: null,
  ...extra,
})

const fullRecord: DiscussionRecord = {
  schema_version: 1,
  id: '20261020-100000-abcdef',
  question: 'Which editor?',
  created_at: '2026-10-20T10:00:00.000+00:00',
  finished_at: '2026-10-20T10:05:00.000+00:00',
  settings: {
    mode: 'consensus',
    participant_ids: ['a', 'b', 'c'],
    judge: 'jev',
    moderator_id: 'a',
    speaking_order: 'parallel',
    max_rounds: 5,
    turn_timeout_seconds: 300,
    jev_threshold: 0.8,
  },
  participants: [snapshot('a', 'Alpha'), snapshot('b', 'Beta'), snapshot('c', 'Gamma')],
  derived_from: '20261020-090000-123456',
  rounds: [
    {
      number: 1,
      turns: [turn('a', 'Vim is best.'), turn('b', 'Emacs is best.'), turn('c', '', { status: 'timeout', text: null, error: 'timed out after 300 s' })],
      draft: 'Draft one: both are fine.',
      judge: null,
      confirmations: null,
    },
    {
      number: 2,
      turns: [
        turn('b', 'Fine, both.', { stance: 'AGREE' }),
        turn('c', '', { status: 'failed', text: null, error: 'crashed' }),
      ],
      draft: 'Draft two: pick what you like.',
      judge: { judge: 'jev', outcome: 'not_reached', detail: { probability: 0.91, threshold: 0.8 } },
      judge_history: [
        { judge: 'jev', outcome: 'confirm', detail: { probability: 0.91, threshold: 0.8 } },
        { judge: 'jev', outcome: 'not_reached', detail: { probability: 0.91, threshold: 0.8 } },
      ],
      confirmations: [{ participant_id: 'b', agree: true, reason: 'Sounds right' }],
    },
    {
      number: 3,
      turns: [turn('b', 'Agreed.', { stance: 'AGREE' })],
      draft: null,
      judge: { judge: 'stance_vote', outcome: 'reached', detail: { stances: { b: 'AGREE', a: null } } },
      confirmations: null,
    },
  ],
  interjections: [{ text: 'Please consider VS Code too', at: '2026-10-20T10:01:00.000+00:00', applies_to_round: 2 }],
  removed_participants: [{ participant_id: 'c', round: 2, reason: '連續 2 輪發言失敗' }],
  moderator_changes: [{ round: 3, participant_id: 'b' }],
  outcome: 'consensus',
  result: { kind: 'consensus', text: 'Use whichever editor you like.', answers: null },
}

test('the read-only view shows every part of a record', async ({ page }) => {
  await page.route(`**/api/discussions/${fullRecord.id}`, (route) => route.fulfill({ json: fullRecord }))
  await page.goto(`/discussions/${fullRecord.id}`)

  const view = page.getByTestId('record-view')
  await expect(view.getByTestId('record-question')).toHaveText('Which editor?')
  await expect(view.getByTestId('record-outcome')).toHaveText('取得共識')
  await expect(view.getByTestId('record-meta')).toContainText('共識討論')
  await expect(view.getByTestId('record-derived-from')).toHaveAttribute('href', '/discussions/20261020-090000-123456')

  const round = (n: number) => view.locator(`[data-testid="record-round"][data-round="${n}"]`)
  await expect(view.getByTestId('record-round')).toHaveCount(3)
  await expect(round(1).getByTestId('turn-card').filter({ hasText: 'Alpha' })).toContainText('Vim is best.')
  await expect(round(1).getByTestId('turn-card').filter({ hasText: 'Gamma' }).getByTestId('turn-status')).toHaveText('逾時')
  await expect(round(1).getByTestId('turn-card').filter({ hasText: 'Gamma' })).toContainText('timed out after 300 s')
  await expect(round(1).getByTestId('record-draft')).toContainText('Draft one: both are fine.')

  await expect(round(2).getByTestId('record-interjection')).toContainText('Please consider VS Code too')
  await expect(round(2).getByTestId('turn-card').filter({ hasText: 'Gamma' }).getByTestId('turn-status')).toHaveText('失敗')
  await expect(round(2).getByTestId('record-turn').filter({ hasText: 'Beta' }).getByTestId('record-stance')).toHaveText('同意')
  // Judge B: the `confirm` verdict (Jev passed the threshold), then the final one.
  await expect(round(2).getByTestId('record-judge')).toHaveCount(2)
  await expect(round(2).getByTestId('record-judge').first()).toContainText('達到門檻，需要反問確認')
  await expect(round(2).getByTestId('record-judge').first()).toContainText('0.91')
  await expect(round(2).getByTestId('record-judge').last()).toContainText('未取得共識')
  await expect(round(2).getByTestId('record-confirmation')).toContainText('Beta')
  await expect(round(2).getByTestId('record-confirmation')).toContainText('Sounds right')
  await expect(round(2).getByTestId('record-removal')).toContainText('Gamma')
  await expect(round(2).getByTestId('record-removal')).toContainText('連續 2 輪發言失敗')

  await expect(round(3).getByTestId('record-moderator-change')).toContainText('Beta')
  await expect(round(3).getByTestId('record-judge')).toContainText('全員同意，取得共識')
  await expect(round(3).getByTestId('record-judge')).toContainText('未表態（視為不同意）')

  await expect(view.getByTestId('record-result')).toContainText('Use whichever editor you like.')
  await expect(page.getByRole('textbox')).toHaveCount(0)
  await expect(page.getByRole('button')).toHaveCount(0)
})

test('an unknown discussion shows an error', async ({ page }) => {
  await page.goto('/discussions/20990101-000000-abcdef')
  await expect(page.getByTestId('record-error')).toBeVisible()
})
