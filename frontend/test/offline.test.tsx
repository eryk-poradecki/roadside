import { act, screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { i18n } from '../src/i18n'
import { en } from '../src/i18n/en'
import { pl } from '../src/i18n/pl'
import { API, fakeApi } from './fakeApi'
import { renderApp } from './render'
import { server } from './setup'

/** An opened Result screen, then the network goes away under it. */
async function openResult() {
  fakeApi.seed({ name: 'Golf' })
  const incident = fakeApi.seedIncident({ problem_type: 'pothole_damage', vehicle_id: 1 })
  const app = renderApp(`/incidents/${String(incident.id)}`)
  await screen.findByRole('heading', { level: 1, name: 'Pothole damage' })
  return { ...app, incident }
}

const loseNetwork = (id: number) => {
  server.use(http.patch(`${API}/api/v1/incidents/${String(id)}`, () => HttpResponse.error()))
}

const banner = () => screen.queryByRole('status', { name: en.offline.label })

function setBrowserOnline(online: boolean) {
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(online)
  act(() => {
    window.dispatchEvent(new Event(online ? 'online' : 'offline'))
  })
}

describe('offline banner', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    window.dispatchEvent(new Event('online'))
  })

  it('is absent while requests get answers', async () => {
    await openResult()
    expect(banner()).not.toBeInTheDocument()
  })

  it('appears when a request gets no response, and the checklist and 112 stay', async () => {
    const { user, incident } = await openResult()
    loseNetwork(incident.id)

    await user.click(screen.getByRole('button', { name: 'Mark resolved' }))

    expect(await screen.findByRole('status', { name: en.offline.label })).toHaveTextContent(
      en.offline.body,
    )
    expect(screen.getByText(en.checklist.lists.pothole.first)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Call emergency number 112' })).toHaveAttribute(
      'href',
      'tel:112',
    )
  })

  it('goes away once a request gets a response again', async () => {
    const { user, incident } = await openResult()
    loseNetwork(incident.id)
    await user.click(screen.getByRole('button', { name: 'Mark resolved' }))
    await screen.findByRole('status', { name: en.offline.label })

    server.resetHandlers()
    await user.click(screen.getByRole('button', { name: 'Mark resolved' }))

    expect(await screen.findByText(en.incident.resolved)).toBeInTheDocument()
    expect(banner()).not.toBeInTheDocument()
  })

  it('treats an HTTP error as reachable, not offline', async () => {
    const { user, incident } = await openResult()
    server.use(
      http.patch(`${API}/api/v1/incidents/${String(incident.id)}`, () =>
        HttpResponse.json({ reason: 'internal_error' }, { status: 500 }),
      ),
    )
    await user.click(screen.getByRole('button', { name: 'Mark resolved' }))

    expect(await screen.findByText(en.errors.generic)).toBeInTheDocument()
    expect(banner()).not.toBeInTheDocument()
  })

  it('follows the browser going offline with no request in flight', async () => {
    await openResult()

    setBrowserOnline(false)
    expect(banner()).toBeInTheDocument()
    expect(screen.getByText(en.checklist.lists.pothole.first)).toBeInTheDocument()

    setBrowserOnline(true)
    expect(banner()).not.toBeInTheDocument()
  })

  it('fails a write at once while the browser says offline, instead of queueing it', async () => {
    const { user, incident } = await openResult()
    setBrowserOnline(false)
    loseNetwork(incident.id)

    await user.click(screen.getByRole('button', { name: 'Mark resolved' }))

    expect(await screen.findByText(/You're offline/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mark resolved' })).toBeEnabled()
  })

  it('speaks Polish', async () => {
    await openResult()
    await act(() => i18n.changeLanguage('pl'))

    setBrowserOnline(false)

    expect(screen.getByRole('status', { name: pl.offline.label })).toHaveTextContent(
      pl.offline.body,
    )
  })
})
