import { expect, test } from '@playwright/test'

// Consensus discussion (共識討論, judge A) end to end with Fake Adapter participants:
// default fakes take no stance in round 1 and agree from round 2, so the discussion
// reaches consensus on the moderator's round-1 draft.

test('a consensus discussion shows the draft, everyone\'s stance and the consensus result', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('radio', { name: '共識討論' }).check()
  await page.getByLabel('問題').fill('Tabs or spaces?')
  await page.getByRole('checkbox', { name: 'Fake A' }).check()
  await page.getByRole('checkbox', { name: 'Fake B' }).check()
  await page.getByRole('button', { name: '送出' }).click()

  const round = (n: number) => page.locator(`[data-testid="round"][data-round="${n}"]`)

  // Round 1: free answers, then the moderator (first participant) writes the draft.
  const draft = round(1).getByTestId('consensus-draft')
  await expect(draft).toContainText('Fake A: consensus draft after round 1.')
  await expect(draft).toContainText('Fake A')
  await expect(round(1).getByTestId('judge-result')).toHaveCount(0)

  // Round 2: everyone, the moderator included, takes a stance on that draft.
  const judge = round(2).getByTestId('judge-result')
  await expect(judge).toContainText('取得共識')
  await expect(judge.getByTestId('stance').filter({ hasText: 'Fake A' })).toContainText('同意')
  await expect(judge.getByTestId('stance').filter({ hasText: 'Fake B' })).toContainText('同意')

  // The consensus result is shown on its own.
  const result = page.getByTestId('discussion-result')
  await expect(result).toContainText('共識結果')
  await expect(result).toContainText('Fake A: consensus draft after round 1.')
  await expect(page.getByTestId('discussion-status')).toHaveText('已結束')
})
