import { screen, waitFor, within } from '@testing-library/react'
import { delay, http, HttpResponse } from 'msw'
import type { IncidentCreate } from '../src/api/incidents'
import { en } from '../src/i18n/en'
import { ADVICE, API, fakeApi, place, PLACES } from './fakeApi'
import { renderApp } from './render'
import { server } from './setup'

const LOCATION = { lat: 52.2297, lon: 21.0122, accuracy_m: 12 }

const panel = () => screen.getByRole('region', { name: 'Nearby' })
const chip = (scope: HTMLElement, name: RegExp) =>
  within(within(scope).getByRole('group', { name: en.nearby.chipsLabel })).getByRole('button', {
    name,
  })
const findPanel = () => screen.findByRole('region', { name: 'Nearby' })
const placeNames = (scope: HTMLElement) =>
  within(within(scope).getByRole('list', { name: en.nearby.listLabel }))
    .getAllByRole('listitem')
    .map((li) => li.querySelector('strong')?.textContent)

function openIncident(body: Partial<IncidentCreate> = {}, extra = {}) {
  const incident = fakeApi.seedIncident(
    { problem_type: 'flat_tyre', location: LOCATION, ...body },
    extra,
  )
  return { incident, ...renderApp(`/incidents/${String(incident.id)}`) }
}

type Fix = { latitude: number; longitude: number; accuracy: number }

function stubGeolocation(fix: Fix) {
  Object.defineProperty(navigator, 'geolocation', {
    configurable: true,
    value: {
      getCurrentPosition: (ok: PositionCallback) => {
        ok({ coords: fix } as GeolocationPosition)
      },
    },
  })
}

afterEach(() => {
  Reflect.deleteProperty(navigator, 'geolocation')
})

describe('Nearby places on the Result screen', () => {
  it('looks up once and shows map data nearest first, with the fitting category chosen', async () => {
    openIncident()

    expect(await within(await findPanel()).findByText('Wulkanizacja Nowa')).toBeInTheDocument()
    const nearby = panel()
    expect(within(nearby).getByText(en.nearby.badge)).toBeInTheDocument()
    expect(within(nearby).getByText(en.nearby.attribution)).toBeInTheDocument()
    expect(chip(nearby, /^Tyres/)).toHaveAttribute('aria-pressed', 'true')
    expect(chip(nearby, /^All/)).toHaveAttribute('aria-pressed', 'false')
    // Only tyre shops, still nearest first.
    expect(placeNames(nearby)).toEqual(['Wulkanizacja Nowa', 'Opony Max'])
    expect(within(nearby).getByRole('img', { name: en.nearby.mapLabel })).toHaveAttribute(
      'data-pins',
      'node/2 node/4',
    )
    // Opening hours only in the simple forms.
    expect(within(nearby).getByText('· Open 24 hours')).toBeInTheDocument()
    expect(within(nearby).queryByText(/08:00/)).not.toBeInTheDocument()
    expect(within(nearby).getByText('600 m')).toBeInTheDocument()
    expect(within(nearby).getByText('1.2 km')).toBeInTheDocument()

    expect(fakeApi.nearbyRequests).toEqual([{ incidentId: 1, body: { radius_km: 5 } }])
  })

  it('chips switch categories without a new request', async () => {
    const { user } = openIncident()
    await within(await findPanel()).findByText('Wulkanizacja Nowa')

    await user.click(chip(panel(), /^All/))
    expect(placeNames(panel())).toEqual([
      'Auto Serwis Hoża',
      'Wulkanizacja Nowa',
      // No name: the category stands in.
      'Fuel station',
    ])

    await user.click(chip(panel(), /^Fuel/))
    expect(placeNames(panel())).toEqual(['Fuel station', 'Orlen'])

    await user.click(chip(panel(), /^Repair/))
    expect(placeNames(panel())).toEqual(['Auto Serwis Hoża', 'Fuel station', 'Orlen'])

    expect(fakeApi.nearbyRequests).toHaveLength(1)
  })

  it('preselects charging for an electric vehicle out of charge', async () => {
    const car = fakeApi.seed({ name: 'Leaf', fuel_type: 'electric' })
    openIncident({ problem_type: 'out_of_fuel', vehicle_id: car.id })

    expect(await within(await findPanel()).findByText('GreenWay')).toBeInTheDocument()
    expect(chip(panel(), /^Charging/)).toHaveAttribute('aria-pressed', 'true')
    expect(placeNames(panel())).toEqual(['GreenWay'])
  })

  it("the advice's extra categories only add chips", async () => {
    openIncident(
      {},
      { ai_turns: [fakeApi.adviceTurn({ ...ADVICE, extra_categories: ['repair'] })] },
    )

    await within(await findPanel()).findByText('Wulkanizacja Nowa')
    for (const name of [/^Tyres/, /^Repair/])
      expect(chip(panel(), name)).toHaveAttribute('aria-pressed', 'true')
    expect(placeNames(panel())).toEqual(['Auto Serwis Hoża', 'Wulkanizacja Nowa', 'Opony Max'])
  })

  it('the preview opens a full map with the list, chips and the attribution', async () => {
    const { user } = openIncident()
    await within(await findPanel()).findByText('Wulkanizacja Nowa')

    await user.click(within(panel()).getByRole('button', { name: en.nearby.openMap }))

    const map = screen.getByRole('dialog', { name: en.nearby.mapLabel })
    expect(placeNames(map)).toEqual(['Wulkanizacja Nowa', 'Opony Max'])
    expect(within(map).getByRole('link', { name: en.nearby.attribution })).toHaveAttribute(
      'href',
      'https://www.openstreetmap.org/copyright',
    )
    await user.click(chip(map, /^All/))
    expect(placeNames(map)).toHaveLength(PLACES.length)
    expect(within(map).getByRole('link', { name: 'Call Auto Serwis Hoża' })).toHaveAttribute(
      'href',
      'tel:+48220000001',
    )

    await user.click(within(map).getByRole('button', { name: en.nearby.closeMap }))
    expect(screen.queryByRole('dialog', { name: en.nearby.mapLabel })).not.toBeInTheDocument()
    expect(fakeApi.nearbyRequests).toHaveLength(1)
  })

  it('tapping a place in the preview opens the map on it', async () => {
    const { user } = openIncident()

    await user.click(
      await within(await findPanel()).findByRole('button', { name: /^Wulkanizacja Nowa/ }),
    )

    const map = screen.getByRole('dialog', { name: en.nearby.mapLabel })
    expect(within(map).getByRole('button', { name: /^Wulkanizacja Nowa/ })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('offers "Search within 25 km" when nothing is found within 5 km', async () => {
    fakeApi.nearbyScript = [[], [place(9, 'tyres', { name: 'Far Tyres', distance_m: 18_000 })]]
    const { user } = openIncident()

    expect(
      await within(await findPanel()).findByText('No places found within 5 km.'),
    ).toBeInTheDocument()
    await user.click(within(panel()).getByRole('button', { name: en.nearby.widen }))

    expect(await within(await findPanel()).findByText('Far Tyres')).toBeInTheDocument()
    expect(within(panel()).getByText('Within 25 km, nearest first')).toBeInTheDocument()
    expect(fakeApi.nearbyRequests.map((r) => r.body)).toEqual([{ radius_km: 5 }, { radius_km: 25 }])
  })

  it('shows "Search within 25 km" when the chosen category has nothing within 5 km', async () => {
    fakeApi.nearbyScript = [[place(1, 'fuel', { name: 'Orlen' })]]
    openIncident()

    expect(
      await within(await findPanel()).findByText(/None of these within 5 km/),
    ).toBeInTheDocument()
    expect(within(panel()).getByRole('button', { name: en.nearby.widen })).toBeInTheDocument()
  })

  it('a failed lookup shows a retry and keeps the previous results', async () => {
    fakeApi.nearbyScript = [{ status: 503, reason: 'nearby_unavailable' }, PLACES]
    const previous = {
      status: 'found' as const,
      places: [place(1, 'fuel', { name: 'Orlen' })],
      radius_km: 5,
      fetched_at: '2026-11-10T09:00:00.000Z',
    }
    const { user } = openIncident({}, { nearby: previous })

    await user.click(
      await within(await findPanel()).findByRole('button', { name: en.nearby.widen }),
    )

    const alert = await within(await findPanel()).findByRole('alert')
    expect(alert).toHaveTextContent(en.nearby.unavailable)
    expect(alert).toHaveTextContent(en.errors.nearby_unavailable)
    expect(alert).toHaveTextContent(en.nearby.earlier)
    await user.click(chip(panel(), /^All/))
    expect(placeNames(panel())).toEqual(['Orlen'])

    await user.click(within(alert).getByRole('button', { name: en.nearby.retry }))

    expect(await within(await findPanel()).findByText('Wulkanizacja Nowa')).toBeInTheDocument()
    expect(within(panel()).queryByRole('alert')).not.toBeInTheDocument()
    // "Try again" repeats the radius that failed.
    expect(fakeApi.nearbyRequests.map((r) => r.body.radius_km)).toEqual([25, 25])
  })

  it('demo mode without recorded places says so, with no retry that cannot help', async () => {
    fakeApi.nearbyScript = [{ status: 503, reason: 'nearby_not_recorded' }]
    openIncident()

    const alert = await within(await findPanel()).findByRole('alert')
    expect(alert).toHaveTextContent(en.errors.nearby_not_recorded)
    expect(within(alert).queryByRole('button')).not.toBeInTheDocument()
  })

  it('a failed first lookup shows a retry instead of places', async () => {
    fakeApi.nearbyScript = [{ status: 503, reason: 'nearby_unavailable' }]
    const { user } = openIncident()

    const alert = await within(await findPanel()).findByRole('alert')
    expect(alert).toHaveTextContent(en.nearby.unavailable)
    await user.click(within(alert).getByRole('button', { name: en.nearby.retry }))

    expect(await within(await findPanel()).findByText('Wulkanizacja Nowa')).toBeInTheDocument()
  })

  it('shows a waiting state while it looks', async () => {
    server.use(
      http.post(`${API}/api/v1/incidents/:id/nearby`, async () => {
        await delay('infinite')
        return HttpResponse.json({})
      }),
    )
    openIncident()

    expect(await within(await findPanel()).findByText(en.nearby.searching)).toBeInTheDocument()
    expect(panel()).toHaveAttribute('aria-busy', 'true')
  })

  it('without a location shows a clear state, not an error, and asks nothing', async () => {
    openIncident({ location: null })

    expect(await within(await findPanel()).findByText(en.nearby.noLocation)).toBeInTheDocument()
    expect(within(panel()).getByRole('link', { name: en.nearby.setLocation })).toHaveAttribute(
      'href',
      '/incidents/1/edit',
    )
    expect(within(panel()).queryByRole('alert')).not.toBeInTheDocument()
    expect(fakeApi.nearbyRequests).toEqual([])
  })

  it('shows the stored places without a new lookup', async () => {
    const stored = { status: 'found' as const, places: PLACES, radius_km: 5, fetched_at: 'x' }
    openIncident({}, { nearby: stored })

    expect(await within(await findPanel()).findByText('Wulkanizacja Nowa')).toBeInTheDocument()
    expect(fakeApi.nearbyRequests).toEqual([])
  })

  it('a resolved incident waits for the driver to ask', async () => {
    const { user } = openIncident({}, { status: 'resolved' })

    await user.click(await within(await findPanel()).findByRole('button', { name: en.nearby.find }))

    expect(await within(await findPanel()).findByText('Wulkanizacja Nowa')).toBeInTheDocument()
    expect(fakeApi.nearbyRequests).toHaveLength(1)
  })

  it('never renders anything from an AI turn as a place', async () => {
    const advice = {
      ...ADVICE,
      steps: ['Drive to Garage From The Model on Main Street', 'Call your assistance'],
      extra_categories: ['tyres' as const],
    }
    fakeApi.nearbyScript = [[]]
    openIncident({}, { ai_turns: [fakeApi.adviceTurn(advice)] })

    expect(
      await within(await findPanel()).findByText('No places found within 5 km.'),
    ).toBeInTheDocument()
    expect(within(panel()).queryByText(/Garage From The Model/)).not.toBeInTheDocument()
    expect(within(panel()).queryByRole('list')).not.toBeInTheDocument()
  })
})

describe('Nearby in the help flow', () => {
  it('looks up in parallel with the AI turn, and a failed turn leaves the places alone', async () => {
    stubGeolocation({ latitude: 52.2297, longitude: 21.0122, accuracy: 12 })
    fakeApi.turnScript = [{ status: 504, reason: 'timeout' }]
    const { user } = renderApp('/')

    await user.click(await screen.findByRole('button', { name: 'Flat tyre' }))
    const sheet = await screen.findByRole('dialog', { name: 'Flat tyre' })
    await waitFor(() => {
      expect(within(sheet).queryByText(/Finding your location/i)).not.toBeInTheDocument()
    })
    await user.click(within(sheet).getByRole('button', { name: 'Get help now' }))

    const ai = await screen.findByRole('region', { name: 'Personalised steps' })
    expect(await within(ai).findByRole('button', { name: en.ai.retry })).toBeInTheDocument()
    expect(await within(await findPanel()).findByText('Wulkanizacja Nowa')).toBeInTheDocument()
    expect(within(panel()).queryByRole('alert')).not.toBeInTheDocument()
    expect(fakeApi.nearbyRequests).toEqual([{ incidentId: 1, body: { radius_km: 5 } }])
  })

  it('a location edit clears the places and looks up again around the new point', async () => {
    fakeApi.config.demo_mode = false
    stubGeolocation({ latitude: 50.06, longitude: 19.94, accuracy: 9 })
    const stored = { status: 'found' as const, places: PLACES, radius_km: 5, fetched_at: 'x' }
    const incident = fakeApi.seedIncident(
      { problem_type: 'flat_tyre', location: LOCATION },
      { nearby: stored },
    )
    const { user } = renderApp(`/incidents/${String(incident.id)}/edit`)

    await user.click(await screen.findByRole('button', { name: 'Use my current location' }))
    await screen.findByText('50.06000, 19.94000')
    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })
    await waitFor(() => {
      expect(fakeApi.nearbyRequests).toEqual([{ incidentId: 1, body: { radius_km: 5 } }])
    })
    expect(await within(panel()).findByText('Wulkanizacja Nowa')).toBeInTheDocument()
  })
})
