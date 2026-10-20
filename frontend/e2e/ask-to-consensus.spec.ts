import { expect, test } from '@playwright/test'

// 提問轉共識討論 (ticket 10): ask, press 開始共識討論, the consensus discussion finishes.

test('an ask can be continued as a consensus discussion that reuses its answers as round 1', async ({ page }) => {
  await page.goto('/')

  await page.getByLabel('問題').fill('Which editor?')
  await page.getByRole('checkbox', { name: 'Fake A' }).check()
  await page.getByRole('checkbox', { name: 'Fake B' }).check()
  await page.getByRole('button', { name: '送出' }).click()
  await expect(page.getByTestId('discussion-status')).toHaveText('已結束')

  const button = page.getByRole('button', { name: '開始共識討論' })
  await button.click()

  await expect(page.getByTestId('discussion-question')).toHaveText('Which editor?')
  await expect(page.getByTestId('consensus-draft').first()).toContainText('Fake A: consensus draft after round 1.')
  const result = page.getByTestId('discussion-result')
  await expect(result).toHaveAttribute('data-outcome', 'consensus')
  await expect(result).toContainText('Fake A: consensus draft after round 1.')
  // Round 1 is the ask's answers; round 2 is the first real consensus round.
  await expect(page.getByTestId('turn-card').filter({ hasText: 'Fake B: reply for round 1.' })).toHaveCount(1)
  await expect(page.getByTestId('turn-card').filter({ hasText: 'Fake B: reply for round 2.' })).toHaveCount(1)
  await expect(button).toHaveCount(0)
})
