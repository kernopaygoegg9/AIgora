import { expect, test } from '@playwright/test'

// Interjections (插話) and stop (停止) end to end with Fake Adapter participants.
// Fake Echo replies with its prompt after 1.5 s, so its round-2 reply shows whether
// the interjection reached the prompt; Fake Sleepy never finishes on its own.

const round = (page: import('@playwright/test').Page, n: number) =>
  page.locator(`[data-testid="round"][data-round="${n}"]`)

test('an interjection applies from the next round, and stop ends the discussion', async ({
  page,
}) => {
  await page.goto('/')
  await page.getByRole('radio', { name: '共識討論' }).check()
  await page.getByLabel('問題').fill('Tabs or spaces?')
  await page.getByRole('checkbox', { name: 'Fake A' }).check()
  await page.getByRole('checkbox', { name: 'Fake Echo' }).check()
  await page.getByRole('button', { name: '開始討論' }).click()

  const echo = (n: number) =>
    round(page, n).getByTestId('turn-card').filter({ hasText: 'Fake Echo' })
  await expect(echo(1).getByTestId('turn-status')).toHaveText('回覆中')

  // Interject while round 1 is still running: it is queued for round 2.
  await page.getByLabel('插話').fill('Please consider readability too.')
  await page.getByRole('button', { name: '送出插話' }).click()
  const queued = page.getByTestId('interjection')
  await expect(queued).toContainText('Please consider readability too.')
  await expect(queued).toContainText('第 2 輪')
  await expect(page.getByLabel('插話')).toHaveValue('')

  // Round 1 is not touched; round 2's prompt carries the interjection.
  await expect(echo(1).getByTestId('turn-status')).toHaveText('完成')
  await expect(echo(1).getByTestId('turn-text')).not.toContainText(
    'Please consider readability too.',
  )
  await expect(echo(2).getByTestId('turn-text')).toContainText('Please consider readability too.')

  // Stop: the running turn is cancelled and the discussion ends as stopped.
  await expect(echo(3).getByTestId('turn-status')).toHaveText('回覆中')
  await page.getByRole('button', { name: '停止' }).click()
  await expect(page.getByTestId('discussion-stopped')).toBeVisible()
  await expect(page.getByTestId('discussion-status')).toHaveText('已結束')
  await expect(echo(3).getByTestId('turn-status')).toHaveText('失敗')
  await expect(echo(3).getByTestId('turn-failure')).toContainText('停止')
  await expect(page.getByRole('button', { name: '停止' })).toHaveCount(0)
  await expect(page.getByLabel('插話')).toHaveCount(0)
})

test('stop cancels a turn that would otherwise never finish', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('問題').fill('Will you ever answer?')
  await page.getByRole('checkbox', { name: 'Fake A' }).check()
  await page.getByRole('checkbox', { name: 'Fake Sleepy' }).check()
  await page.getByRole('button', { name: '開始討論' }).click()

  const card = (name: string) => page.getByTestId('turn-card').filter({ hasText: name })
  await expect(card('Fake A').getByTestId('turn-status')).toHaveText('完成')
  await expect(card('Fake Sleepy').getByTestId('turn-status')).toHaveText('回覆中')
  // A one-round ask has no next round, so there is nothing to interject into.
  await expect(page.getByLabel('插話')).toHaveCount(0)

  await page.getByRole('button', { name: '停止' }).click()
  await expect(page.getByTestId('discussion-stopped')).toBeVisible()
  await expect(card('Fake Sleepy').getByTestId('turn-status')).toHaveText('失敗')
  await expect(card('Fake A').getByTestId('turn-status')).toHaveText('完成')
})
