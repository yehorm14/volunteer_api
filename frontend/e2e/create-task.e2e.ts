import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.route('**/api/tasks**', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: [] })
      return
    }
    const task = route.request().postDataJSON()
    await route.fulfill({
      status: 201,
      json: { ...task, id: 1, owner_id: 1, description: task.description ?? null },
    })
  })
  await page.addInitScript(() => {
    const payload = btoa(JSON.stringify({ sub: 'vol@example.com' }))
    localStorage.setItem('access_token', 'x.' + payload + '.x')
  })
  await page.goto('/dashboard')
  await expect(page.getByText('No tasks yet')).toBeVisible()
})

test('the create-task dialog has a name and contains keyboard focus', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 700 })
  const triggers = page.getByRole('button', { name: '+ New task' })
  const trigger = triggers.last()
  await trigger.focus()
  await page.keyboard.press('Enter')

  const dialog = page.getByRole('dialog', { name: 'New task' })
  const close = dialog.getByRole('button', { name: 'Close' })
  const cancel = dialog.getByRole('button', { name: 'Cancel' })
  const title = dialog.getByRole('textbox', { name: 'Title' })
  await expect(title).toBeFocused()
  const accessibility = await new AxeBuilder({ page }).include('dialog').analyze()
  expect(accessibility.violations).toEqual([])

  // The dashboard trigger stays in the document but the native dialog blocks focus.
  await page.getByRole('button', { name: '+ New task', includeHidden: true }).first()
    .evaluate((button) => button.focus())
  await expect(title).toBeFocused()

  for (const control of [
    dialog.getByRole('textbox', { name: 'Description' }),
    dialog.getByRole('button', { name: 'Create task' }),
    cancel,
    close,
  ]) {
    await page.keyboard.press('Tab')
    await expect(control).toBeFocused()
  }
  await page.keyboard.press('Shift+Tab')
  await expect(cancel).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(trigger).toBeFocused()

  for (const dismiss of [
    () => dialog.getByRole('button', { name: 'Cancel' }).click(),
    () => dialog.getByRole('button', { name: 'Close' }).click(),
    () => page.mouse.click(5, 5),
  ]) {
    await trigger.click()
    await expect(title).toBeFocused()
    await dismiss()
    await expect(dialog).toHaveCount(0)
    await expect(trigger).toBeFocused()
  }
})

test('creating the first task moves focus to the remaining New task button', async ({ page }) => {
  const triggers = page.getByRole('button', { name: '+ New task' })
  await triggers.last().click()
  const dialog = page.getByRole('dialog', { name: 'New task' })
  await dialog.getByRole('textbox', { name: 'Title' }).fill('Pack food boxes')
  await dialog.getByRole('button', { name: 'Create task' }).click()

  await expect(dialog).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Pack food boxes' })).toBeVisible()
  await expect(triggers).toHaveCount(1)
  await expect(triggers).toBeFocused()
})
