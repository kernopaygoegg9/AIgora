import { expect, test, type Page } from '@playwright/test'

// Consensus judge B (Jev 判斷 + 反問確認) on the discussion page. The E2E backend has no
// TypeSafe key (judge B is unavailable there, see settings-panel.spec.ts), so the
// discussion socket is answered by a scripted server here; the backend behaviour itself
// is covered by backend/tests/test_consensus_jev.py with a fake Jev client.

const participants = [
  { id: 'fake-a', display_name: 'Fake A', adapter: 'fake', model: null, avatar: 'default.png', capabilities: { web_access: true, streaming: false } },
  { id: 'fake-b', display_name: 'Fake B', adapter: 'fake', model: null, avatar: 'default.png', capabilities: { web_access: true, streaming: false } },
]
const settings = {
  mode: 'consensus',
  participant_ids: ['fake-a', 'fake-b'],
  judge: 'jev',
  moderator_id: 'fake-a',
  speaking_order: 'parallel',
  max_rounds: 5,
  turn_timeout_seconds: 300,
  jev_threshold: 0.8,
}

type Body = Record<string, unknown> & { type: string }

const turns = (round: number, texts: [string, string]): Body[] => [
  { type: 'turn_started', round, participant_id: 'fake-a', purpose: 'turn' },
  { type: 'turn_started', round, participant_id: 'fake-b', purpose: 'turn' },
  { type: 'turn_completed', round, participant_id: 'fake-a', purpose: 'turn', text: texts[0], stance: round > 1 ? 'AGREE' : null },
  { type: 'turn_completed', round, participant_id: 'fake-b', purpose: 'turn', text: texts[1], stance: round > 1 ? 'AGREE' : null },
]
const draft = (round: number, text: string): Body[] => [
  { type: 'turn_started', round, participant_id: 'fake-a', purpose: 'draft' },
  { type: 'turn_completed', round, participant_id: 'fake-a', purpose: 'draft', text, stance: null },
  { type: 'draft_created', round, text },
]
const confirmations = (round: number): Body[] => [
  { type: 'turn_started', round, participant_id: 'fake-a', purpose: 'confirmation' },
  { type: 'turn_started', round, participant_id: 'fake-b', purpose: 'confirmation' },
  { type: 'turn_completed', round, participant_id: 'fake-a', purpose: 'confirmation', text: 'Yes\nSTANCE: AGREE', stance: 'AGREE' },
  { type: 'turn_completed', round, participant_id: 'fake-b', purpose: 'confirmation', text: 'x', stance: null },
]

const script: Body[] = [
  { type: 'discussion_started', question: 'Tabs or spaces?', derived_from: null, settings, participants },
  { type: 'round_started', round: 1 },
  ...turns(1, ['Spaces.', 'Tabs.']),
  ...draft(1, 'Draft one: spaces.'),
  { type: 'round_completed', round: 1 },
  { type: 'round_started', round: 2 },
  ...turns(2, ['OK\nSTANCE: AGREE', 'OK\nSTANCE: AGREE']),
  { type: 'judge_result', round: 2, judge: 'jev', outcome: 'confirm', detail: { stances: null, probability: 0.91, threshold: 0.8 } },
  ...confirmations(2),
  {
    type: 'confirmation_result',
    round: 2,
    answers: [
      { participant_id: 'fake-a', agree: true, reason: 'Yes' },
      { participant_id: 'fake-b', agree: false, reason: 'We still differ on indentation width.' },
    ],
  },
  { type: 'judge_result', round: 2, judge: 'jev', outcome: 'not_reached', detail: { stances: null, probability: 0.91, threshold: 0.8 } },
  ...draft(2, 'Draft two: spaces, width 4.'),
  { type: 'round_completed', round: 2 },
  { type: 'round_started', round: 3 },
  ...turns(3, ['Fine\nSTANCE: AGREE', 'Fine\nSTANCE: AGREE']),
  { type: 'judge_result', round: 3, judge: 'jev', outcome: 'confirm', detail: { stances: null, probability: 0.97, threshold: 0.8 } },
  {
    type: 'confirmation_result',
    round: 3,
    answers: [
      { participant_id: 'fake-a', agree: true, reason: 'Yes' },
      { participant_id: 'fake-b', agree: true, reason: 'Yes' },
    ],
  },
  { type: 'judge_result', round: 3, judge: 'jev', outcome: 'reached', detail: { stances: null, probability: 0.97, threshold: 0.8 } },
  { type: 'turn_started', round: 3, participant_id: 'fake-a', purpose: 'final_result' },
  { type: 'turn_completed', round: 3, participant_id: 'fake-a', purpose: 'final_result', text: 'Use spaces, 4 wide.', stance: null },
  { type: 'round_completed', round: 3 },
  { type: 'discussion_finished', outcome: 'consensus', result: { kind: 'consensus', text: 'Use spaces, 4 wide.', answers: null }, reason: null },
]

async function scriptedSocket(page: Page) {
  await page.routeWebSocket('**/ws/discussion', (ws) => {
    ws.onMessage((raw) => {
      if (JSON.parse(String(raw)).type !== 'start') return
      script.forEach((body, i) => ws.send(JSON.stringify({ ...body, discussion_id: 'd-jev', seq: i + 1 })))
    })
  })
}

test('judge B shows Jev\'s probability, the confirmation answers with reasons, and the final result', async ({ page }) => {
  await scriptedSocket(page)
  await page.goto('/')
  await page.getByRole('radio', { name: '共識討論' }).check()
  await page.getByLabel('問題').fill('Tabs or spaces?')
  await page.getByRole('checkbox', { name: 'Fake A' }).check()
  await page.getByRole('checkbox', { name: 'Fake B' }).check()
  await page.getByRole('button', { name: '送出' }).click()

  const round = (n: number) => page.locator(`[data-testid="round"][data-round="${n}"]`)

  // Round 2: Jev was above the threshold, but one participant disagreed when asked.
  const judge2 = round(2).getByTestId('judge-result')
  await expect(judge2).toContainText('Jev 判斷')
  await expect(judge2).toContainText('尚未取得共識')
  await expect(judge2.getByTestId('jev-probability')).toContainText('0.91')
  await expect(judge2.getByTestId('jev-probability')).toContainText('門檻 0.8')
  const answers2 = round(2).getByTestId('confirmation-result')
  await expect(answers2).toContainText('有參與者不同意')
  await expect(answers2.getByTestId('confirmation-answer').filter({ hasText: 'Fake A' })).toContainText('同意')
  const disagree = answers2.getByTestId('confirmation-answer').filter({ hasText: 'Fake B' })
  await expect(disagree).toContainText('不同意')
  await expect(disagree).toContainText('We still differ on indentation width.')
  await expect(round(2).getByTestId('consensus-draft')).toContainText('Draft two: spaces, width 4.')

  // Round 3: everyone confirmed; the moderator's final result is the consensus.
  const judge3 = round(3).getByTestId('judge-result')
  await expect(judge3).toContainText('反問全員同意')
  await expect(judge3.getByTestId('jev-probability')).toContainText('0.97')
  await expect(round(3).getByTestId('confirmation-result')).toContainText('全員同意已取得共識')
  const result = page.getByTestId('discussion-result')
  await expect(result).toContainText('Use spaces, 4 wide.')
})
