import { expect, test } from '@playwright/test'

// Ask (提問) end to end: real backend, Fake Adapter participants from participants.e2e.toml.

test('asking a question streams every participant side by side and finishes', async ({ page }) => {
  await page.goto('/')

  await page.getByLabel('問題').fill('Tabs or spaces?')
  await page.getByRole('checkbox', { name: 'Fake A' }).check()
  await page.getByRole('checkbox', { name: 'Fake B' }).check()
  await page.getByRole('checkbox', { name: 'Fake Slow' }).check()
  await page.getByRole('button', { name: '開始討論' }).click()

  const card = (name: string) => page.getByTestId('turn-card').filter({ hasText: name })

  // The slow participant is visibly still streaming: partial text while marked as replying.
  const slow = card('Fake Slow')
  await expect(slow.getByTestId('turn-status')).toHaveText('回覆中')
  await expect(slow.getByTestId('turn-text')).toContainText('Streaming')
  await expect(slow.getByTestId('turn-text')).not.toContainText('the end.')

  await expect(card('Fake A').getByTestId('turn-text')).toHaveText('Fake A: reply for round 1.')
  await expect(card('Fake B').getByTestId('turn-text')).toHaveText('Fake B: reply for round 1.')
  await expect(slow.getByTestId('turn-text')).toContainText('the end.')
  await expect(slow.getByTestId('turn-status')).toHaveText('完成')
  await expect(page.getByTestId('discussion-status')).toHaveText('已結束')
  // An ask has no stances, so the inspector has no stance tracker (ui-redesign 05).
  await expect(page.getByTestId('inspector-participant')).not.toHaveCount(0)
  await expect(page.getByTestId('stance-tracker')).toHaveCount(0)

  // Side by side: the cards share a row.
  const boxes = await Promise.all(
    ['Fake A', 'Fake B', 'Fake Slow'].map((n) => card(n).boundingBox()),
  )
  const tops = boxes.map((b) => Math.round(b!.y))
  expect(new Set(tops).size).toBe(1)
  const lefts = boxes.map((b) => b!.x)
  expect(lefts[0]).toBeLessThan(lefts[1])
  expect(lefts[1]).toBeLessThan(lefts[2])
})

test('participants without web access are marked', async ({ page }) => {
  await page.goto('/')
  await expect(
    page.getByTestId('participant-option').filter({ hasText: 'Fake Offline' }),
  ).toContainText('無上網')
})
