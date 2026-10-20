import { expect, test } from '@playwright/test'

// Failure handling (失敗處理, ticket 07) with Fake Adapter participants: `fake-flaky`
// fails its turns in rounds 1 and 2, so it is removed after round 2.

const round = (page: import('@playwright/test').Page, n: number) =>
  page.locator(`[data-testid="round"][data-round="${n}"]`)

test('a failing participant is marked failed, then removed, and the moderator hands over', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('radio', { name: '共識討論' }).check()
  await page.getByLabel('問題').fill('Tabs or spaces?')
  await page.getByRole('checkbox', { name: 'Fake A' }).check()
  await page.getByRole('checkbox', { name: 'Fake B' }).check()
  await page.getByRole('checkbox', { name: 'Fake Flaky' }).check()
  await page.getByLabel('主持人', { exact: true }).selectOption('fake-flaky')
  await page.getByRole('button', { name: '送出' }).click()

  // Round 1: the failed turn shows its status and reason; the others answer normally.
  const flaky1 = round(page, 1).locator('[data-testid="turn-card"][data-participant-id="fake-flaky"]')
  await expect(flaky1.getByTestId('turn-status')).toHaveText('失敗')
  await expect(flaky1.getByTestId('turn-failure')).toHaveText('fake: simulated crash')
  const a1 = round(page, 1).locator('[data-testid="turn-card"][data-participant-id="fake-a"]')
  await expect(a1.getByTestId('turn-status')).toHaveText('完成')
  await expect(round(page, 1).getByTestId('participant-removed')).toHaveCount(0)

  // Round 2: second failure in a row -> removed; the moderator role moves on (wrapping to Fake A).
  const removed = round(page, 2).getByTestId('participant-removed')
  await expect(removed).toContainText('Fake Flaky')
  await expect(removed).toContainText('連續 2 輪')
  await expect(round(page, 2).getByTestId('moderator-changed')).toContainText('改由 Fake A 擔任主持人')

  // The remaining two still reach consensus.
  await expect(page.getByTestId('discussion-result')).toContainText('共識結果')
  await expect(page.getByTestId('discussion-status')).toHaveText('已結束')
})

test('with fewer than two participants left the discussion ends and says why', async ({ page }) => {
  await page.goto('/')

  await page.getByRole('radio', { name: '共識討論' }).check()
  await page.getByLabel('問題').fill('Tabs or spaces?')
  await page.getByRole('checkbox', { name: 'Fake A' }).check()
  await page.getByRole('checkbox', { name: 'Fake Flaky' }).check()
  await page.getByRole('button', { name: '送出' }).click()

  await expect(round(page, 2).getByTestId('participant-removed')).toContainText('Fake Flaky')
  const result = page.getByTestId('discussion-result')
  await expect(result).toHaveAttribute('data-outcome', 'insufficient_participants')
  await expect(result).toContainText('在場參與者不足')
  await expect(result).toContainText('少於 2 個')
  await expect(page.getByTestId('discussion-status')).toHaveText('已結束')
})
