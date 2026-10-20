import { expect, test, type Locator } from '@playwright/test'

// Ticket 17: the real brand assets and avatars show up (not the grey placeholder).

async function expectLoadedImage(img: Locator) {
  await expect(img).toBeVisible()
  await expect.poll(() => img.evaluate((el) => (el as unknown as { naturalWidth: number }).naturalWidth)).toBeGreaterThan(0)
}

test('header shows the app icon and the page links both favicons', async ({ page, request }) => {
  await page.goto('/')
  await expectLoadedImage(page.getByTestId('app-logo'))

  const icons = page.locator('link[rel="icon"]')
  await expect(icons).toHaveCount(2)
  for (const href of await icons.evaluateAll((els) => els.map((el) => el.getAttribute('href') ?? ''))) {
    const response = await request.get(href)
    expect(response.status()).toBe(200)
    expect(response.headers()['content-type']).toContain('image/png')
  }
})

test('participants in the settings panel show their avatar', async ({ page }) => {
  await page.goto('/')
  const option = page.getByTestId('participant-option').filter({ hasText: 'Fake A' })
  await expectLoadedImage(option.locator('img.avatar'))
  await expect(page.locator('.avatar-missing')).toHaveCount(0)
})
