import { expect, test } from '@playwright/test'

test('main layout loads and switches between the discussion and history pages', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('banner')).toContainText('AIgora')
  await expect(page.getByTestId('discussion-page')).toBeVisible()

  await page.getByRole('link', { name: '歷史' }).click()
  await expect(page).toHaveURL(/\/history$/)
  await expect(page.getByTestId('history-page')).toBeVisible()

  await page.getByRole('link', { name: '討論' }).click()
  await expect(page.getByTestId('discussion-page')).toBeVisible()
})

test('frontend reaches the backend through the dev proxy', async ({ request }) => {
  const response = await request.get('/api/participants')
  expect(response.status()).toBe(200)
})
