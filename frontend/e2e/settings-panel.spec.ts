import { expect, test, type Page } from '@playwright/test'

// Settings panel (設定面板): defaults from participants.e2e.toml `[defaults]`, fields per
// mode, availability marks, judge B without a TypeSafe key (e2e.env has none), lock.

const panel = (page: Page) => page.getByTestId('settings-panel')

test('defaults match [defaults] of the participants file', async ({ page }) => {
  await page.goto('/')
  const p = panel(page)
  // participants.e2e.toml: mode ask, speaking_order parallel, turn_timeout_seconds 300.
  await expect(p.getByRole('radio', { name: '提問' })).toBeChecked()
  await expect(p.getByLabel('發言順序')).toHaveValue('parallel')
  await expect(p.getByLabel('逾時（秒）')).toHaveValue('300')

  // Consensus fields: judge stance_vote, max_rounds 15, moderator omitted = first participant.
  await p.getByRole('radio', { name: '共識討論' }).check()
  await expect(p.getByRole('radio', { name: /主持人 \+ 全員表態/ })).toBeChecked()
  await expect(p.getByLabel('輪數上限')).toHaveValue('15')
  await p.getByRole('checkbox', { name: 'Fake B' }).check()
  await p.getByRole('checkbox', { name: 'Fake A' }).check()
  await expect(p.getByLabel('主持人', { exact: true })).toHaveValue('fake-a')
})

test('ask shows only the fields it uses; consensus adds moderator, judge and max rounds', async ({ page }) => {
  await page.goto('/')
  const p = panel(page)
  await expect(p.getByRole('radio', { name: '提問' })).toBeChecked()
  await expect(p.getByLabel('發言順序')).toBeVisible()
  await expect(p.getByLabel('主持人', { exact: true })).toHaveCount(0)
  await expect(p.getByLabel('輪數上限')).toHaveCount(0)
  await expect(p.getByTestId('judge-options')).toHaveCount(0)

  await p.getByRole('radio', { name: '共識討論' }).check()
  await expect(p.getByLabel('主持人', { exact: true })).toBeVisible()
  await expect(p.getByLabel('輪數上限')).toBeVisible()
  await expect(p.getByTestId('judge-options')).toBeVisible()

  await p.getByRole('radio', { name: '提問' }).check()
  await expect(p.getByLabel('主持人', { exact: true })).toHaveCount(0)
})

test('the moderator can only be one of the chosen participants', async ({ page }) => {
  await page.goto('/')
  const p = panel(page)
  await p.getByRole('radio', { name: '共識討論' }).check()
  await p.getByRole('checkbox', { name: 'Fake B' }).check()
  await expect(p.getByLabel('主持人', { exact: true })).toHaveValue('fake-b')
  await expect(p.getByLabel('主持人', { exact: true }).locator('option')).toHaveText(['Fake B'])

  // A hand-picked moderator stays while chosen, even when the default moderator is added.
  await p.getByRole('checkbox', { name: 'Fake Slow' }).check()
  await p.getByLabel('主持人', { exact: true }).selectOption('fake-slow')
  await p.getByRole('checkbox', { name: 'Fake A' }).check()
  await expect(p.getByLabel('主持人', { exact: true })).toHaveValue('fake-slow')
  await p.getByRole('checkbox', { name: 'Fake Slow' }).uncheck()
  await expect(p.getByLabel('主持人', { exact: true })).toHaveValue('fake-a')
})

test('unavailable participants show the reason and cannot be picked; no web access is marked', async ({ page }) => {
  await page.goto('/')
  const p = panel(page)
  const down = p.getByTestId('participant-option').filter({ hasText: 'Fake Down' })
  await expect(down).toContainText('fake: CLI not installed')
  await expect(p.getByRole('checkbox', { name: 'Fake Down' })).toBeDisabled()
  await expect(p.getByTestId('participant-option').filter({ hasText: 'Fake Offline' })).toContainText('無上網')
  await expect(p.getByTestId('participant-option').filter({ hasText: 'Fake A' })).not.toContainText('無上網')
})

test('judge B is greyed out with a reason when .env has no TypeSafe key', async ({ page }) => {
  await page.goto('/')
  const p = panel(page)
  await p.getByRole('radio', { name: '共識討論' }).check()
  const jev = p.getByRole('radio', { name: /Jev 判斷 \+ 反問確認/ })
  await expect(jev).toBeDisabled()
  await expect(p.getByTestId('judge-option').filter({ hasText: 'Jev' })).toContainText('TYPESAFE_API_KEY')
  await expect(p.getByRole('radio', { name: /主持人 \+ 全員表態/ })).toBeEnabled()
  // The not-yet-built sequential order cannot be picked either.
  await expect(p.getByLabel('發言順序').locator('option[value="sequential"]')).toBeDisabled()
})

test('starting needs at least 2 participants', async ({ page }) => {
  await page.goto('/')
  const p = panel(page)
  await p.getByLabel('問題').fill('Alone?')
  const submit = p.getByRole('button', { name: '開始討論' })
  await expect(submit).toBeDisabled()
  await expect(p.getByTestId('participants-hint')).toHaveText('請選擇至少 2 個參與者')

  await p.getByRole('checkbox', { name: 'Fake A' }).check()
  await expect(submit).toBeDisabled()
  await expect(p.getByTestId('participants-hint')).toBeVisible()

  await p.getByRole('checkbox', { name: 'Fake B' }).check()
  await expect(submit).toBeEnabled()
  await expect(p.getByTestId('participants-hint')).toHaveCount(0)
})

test('the chosen settings are sent with start and the panel locks while the discussion runs', async ({ page }) => {
  const sent: string[] = []
  page.on('websocket', (ws) => ws.on('framesent', (frame) => sent.push(String(frame.payload))))
  await page.goto('/')
  const p = panel(page)

  await p.getByLabel('問題').fill('Lock me?')
  await p.getByRole('checkbox', { name: 'Fake Slow' }).check()
  await p.getByRole('checkbox', { name: 'Fake B' }).check()
  await p.getByLabel('逾時（秒）').fill('120')
  await p.getByRole('button', { name: '開始討論' }).click()

  await expect(page.getByTestId('discussion-status')).toHaveText('討論中')
  // ui-redesign 04: the locked settings show in the inspector; the form is hidden (still
  // mounted and disabled, so the inputs survive).
  await expect(page.getByTestId('discussion-inspector').getByTestId('settings-locked')).toBeVisible()
  await expect(p).toBeHidden()
  await expect(p.getByLabel('問題')).toBeDisabled()
  await expect(p.getByRole('radio', { name: '共識討論', includeHidden: true })).toBeDisabled()
  await expect(p.getByRole('checkbox', { name: 'Fake A', includeHidden: true })).toBeDisabled()
  await expect(p.getByLabel('逾時（秒）')).toBeDisabled()
  await expect(p.getByRole('button', { name: '開始討論', includeHidden: true })).toBeDisabled()

  const start = JSON.parse(sent.find((s) => s.includes('"start"'))!)
  expect(start.settings).toEqual({
    mode: 'ask',
    participant_ids: ['fake-b', 'fake-slow'],
    speaking_order: 'parallel',
    turn_timeout_seconds: 120,
  })

  await expect(page.getByTestId('discussion-status')).toHaveText('已結束', {
    timeout: 20_000,
  })
  await expect(p.getByTestId('settings-locked')).toHaveCount(0)
  await expect(p.getByLabel('問題')).toBeEnabled()

  // Back to the settings page: the previous inputs are still there.
  await page.getByRole('link', { name: '討論', exact: true }).click()
  await expect(p).toBeVisible()
  await expect(p.getByLabel('問題')).toHaveValue('Lock me?')
  await expect(p.getByLabel('逾時（秒）')).toHaveValue('120')
})
