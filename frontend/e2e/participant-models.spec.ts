import { expect, test, type Page } from '@playwright/test'

// Model picker and extra participants (臨時參與者) on the settings page (ui-redesign 11).
// Fake A / Fake B list the models `fake-small` and `fake-large` (participants.e2e.toml).

const panel = (page: Page) => page.getByTestId('settings-panel')
const card = (page: Page, name: string) =>
  page.getByTestId('turn-card').filter({ has: page.getByText(name, { exact: true }) })

test('a model picked for a participant is used and shown on its card', async ({ page }) => {
  await page.goto('/')
  const p = panel(page)
  const picker = p.getByLabel('Fake A 的模型', { exact: true })
  await expect(picker.locator('option')).toHaveText(['預設（Adapter 預設）', 'fake-small', 'fake-large'])
  // Unavailable participants cannot pick a model.
  await expect(p.getByLabel('Fake Down 的模型', { exact: true })).toBeDisabled()

  await p.getByLabel('問題').fill('Which model?')
  await p.getByRole('checkbox', { name: 'Fake A' }).check()
  await p.getByRole('checkbox', { name: 'Fake B' }).check()
  await picker.selectOption('fake-large')
  await p.getByRole('button', { name: '開始討論' }).click()

  await expect(page.getByTestId('discussion-status')).toHaveText('已結束')
  await expect(card(page, 'Fake A').getByTestId('participant-model')).toHaveText('fake-large')
  await expect(card(page, 'Fake B').getByTestId('participant-model')).toHaveText('預設模型')
})

async function addExtra(page: Page, adapter: string, model: string) {
  const p = panel(page)
  await p.getByRole('button', { name: '＋ 新增參與者' }).click()
  await p.getByLabel('新參與者的 Adapter', { exact: true }).selectOption(adapter)
  await p.getByLabel('新參與者的模型', { exact: true }).selectOption(model)
  await p.getByRole('button', { name: '加入', exact: true }).click()
}

test('an extra participant copied from Fake A takes part under a name of its own', async ({ page }) => {
  await page.goto('/')
  const p = panel(page)
  await p.getByLabel('問題').fill('Two of a kind?')
  await p.getByRole('checkbox', { name: 'Fake A' }).check()
  await addExtra(page, 'fake', 'fake-large')

  // Same display name twice: both get their model added (the spec's naming rule).
  await expect(p.getByTestId('participant-option').filter({ hasText: '臨時' })).toHaveCount(1)
  await expect(p.getByRole('checkbox', { name: 'Fake A（fake-large）', exact: true })).toBeChecked()
  await expect(p.getByRole('checkbox', { name: 'Fake A（預設模型）', exact: true })).toBeChecked()
  await expect(p.getByLabel('Fake A（fake-large） 的模型', { exact: true })).toHaveValue('fake-large')

  await p.getByRole('button', { name: '開始討論' }).click()
  await expect(page.getByTestId('discussion-status')).toHaveText('已結束')
  const extra = card(page, 'Fake A（fake-large）')
  await expect(extra.getByTestId('turn-text')).toHaveText('Fake A（fake-large）: reply for round 1.')
  await expect(extra.getByTestId('participant-model')).toHaveText('fake-large')
  await expect(card(page, 'Fake A（預設模型）').getByTestId('turn-text')).toHaveText(
    'Fake A（預設模型）: reply for round 1.',
  )

  // Back on the settings page the extra participant and its model are still there.
  await page.getByRole('link', { name: '討論', exact: true }).click()
  await expect(p.getByLabel('Fake A（fake-large） 的模型', { exact: true })).toHaveValue('fake-large')
})

test('an extra participant can be removed', async ({ page }) => {
  await page.goto('/')
  const p = panel(page)
  await addExtra(page, 'fake', 'fake-small')
  await addExtra(page, 'fake', 'fake-large')
  await expect(p.getByTestId('participant-option').filter({ hasText: '臨時' })).toHaveCount(2)

  await p.getByRole('button', { name: '移除 Fake A（fake-small）', exact: true }).click()
  const left = p.getByTestId('participant-option').filter({ hasText: '臨時' })
  await expect(left).toHaveCount(1)
  // No duplicate among the chosen any more, so the name loses its model.
  await expect(left.getByRole('checkbox', { name: 'Fake A', exact: true })).toBeChecked()
  await expect(left.getByLabel('Fake A 的模型', { exact: true })).toHaveValue('fake-large')
})

test('an extra participant can moderate a consensus discussion', async ({ page }) => {
  await page.goto('/')
  const p = panel(page)
  await p.getByLabel('問題').fill('Who leads?')
  await p.getByRole('radio', { name: '共識討論' }).check()
  await p.getByRole('checkbox', { name: 'Fake B' }).check()
  await addExtra(page, 'fake', 'fake-large')

  const moderator = p.getByLabel('主持人', { exact: true })
  await expect(moderator.locator('option')).toHaveText(['Fake B', 'Fake A'])
  await moderator.selectOption({ label: 'Fake A' })
  await p.getByRole('button', { name: '開始討論' }).click()

  await expect(page.getByTestId('discussion-status')).toHaveText('已結束')
  const lead = page.getByTestId('inspector-participant').filter({ has: page.getByTestId('inspector-moderator') })
  await expect(lead).toContainText('Fake A')
  await expect(lead.getByTestId('participant-model')).toHaveText('fake-large')

  // Removing the moderator falls back to the first chosen participant.
  await page.getByRole('link', { name: '討論', exact: true }).click()
  await p.getByRole('button', { name: '移除 Fake A', exact: true }).click()
  await expect(moderator).toHaveValue('fake-b')
})
