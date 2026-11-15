import { screen, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { API, fakeApi } from './fakeApi'
import { renderApp } from './render'
import { server } from './setup'
import { asDesktop } from './viewport'

/** The shell's scrollers: `<main>` on mobile, the column around it on desktop. */
const scrollers = () => {
  const main = screen.getByRole('main')
  return [main, main.parentElement as HTMLElement]
}

// #158: the shell outlives the navigation, so the Result screen opened at the list's offset.
it.each([false, true])(
  'opens the Result screen at the top after scrolling Start (desktop: %s)',
  async (desktop) => {
    if (desktop) asDesktop()
    fakeApi.seed({ name: 'Golf' })
    const { user } = renderApp('/')
    await user.click(await screen.findByRole('button', { name: 'Flat tyre' }))
    for (const scroller of scrollers()) scroller.scrollTop = 600

    await user.click(screen.getByRole('button', { name: 'Get help now' }))
    await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })

    for (const scroller of scrollers()) expect(scroller.scrollTop).toBe(0)
  },
)

// Only a new incident resets: History → Result → Back keeps the shared offset, as before.
it('keeps the offset when an incident is opened from History', async () => {
  fakeApi.seed({ name: 'Golf' })
  fakeApi.seedIncident({ problem_type: 'flat_tyre', vehicle_id: 1 })
  const { user } = renderApp('/incidents')
  const row = await within(await screen.findByRole('list', { name: 'Your incidents' })).findByRole(
    'link',
    { name: /Flat tyre/ },
  )
  screen.getByRole('main').scrollTop = 300

  await user.click(row)
  await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })

  expect(screen.getByRole('main').scrollTop).toBe(300)
})

it('shows the offline result at the top of the sheet', async () => {
  server.use(http.post(`${API}/api/v1/incidents`, () => HttpResponse.error()))
  const { user } = renderApp('/')
  await user.click(await screen.findByRole('button', { name: 'Flat tyre' }))
  const sheet = screen.getByRole('dialog', { name: 'Flat tyre' })
  const body = sheet.querySelector('.sheet-body') as HTMLElement
  body.scrollTop = 400

  await user.click(within(sheet).getByRole('button', { name: 'Get help now' }))
  await within(sheet).findByText(
    'Not saved — try again when you have signal',
    {},
    { timeout: 5000 },
  )

  expect(body.scrollTop).toBe(0)
})
