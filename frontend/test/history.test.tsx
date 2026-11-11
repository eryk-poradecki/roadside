import { screen, waitFor, within } from '@testing-library/react'
import { en } from '../src/i18n/en'
import { fakeApi } from './fakeApi'
import { renderApp } from './render'

const list = () => screen.getByRole('list', { name: 'Your incidents' })
const items = () => within(list()).getAllByRole('listitem')
const checklistRegion = () => screen.queryByRole('region', { name: 'Do this first' })

describe('History', () => {
  it('lists incidents newest first with their status', async () => {
    fakeApi.seedIncident({ problem_type: 'flat_tyre' }, { created_at: '2026-11-01T08:00:00.000Z' })
    fakeApi.seedIncident(
      { problem_type: 'out_of_fuel' },
      { created_at: '2026-11-03T08:00:00.000Z', status: 'resolved' },
    )
    fakeApi.seedIncident({ problem_type: 'other' }, { created_at: '2026-11-02T08:00:00.000Z' })
    renderApp('/incidents')

    await screen.findByRole('list', { name: 'Your incidents' })
    const [first, second, ...rest] = items()
    if (!first || !second) throw new Error('expected rows')
    expect([first, second, ...rest].map((r) => within(r).getByRole('heading').textContent)).toEqual(
      ['Out of fuel', 'Something else', 'Flat tyre'],
    )
    expect(within(first).getByText('Resolved')).toBeInTheDocument()
    expect(within(second).getByText('Open')).toBeInTheDocument()
    expect(screen.getByText('3 incidents')).toBeInTheDocument()
  })

  it('filters by status', async () => {
    fakeApi.seedIncident({ problem_type: 'flat_tyre' })
    fakeApi.seedIncident({ problem_type: 'flat_battery' }, { status: 'resolved' })
    const { user } = renderApp('/incidents')
    await screen.findByRole('list', { name: 'Your incidents' })

    await user.click(screen.getByRole('button', { name: 'Resolved' }))
    expect(screen.getByRole('button', { name: 'Resolved' })).toHaveAttribute('aria-pressed', 'true')
    await waitFor(() => {
      expect(items()).toHaveLength(1)
    })
    expect(within(list()).getByText('Flat battery')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Open' }))
    await waitFor(() => {
      expect(within(list()).getByText('Flat tyre')).toBeInTheDocument()
    })
    expect(items()).toHaveLength(1)
  })

  it('says so when a filter has nothing, and when there is no history yet', async () => {
    const { user } = renderApp('/incidents')
    expect(await screen.findByText(en.history.empty)).toBeInTheDocument()
    fakeApi.seedIncident({ problem_type: 'flat_tyre' })
    await user.click(screen.getByRole('button', { name: 'Resolved' }))
    expect(await screen.findByText(en.history.emptyResolved)).toBeInTheDocument()
  })

  it('pages with Show more', async () => {
    for (let day = 1; day <= 25; day++)
      fakeApi.seedIncident(
        { problem_type: 'other' },
        { created_at: `2026-10-${String(day).padStart(2, '0')}T08:00:00.000Z` },
      )
    const { user } = renderApp('/incidents')
    await screen.findByRole('list', { name: 'Your incidents' })
    expect(items()).toHaveLength(20)
    await user.click(screen.getByRole('button', { name: 'Show more' }))
    await waitFor(() => {
      expect(items()).toHaveLength(25)
    })
    expect(screen.queryByRole('button', { name: 'Show more' })).not.toBeInTheDocument()
  })

  it('opens the incident detail', async () => {
    const golf = fakeApi.seed({ name: 'Golf' })
    const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre', vehicle_id: golf.id })
    const { user } = renderApp('/incidents')
    const row = await screen.findByRole('link', { name: /Flat tyre/ })
    expect(within(row).getByText('Golf')).toBeInTheDocument()
    await user.click(row)
    expect(await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })).toBeInTheDocument()
    expect(fakeApi.incidents[0]?.id).toBe(incident.id)
  })
})

describe('incident upkeep', () => {
  it('marks an incident resolved, folding the checklist, and reopens it', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre' })
    const { user } = renderApp(`/incidents/${String(incident.id)}`)

    await user.click(await screen.findByRole('button', { name: 'Mark resolved' }))

    expect(await screen.findByRole('button', { name: 'Reopen' })).toBeInTheDocument()
    expect(screen.getByText('Resolved', { selector: '.status' })).toBeInTheDocument()
    expect(fakeApi.requests).toContainEqual({ method: 'PATCH', body: { status: 'resolved' } })
    expect(fakeApi.incidents[0]?.status).toBe('resolved')
    // The whole checklist, first step included, folds into one "Safety steps" disclosure.
    expect(checklistRegion()).not.toBeInTheDocument()
    const fold = screen.getByText('Safety steps').closest('details')
    if (!fold) throw new Error('expected the fold')
    expect(fold).not.toHaveAttribute('open')
    expect(within(fold).getByText(en.checklist.lists.tyre.first)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Reopen' }))
    expect(await screen.findByRole('button', { name: 'Mark resolved' })).toBeInTheDocument()
    expect(fakeApi.incidents[0]?.status).toBe('open')
    expect(checklistRegion()).toBeInTheDocument()
    expect(screen.queryByText('Safety steps')).not.toBeInTheDocument()
  })

  it('shows the folded checklist when a resolved incident is opened', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'flat_battery' }, { status: 'resolved' })
    const { user } = renderApp(`/incidents/${String(incident.id)}`)
    const summary = await screen.findByText('Safety steps')
    expect(checklistRegion()).not.toBeInTheDocument()
    await user.click(summary)
    expect(summary.closest('details')).toHaveAttribute('open')
  })

  it('deletes an incident after confirming and returns to History', async () => {
    const keep = fakeApi.seedIncident({ problem_type: 'other' })
    const gone = fakeApi.seedIncident({ problem_type: 'flat_tyre' })
    const { user } = renderApp(`/incidents/${String(gone.id)}`)

    await user.click(await screen.findByRole('button', { name: 'Delete incident' }))
    const confirm = screen.getByRole('group', { name: 'Delete incident' })
    await user.click(within(confirm).getByRole('button', { name: 'Cancel' }))
    expect(fakeApi.incidents).toHaveLength(2)

    await user.click(screen.getByRole('button', { name: 'Delete incident' }))
    await user.click(screen.getByRole('button', { name: 'Yes, delete' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'History' })).toBeInTheDocument()
    expect(fakeApi.incidents.map((i) => i.id)).toEqual([keep.id])
    await waitFor(() => {
      expect(items()).toHaveLength(1)
    })
    expect(within(list()).queryByText('Flat tyre')).not.toBeInTheDocument()
  })

  it('edits the note, problem type and vehicle, sending only what changed', async () => {
    const golf = fakeApi.seed({ name: 'Golf' })
    const yaris = fakeApi.seed({ name: 'Yaris' })
    const incident = fakeApi.seedIncident({
      problem_type: 'flat_tyre',
      vehicle_id: golf.id,
      note: 'Rear left',
    })
    const { user } = renderApp(`/incidents/${String(incident.id)}`)

    await user.click(await screen.findByRole('link', { name: 'Edit details' }))
    await screen.findByRole('heading', { level: 1, name: 'Edit incident' })
    const note = screen.getByLabelText('Note')
    expect(note).toHaveValue('Rear left')
    await user.clear(note)
    await user.type(note, 'Front right')
    await user.click(screen.getByRole('radio', { name: 'Flat battery' }))
    await user.click(screen.getByRole('radio', { name: 'Yaris' }))
    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Flat battery' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Yaris')).toBeInTheDocument()
    expect(fakeApi.requests).toContainEqual({
      method: 'PATCH',
      body: { note: 'Front right', problem_type: 'flat_battery', vehicle_id: yaris.id },
    })
  })

  it('changes where the car is, which switches the checklist', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'flat_battery' })
    const { user } = renderApp(`/incidents/${String(incident.id)}/edit`)

    const where = await screen.findByRole('group', { name: 'Where is the car?' })
    expect(within(where).getByRole('radio', { name: 'On the road' })).toBeChecked()
    await user.click(within(where).getByRole('radio', { name: 'Parked (parking lot, driveway)' }))
    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    expect(await screen.findByText(en.checklist.parkedLists.battery.first)).toBeInTheDocument()
    expect(fakeApi.requests).toContainEqual({ method: 'PATCH', body: { situation: 'parked' } })
  })

  it('removes and replaces the location', async () => {
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: {
        getCurrentPosition: (ok: PositionCallback) => {
          ok({ coords: { latitude: 50.06, longitude: 19.94, accuracy: 9 } } as GeolocationPosition)
        },
      },
    })
    const incident = fakeApi.seedIncident({
      problem_type: 'other',
      location: { lat: 52.2297, lon: 21.0122 },
    })
    const { user } = renderApp(`/incidents/${String(incident.id)}/edit`)

    await user.click(await screen.findByRole('button', { name: 'Remove location' }))
    expect(screen.getByText('No location')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Use my current location' }))
    expect(await screen.findByText('50.06000, 19.94000')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Save changes' }))

    await screen.findByRole('heading', { level: 1, name: 'Something else' })
    expect(fakeApi.requests).toContainEqual({
      method: 'PATCH',
      body: { location: { lat: 50.06, lon: 19.94, accuracy_m: 9 } },
    })
    Reflect.deleteProperty(navigator, 'geolocation')
  })

  it('saves nothing when nothing changed', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'other', note: 'x' })
    const { user } = renderApp(`/incidents/${String(incident.id)}/edit`)
    await user.click(await screen.findByRole('button', { name: 'Save changes' }))
    await screen.findByRole('heading', { level: 1, name: 'Something else' })
    expect(fakeApi.requests.filter((r) => r.method === 'PATCH')).toHaveLength(0)
  })
})
