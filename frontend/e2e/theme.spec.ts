import { expect, test } from '@playwright/test'

// Theme (ui-redesign 01/02): follows the system until the user picks one in the sidebar;
// the pick survives a reload.

test('the theme toggle cycles system → light → dark and the choice survives a reload', async ({
  page,
}) => {
  await page.goto('/')
  const html = page.locator('html')
  const toggle = page.getByTestId('theme-toggle')

  await expect(toggle).toContainText('跟隨系統')
  await expect(html).not.toHaveAttribute('data-theme', /.*/)

  await toggle.click()
  await expect(toggle).toContainText('亮色')
  await expect(html).toHaveAttribute('data-theme', 'light')
  await page.reload()
  await expect(html).toHaveAttribute('data-theme', 'light')

  await toggle.click()
  await expect(html).toHaveAttribute('data-theme', 'dark')

  await toggle.click()
  await expect(toggle).toContainText('跟隨系統')
  await expect(html).not.toHaveAttribute('data-theme', /.*/)
  await page.reload()
  await expect(html).not.toHaveAttribute('data-theme', /.*/)
})

test('the system colour scheme decides the theme until one is picked', async ({ page }) => {
  // --bg of each theme in styles/tokens.css.
  const body = page.locator('body')
  await page.emulateMedia({ colorScheme: 'light' })
  await page.goto('/')
  await expect(body).toHaveCSS('background-color', 'rgb(245, 246, 248)')
  await page.emulateMedia({ colorScheme: 'dark' })
  await expect(body).toHaveCSS('background-color', 'rgb(14, 17, 22)')

  // A picked theme wins over the system.
  await page.getByTestId('theme-toggle').click()
  await expect(body).toHaveCSS('background-color', 'rgb(245, 246, 248)')
})
