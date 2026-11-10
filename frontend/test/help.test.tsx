import { screen, waitFor, within } from '@testing-library/react'
import { onlineManager } from '@tanstack/react-query'
import { delay, http, HttpResponse } from 'msw'
import { en } from '../src/i18n/en'
import { API, fakeApi, problem } from './fakeApi'
import { renderApp } from './render'
import { server } from './setup'

type Fix = { latitude: number; longitude: number; accuracy: number } | 'denied'

/** jsdom has no geolocation; give the app one that answers at once. */
function stubGeolocation(fix: Fix) {
  Object.defineProperty(navigator, 'geolocation', {
    configurable: true,
    value: {
      getCurrentPosition: (ok: PositionCallback, fail: PositionErrorCallback) => {
        if (fix === 'denied') fail({ code: 1, message: 'denied' } as GeolocationPositionError)
        else ok({ coords: fix } as GeolocationPosition)
      },
    },
  })
}

afterEach(() => {
  Reflect.deleteProperty(navigator, 'geolocation')
})

const checklist = () => screen.getByRole('region', { name: 'Do this first' })

describe('help request: Start → Get help now → Result', () => {
  it('creates the incident and shows the checklist for the tapped problem type', async () => {
    const golf = fakeApi.seed({ name: 'Golf', fuel_type: 'petrol' })
    const { user } = renderApp('/')

    await user.click(await screen.findByRole('button', { name: 'Flat tyre' }))
    const sheet = await screen.findByRole('dialog', { name: 'Flat tyre' })
    await user.type(within(sheet).getByLabelText('Anything we should know?'), 'Rear left, hissing')
    await user.click(within(sheet).getByRole('button', { name: 'Get help now' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })).toBeInTheDocument()
    const list = en.checklist.lists.tyre
    expect(within(checklist()).getByText(list.first)).toBeInTheDocument()
    for (const item of list.items) expect(within(checklist()).getByText(item)).toBeInTheDocument()
    expect(within(checklist()).getByText('Safety basics · not AI')).toBeInTheDocument()
    expect(screen.getByText('Saved to your incidents')).toBeInTheDocument()

    expect(fakeApi.incidentRequests).toHaveLength(1)
    const [request] = fakeApi.incidentRequests
    expect(request?.key).toMatch(/^[0-9a-f-]{36}$/)
    expect(request?.body).toEqual({
      problem_type: 'flat_tyre',
      vehicle_id: golf.id,
      note: 'Rear left, hissing',
      location: null,
    })
  })

  it('sends the detected location', async () => {
    stubGeolocation({ latitude: 52.2297, longitude: 21.0122, accuracy: 18 })
    const { user } = renderApp('/')
    expect(await screen.findByText('Accurate to ~18 m')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Pothole damage' }))
    await user.click(await screen.findByRole('button', { name: 'Get help now' }))

    expect(await screen.findByText('52.22970, 21.01220')).toBeInTheDocument()
    expect(fakeApi.incidentRequests[0]?.body.location).toEqual({
      lat: 52.2297,
      lon: 21.0122,
      accuracy_m: 18,
    })
  })

  it('works with no vehicle and geolocation denied, and invites adding a vehicle', async () => {
    stubGeolocation('denied')
    const { user } = renderApp('/')
    expect(await screen.findByText('Location is off')).toBeInTheDocument()
    expect(screen.getByText('You can still get help without it.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Something else' }))
    const sheet = await screen.findByRole('dialog', { name: 'Something else' })
    expect(within(sheet).queryByRole('group', { name: 'Which vehicle?' })).not.toBeInTheDocument()
    await user.click(within(sheet).getByRole('button', { name: 'Get help now' }))

    expect(await screen.findByText(en.checklist.lists.other.first)).toBeInTheDocument()
    expect(screen.getByText('No location')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Add a vehicle' })).toHaveAttribute(
      'href',
      '/vehicles/new',
    )
    expect(fakeApi.incidentRequests[0]?.body).toMatchObject({ vehicle_id: null, location: null })
  })

  it('labels the fuel tile "Out of charge" and shows the charge checklist for an electric default', async () => {
    fakeApi.seed({ name: 'Leaf', fuel_type: 'electric' })
    const { user } = renderApp('/')

    await user.click(await screen.findByRole('button', { name: 'Out of charge' }))
    await user.click(await screen.findByRole('button', { name: 'Get help now' }))

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Out of charge' }),
    ).toBeInTheDocument()
    expect(
      within(checklist()).getByText(
        "Ask for a flatbed truck. Many electric cars can't be towed on their wheels.",
      ),
    ).toBeInTheDocument()
    expect(fakeApi.incidentRequests[0]?.body.problem_type).toBe('out_of_fuel')
  })

  it('lets the vehicle picked in the sheet decide the label and the checklist', async () => {
    fakeApi.seed({ name: 'Golf', fuel_type: 'diesel' })
    const leaf = fakeApi.seed({ name: 'Leaf', fuel_type: 'electric', is_default: false })
    const { user } = renderApp('/')

    // The tile follows the default vehicle (diesel)...
    await user.click(await screen.findByRole('button', { name: 'Out of fuel' }))
    const sheet = await screen.findByRole('dialog', { name: 'Out of fuel' })
    const picker = within(sheet).getByRole('group', { name: 'Which vehicle?' })
    expect(within(picker).getByRole('radio', { name: 'Golf' })).toBeChecked()

    // ...and from the sheet on, the incident's vehicle does.
    await user.click(within(picker).getByRole('radio', { name: 'Leaf' }))
    expect(screen.getByRole('dialog', { name: 'Out of charge' })).toBeInTheDocument()
    await user.click(within(sheet).getByRole('button', { name: 'Get help now' }))

    expect(await screen.findByText(en.checklist.lists.charge.first)).toBeInTheDocument()
    expect(fakeApi.incidentRequests[0]?.body.vehicle_id).toBe(leaf.id)
  })

  it('can send the request with no vehicle even when the driver has one', async () => {
    fakeApi.seed({ name: 'Golf' })
    const { user } = renderApp('/')

    await user.click(await screen.findByRole('button', { name: 'Flat battery' }))
    await user.click(await screen.findByRole('radio', { name: 'No vehicle' }))
    await user.click(screen.getByRole('button', { name: 'Get help now' }))

    expect(await screen.findByText(en.checklist.lists.battery.first)).toBeInTheDocument()
    expect(fakeApi.incidentRequests[0]?.body.vehicle_id).toBeNull()
    // The driver has vehicles and chose none on purpose: no invite.
    expect(screen.queryByRole('link', { name: 'Add a vehicle' })).not.toBeInTheDocument()
  })

  it('does not create a second incident on a double tap', async () => {
    const { user } = renderApp('/')
    await user.click(await screen.findByRole('button', { name: 'Flat tyre' }))
    const button = await screen.findByRole('button', { name: 'Get help now' })
    await user.dblClick(button)

    expect(await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })).toBeInTheDocument()
    expect(fakeApi.incidents).toHaveLength(1)
    expect(new Set(fakeApi.incidentRequests.map((r) => r.key)).size).toBe(1)
  })

  it('retries a lost response with the same key and lands on the one incident', async () => {
    fakeApi.loseNextCreateResponse = true
    const { user } = renderApp('/')
    await user.click(await screen.findByRole('button', { name: 'Flat tyre' }))
    await user.click(await screen.findByRole('button', { name: 'Get help now' }))

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Flat tyre' }, { timeout: 4000 }),
    ).toBeInTheDocument()
    expect(fakeApi.incidentRequests).toHaveLength(2)
    const [first, second] = fakeApi.incidentRequests
    expect(second?.key).toBe(first?.key)
    expect(fakeApi.incidents).toHaveLength(1)
  })

  it('reuses the key when the driver taps again after a failed request', async () => {
    let failedKey: string | null = null
    server.use(
      http.post(
        `${API}/api/v1/incidents`,
        ({ request }) => {
          failedKey = request.headers.get('Idempotency-Key')
          return problem(422, 'validation_error', 'x')
        },
        { once: true },
      ),
    )
    const { user } = renderApp('/')
    await user.click(await screen.findByRole('button', { name: 'Flat tyre' }))
    await user.click(await screen.findByRole('button', { name: 'Get help now' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/Some details aren't valid/)

    await user.click(screen.getByRole('button', { name: 'Get help now' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })).toBeInTheDocument()
    expect(fakeApi.incidentRequests).toHaveLength(1)
    expect(fakeApi.incidentRequests[0]?.key).toBe(failedKey)
  })

  it('keeps the key when the driver closes and reopens the same tile after a lost response', async () => {
    let lostKey: string | null = null
    server.use(
      http.post(
        `${API}/api/v1/incidents`,
        ({ request }) => {
          lostKey = request.headers.get('Idempotency-Key')
          return problem(422, 'validation_error', 'x')
        },
        { once: true },
      ),
    )
    const { user } = renderApp('/')
    await user.click(await screen.findByRole('button', { name: 'Flat tyre' }))
    await user.click(await screen.findByRole('button', { name: 'Get help now' }))
    await screen.findByRole('alert')
    await user.click(screen.getByRole('button', { name: 'Close' }))

    await user.click(screen.getByRole('button', { name: 'Flat tyre' }))
    await user.click(await screen.findByRole('button', { name: 'Get help now' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })).toBeInTheDocument()
    expect(fakeApi.incidentRequests[0]?.key).toBe(lostKey)
  })

  it('fails with the offline message instead of waiting when the browser is offline', async () => {
    onlineManager.setOnline(false)
    server.use(http.post(`${API}/api/v1/incidents`, () => HttpResponse.error()))
    try {
      const { user } = renderApp('/')
      await user.click(await screen.findByRole('button', { name: 'Flat tyre' }))
      await user.click(await screen.findByRole('button', { name: 'Get help now' }))
      expect(await screen.findByRole('alert', {}, { timeout: 5000 })).toHaveTextContent(
        /You're offline/,
      )
      expect(screen.getByRole('button', { name: 'Get help now' })).toBeEnabled()
    } finally {
      onlineManager.setOnline(true)
    }
  })

  it('stays on Start when the driver closes the sheet before the request finishes', async () => {
    server.use(
      http.post(`${API}/api/v1/incidents`, async () => {
        await delay(150)
        return HttpResponse.json(fakeApi.seedIncident({ problem_type: 'flat_tyre' }), {
          status: 201,
        })
      }),
    )
    const { user } = renderApp('/')
    await user.click(await screen.findByRole('button', { name: 'Flat tyre' }))
    await user.click(await screen.findByRole('button', { name: 'Get help now' }))
    await user.click(screen.getByRole('button', { name: 'Close' }))

    await waitFor(() => {
      expect(fakeApi.incidents).toHaveLength(1)
    })
    await new Promise((r) => setTimeout(r, 50))
    expect(screen.getByRole('heading', { level: 1, name: 'What happened?' })).toBeInTheDocument()
  })

  it('uses a fresh key for the next help request', async () => {
    const { user } = renderApp('/')
    await user.click(await screen.findByRole('button', { name: 'Flat tyre' }))
    await user.click(await screen.findByRole('button', { name: 'Get help now' }))
    await user.click(await screen.findByRole('link', { name: 'Back' }))

    await user.click(await screen.findByRole('button', { name: 'Flat battery' }))
    await user.click(await screen.findByRole('button', { name: 'Get help now' }))

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Flat battery' }),
    ).toBeInTheDocument()
    const [a, b] = fakeApi.incidentRequests
    expect(a?.key).not.toBe(b?.key)
    expect(fakeApi.incidents).toHaveLength(2)
  })

  it('closes the sheet without sending anything', async () => {
    const { user } = renderApp('/')
    await user.click(await screen.findByRole('button', { name: 'Flat tyre' }))
    await user.click(await screen.findByRole('button', { name: 'Close' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(fakeApi.incidentRequests).toEqual([])
  })
})

describe('Result screen', () => {
  it('shows the same incident after a reload of its URL', async () => {
    fakeApi.seed({ name: 'Golf' })
    const incident = fakeApi.seedIncident({ problem_type: 'pothole_damage', vehicle_id: 1 })
    renderApp(`/incidents/${String(incident.id)}`)

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Pothole damage' }),
    ).toBeInTheDocument()
    expect(screen.getByText(en.checklist.lists.pothole.first)).toBeInTheDocument()
    expect(screen.getByText('Golf')).toBeInTheDocument()
  })

  it('uses the charge checklist when the incident vehicle is electric', async () => {
    fakeApi.seed({ name: 'Golf', fuel_type: 'petrol' })
    const leaf = fakeApi.seed({ name: 'Leaf', fuel_type: 'electric', is_default: false })
    const incident = fakeApi.seedIncident({ problem_type: 'out_of_fuel', vehicle_id: leaf.id })
    renderApp(`/incidents/${String(incident.id)}`)

    expect(await screen.findByText(en.checklist.lists.charge.first)).toBeInTheDocument()
  })

  it('offers "Call <insurer>" with the policy number next to a compact 112', async () => {
    const golf = fakeApi.seed({
      name: 'Golf',
      assistance_insurer: 'PZU Pomoc',
      assistance_phone: '+48 22 111 22 33',
      policy_number: 'POL-9',
    })
    const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre', vehicle_id: golf.id })
    renderApp(`/incidents/${String(incident.id)}`)

    const call = await screen.findByRole('link', { name: /Call PZU Pomoc/ })
    expect(call).toHaveAttribute('href', 'tel:+48221112233')
    expect(call).toHaveTextContent('Policy POL-9')
    expect(screen.getByRole('link', { name: 'Call emergency number 112' })).toHaveTextContent('112')
  })

  it('renders no assistance button without a phone number, even with an insurer name', async () => {
    const golf = fakeApi.seed({ name: 'Golf', assistance_insurer: 'PZU Pomoc' })
    const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre', vehicle_id: golf.id })
    renderApp(`/incidents/${String(incident.id)}`)

    expect(await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Call PZU/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Call emergency number 112' })).toHaveTextContent(
      'Emergency? Call 112',
    )
  })

  it('shows a not-found message for an unknown incident', async () => {
    renderApp('/incidents/99')
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/couldn't find that/)
    })
  })
})
