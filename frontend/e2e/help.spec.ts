import type { ConfigRead } from '../src/api/generated'
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
  await page.goto('/?lang=en')
  await page.getByRole('button', { name: /Car won't start after shopping/ }).click()
  const sheet = page.getByRole('dialog')
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

const scenarios = [
  'tyre_parked_morning',
  'battery_parked_night',
  'fuel_almost_at_station',
  'pothole_damaged_wheel',
  'tyre_motorway_night',
  'ev_wont_power_on',
  'unknown_knocking_warning',
  'smoke_engine_bay',
]

for (const locale of ['en', 'pl']) {
  for (const id of scenarios) {
    test(`${id} replays in ${locale} with geolocation denied`, async ({
      page,
      context,
      request,
    }) => {
      await context.clearPermissions()
      const cdp = await context.newCDPSession(page)
      const { targetInfo } = await cdp.send('Target.getTargetInfo')
      await cdp.send('Browser.setPermission', {
        permission: { name: 'geolocation' },
        setting: 'denied',
        origin: 'http://localhost:18080',
        browserContextId: targetInfo.browserContextId,
      })
      const configResponse = await request.get('/api/v1/config')
      const config = (await configResponse.json()) as ConfigRead
      const scenario = config.demo_scenarios.find((item) => item.id === id)
      expect(scenario?.locales[locale]).toBeDefined()
      const copy = scenario?.locales[locale]
      if (!copy) throw new Error(`Missing recorded scenario ${id} in ${locale}`)
      // Count any attempt, including one that the denied permission would reject.
      await page.addInitScript(() => {
        Object.assign(window, { geolocationCalls: 0 })
        navigator.geolocation.getCurrentPosition = () => {
          const state = window as unknown as { geolocationCalls: number }
          state.geolocationCalls++
          throw new Error('Demo must never ask for geolocation')
        }
      })
      await page.route('**/*', async (route) => {
        if (new URL(route.request().url()).origin === 'http://localhost:18080')
          await route.continue()
        else await route.abort()
      })
      await page.goto(`/?lang=${locale}`)
      expect(
        await page.evaluate(
          async () => (await navigator.permissions.query({ name: 'geolocation' })).state,
        ),
      ).toBe('denied')
      await page.getByRole('button', { name: `${copy.title} ${copy.summary}`, exact: true }).click()
      const turnPromise = page.waitForResponse(
        (response) =>
          /\/incidents\/\d+\/ai-turns$/.test(response.url()) &&
          response.request().method() === 'POST',
      )
      await page
        .getByRole('dialog')
        .getByRole('button', {
          name: locale === 'en' ? 'Get help now' : 'Potrzebuję pomocy',
        })
        .click()
      const turn = await turnPromise
      expect(turn.status()).toBe(201)
      const answer = (await turn.json()) as {
        kind: string
        advice: { cause: string } | null
        question: { question: string } | null
      }
      const text = answer.kind === 'advice' ? answer.advice?.cause : answer.question?.question
      if (!text) throw new Error('The first turn has no recorded answer')
      await expect(page.getByText(text, { exact: true })).toBeVisible()
      expect(
        await page.evaluate(
          () => (window as unknown as { geolocationCalls: number }).geolocationCalls,
        ),
      ).toBe(0)
    })
  }
}
