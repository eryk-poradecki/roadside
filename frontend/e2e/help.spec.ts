import { expect, test } from '@playwright/test'

test('a driver gets recorded help and finds the incident in History', async ({ page, request }) => {
  const config = await request.get('/api/v1/config')
  expect(config.ok()).toBe(true)
  expect(await config.json()).toMatchObject({ demo_mode: true })

  // Keep real same-origin API calls; map tiles and any other external browser traffic
  // cannot leave the test. The Compose network also denies backend egress.
  await page.route('**/*', async (route) => {
    if (new URL(route.request().url()).origin === 'http://localhost:18080') {
      await route.continue()
    } else {
      await route.abort()
    }
  })

  // docs/demo-scenarios.md: battery_parked_night (EN), no photos, Golf.
  const note =
    "Left my lights on while shopping. Now it just clicks and won't start. The supermarket car park is nearly empty."
  await page.goto('/?lang=en')
  await expect(page.getByRole('region', { name: 'Your location' })).toContainText('52.23000')
  await page.getByRole('button', { name: 'Flat battery', exact: true }).click()
  const sheet = page.getByRole('dialog')
  await sheet.getByLabel('Anything we should know?').fill(note)
  await sheet.getByRole('radio', { name: 'Golf', exact: true }).check()
  await sheet.getByRole('radio', { name: 'Parked (parking lot, driveway)' }).check()
  await sheet.getByRole('button', { name: 'Get help now' }).click()

  await expect(page).toHaveURL(/\/incidents\/\d+$/)
  const incidentUrl = page.url()
  await expect(page.getByRole('heading', { level: 1, name: 'Flat battery' })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Do this first' })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Do this first' })).toContainText(
    'Turn off the lights, radio, air con and anything else drawing power.',
  )
  await expect(page.getByRole('heading', { name: 'What to do' })).toBeVisible()
  await expect(
    page.getByText(
      'The lights drained the 12 V starter battery, so it can only make the starter click.',
    ),
  ).toBeVisible()

  await page.getByRole('link', { name: 'Back', exact: true }).click()
  await page.getByRole('link', { name: 'History', exact: true }).click()
  const incident = page
    .getByRole('list', { name: 'Your incidents' })
    .getByRole('link', { name: /Flat battery/ })
  await expect(incident).toContainText('Open')
  await incident.click()
  await expect(page).toHaveURL(incidentUrl)
  // A fresh document must read the stored answer through the API, too.
  await page.reload()
  await expect(page.getByRole('heading', { name: 'What to do' })).toBeVisible()
})
