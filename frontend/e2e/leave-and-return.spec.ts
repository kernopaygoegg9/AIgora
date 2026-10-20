import { expect, test } from '@playwright/test'

// Leaving the discussion page closes its socket, which cancels a running discussion (it is
// saved in the history). Coming back must not show a dead live view: the settings return.

test('leaving a running discussion and coming back shows the settings again', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('問題').fill('Will you ever answer?')
  await page.getByRole('checkbox', { name: 'Fake A' }).check()
  await page.getByRole('checkbox', { name: 'Fake Sleepy' }).check()
  await page.getByRole('button', { name: '開始討論' }).click()
  const sleepy = page.getByTestId('turn-card').filter({ hasText: 'Fake Sleepy' })
  await expect(sleepy.getByTestId('turn-status')).toHaveText('回覆中')

  await page.getByRole('link', { name: '歷史', exact: true }).click()
  await expect(page.getByTestId('history-page')).toBeVisible()
  await page.getByRole('link', { name: '討論', exact: true }).click()

  await expect(page.getByTestId('discussion-question')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '停止' })).toHaveCount(0)
  await expect(page.getByLabel('問題')).toBeVisible()

  // And a new discussion starts and finishes from there.
  await page.getByLabel('問題').fill('Tabs or spaces?')
  await page.getByRole('checkbox', { name: 'Fake A' }).check()
  await page.getByRole('checkbox', { name: 'Fake B' }).check()
  await page.getByRole('button', { name: '開始討論' }).click()
  await expect(page.getByTestId('discussion-question')).toHaveText('Tabs or spaces?')
  await expect(page.getByTestId('discussion-status')).toHaveText('已結束')
})
