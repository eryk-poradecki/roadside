import { screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { API, fakeApi, problem } from './fakeApi'
import { renderApp } from './render'
import { server } from './setup'
import { asDesktop, atWidth } from './viewport'

describe('demo vehicles', () => {
  beforeEach(() => {
    fakeApi.config.demo_mode = true
  })
  it('waits for config before offering vehicle actions', async () => {
    const demo = fakeApi.seed({ name: 'Golf' })
    demo.demo_profile = 'golf_2017'
    let releaseConfig = () => {}
    const configGate = new Promise<void>((resolve) => {
      releaseConfig = resolve
    })
    let vehiclesRead = false
    server.use(
      http.get(`${API}/api/v1/config`, async () => {
        await configGate
        return HttpResponse.json({ ...fakeApi.config })
      }),
      http.get(`${API}/api/v1/vehicles`, () => {
        vehiclesRead = true
        return HttpResponse.json([demo])
      }),
    )
    renderApp('/vehicles')
    try {
      await waitFor(() => {
        expect(vehiclesRead).toBe(true)
      })
      expect(screen.queryByRole('link', { name: 'Edit Golf' })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Delete Golf' })).not.toBeInTheDocument()
    } finally {
      releaseConfig()
    }
    expect(await screen.findByText('Demo vehicle')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Delete Golf' })).not.toBeInTheDocument()
  })
  it('keeps marked vehicles editable when demo mode is off', async () => {
    fakeApi.config.demo_mode = false
    const demo = fakeApi.seed({ name: 'Golf' })
    demo.demo_profile = 'golf_2017'
    renderApp('/vehicles')
    expect(await screen.findByRole('link', { name: 'Edit Golf' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Delete Golf' })).toBeInTheDocument()
    expect(screen.queryByText('Demo vehicle')).not.toBeInTheDocument()
    expect(screen.queryByText(/Demo scenarios use the demo vehicles/)).not.toBeInTheDocument()
  })

  it('shows the specific read-only error when a stale vehicle form is refused', async () => {
    const demo = fakeApi.seed({ name: 'Golf' })
    demo.demo_profile = 'golf_2017'
    server.use(
      http.put(`${API}/api/v1/vehicles/:id`, () =>
        problem(403, 'demo_vehicle_read_only', 'Internal detail'),
      ),
    )
    const { user } = renderApp(`/vehicles/${String(demo.id)}`)
    await user.type(await screen.findByLabelText(/^Name/), ' GTI')
    await user.click(screen.getByRole('button', { name: 'Save vehicle' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Demo vehicles can only be made the default in demo mode.',
    )
    expect(screen.queryByText('Something went wrong. Please try again.')).not.toBeInTheDocument()
  })

  it('can make a demo vehicle the default without sending its read-only marker', async () => {
    fakeApi.seed({ name: 'My vehicle' })
    const demo = fakeApi.seed({ name: 'Golf' })
    demo.demo_profile = 'golf_2017'
    server.use(
      http.put(`${API}/api/v1/vehicles/${String(demo.id)}`, async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>
        if ('demo_profile' in body) return problem(422, 'validation_error', 'Extra field')
        if (body.is_default !== true) return problem(403, 'demo_vehicle_read_only', 'Read only')
        fakeApi.vehicles = fakeApi.vehicles.map((v) => ({ ...v, is_default: v.id === demo.id }))
        return HttpResponse.json({ ...demo, is_default: true })
      }),
    )
    const { user } = renderApp('/vehicles')
    await user.click(await screen.findByRole('button', { name: 'Set Golf as default' }))
    await waitFor(() => {
      const card = screen.getByRole('heading', { name: 'Golf' }).closest('li')
      if (!card) throw new Error('Golf must be in a vehicle card')
      expect(within(card).getByText('Default')).toBeInTheDocument()
      expect(within(card).getByText('Demo vehicle')).toBeInTheDocument()
    })
  })
  it.each([390, 1280, 1440, 1920])('protects only marked vehicles at %i px', async (width) => {
    atWidth(width)
    const demo = fakeApi.seed({ name: 'Golf' })
    demo.demo_profile = 'golf_2017'
    fakeApi.seed({ name: 'My vehicle' })
    renderApp('/vehicles')

    const list = await screen.findByRole('list', { name: 'Your vehicles' })
    const cards = within(list).getAllByRole('listitem')
    const golf = cards.find((card) => within(card).queryByRole('heading', { name: 'Golf' }))
    if (!golf) throw new Error('Golf must be in the vehicle list')
    expect(within(golf).getByText('Demo vehicle')).toBeInTheDocument()
    expect(within(golf).queryByRole('link', { name: 'Edit Golf' })).not.toBeInTheDocument()
    expect(within(golf).queryByRole('button', { name: 'Delete Golf' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Edit My vehicle' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Delete My vehicle' })).toBeInTheDocument()
    expect(
      screen.getByText(
        'Demo scenarios use the demo vehicles. Vehicles you add here are for trying the screen.',
      ),
    ).toBeInTheDocument()
  })
})

describe('vehicle form', () => {
  it('requires a name and sends nothing until it is given', async () => {
    const { user } = renderApp('/vehicles/new')
    await user.click(await screen.findByRole('button', { name: 'Save vehicle' }))

    expect(await screen.findByText('Give the vehicle a name.')).toBeInTheDocument()
    expect(screen.getByLabelText(/^Name/)).toBeInvalid()
    expect(fakeApi.requests).toEqual([])
  })

  it('rejects a year outside 1900–2100', async () => {
    const { user } = renderApp('/vehicles/new')
    await user.type(await screen.findByLabelText(/^Name/), 'Golf')
    await user.type(screen.getByLabelText('Year'), '1850')
    await user.click(screen.getByRole('button', { name: 'Save vehicle' }))

    expect(await screen.findByText('Enter a year between 1900 and 2100.')).toBeInTheDocument()
    expect(fakeApi.requests).toEqual([])
  })

  it('hides transmission for an electric vehicle and sends it as null', async () => {
    const { user } = renderApp('/vehicles/new')
    await user.type(await screen.findByLabelText(/^Name/), 'Leaf')
    await user.selectOptions(screen.getByLabelText('Transmission'), 'automatic')
    await user.selectOptions(screen.getByLabelText('Fuel type'), 'electric')

    expect(screen.queryByLabelText('Transmission')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Save vehicle' }))

    await waitFor(() => {
      expect(fakeApi.requests).toHaveLength(1)
    })
    expect(fakeApi.requests[0]?.body).toMatchObject({ fuel_type: 'electric', transmission: null })
  })

  it('shows the wheel-lock key location only when wheel locks are on', async () => {
    const { user } = renderApp('/vehicles/new')
    await user.type(await screen.findByLabelText(/^Name/), 'Golf')
    expect(screen.queryByLabelText('Where is the wheel-lock key?')).not.toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Wheel locks'), 'yes')
    await user.type(screen.getByLabelText('Where is the wheel-lock key?'), 'glovebox')
    await user.selectOptions(screen.getByLabelText('Wheel locks'), 'no')
    expect(screen.queryByLabelText('Where is the wheel-lock key?')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Save vehicle' }))
    await waitFor(() => {
      expect(fakeApi.requests).toHaveLength(1)
    })
    expect(fakeApi.requests[0]?.body).toMatchObject({ wheel_locks: false, lock_key_location: null })
  })

  it('records registration and assistance details, with blanks sent as null', async () => {
    const { user } = renderApp('/vehicles/new')
    await user.type(await screen.findByLabelText(/^Name/), '  Golf  ')
    await user.type(screen.getByLabelText('Registration plate'), 'WA 12345')
    await user.type(screen.getByLabelText('Assistance provider'), 'PZU Pomoc')
    await user.type(screen.getByLabelText('Assistance phone'), '+48 22 111 22 33')
    await user.type(screen.getByLabelText('Policy number'), 'POL-9')
    await user.click(screen.getByRole('button', { name: 'Save vehicle' }))

    await waitFor(() => {
      expect(fakeApi.requests).toHaveLength(1)
    })
    expect(fakeApi.requests[0]?.body).toMatchObject({
      name: 'Golf',
      registration: 'WA 12345',
      assistance_insurer: 'PZU Pomoc',
      assistance_phone: '+48 22 111 22 33',
      policy_number: 'POL-9',
      make_model: null,
      year: null,
    })
    expect(await screen.findByRole('heading', { name: 'Vehicles' })).toBeInTheDocument()
  })
})

describe('vehicles list', () => {
  it('shows the first vehicle added as the default', async () => {
    const { user } = renderApp('/vehicles')
    expect(await screen.findByText(/No vehicles yet/)).toBeInTheDocument()

    await user.click(screen.getByRole('link', { name: 'Add a vehicle' }))
    await user.type(await screen.findByLabelText(/^Name/), 'Golf')
    expect(screen.getByLabelText('Use as my default vehicle')).toBeChecked()
    await user.click(screen.getByRole('button', { name: 'Save vehicle' }))

    const list = await screen.findByRole('list', { name: 'Your vehicles' })
    expect(within(list).getByText('Default')).toBeInTheDocument()
    expect(
      within(list).queryByRole('button', { name: /Set Golf as default/ }),
    ).not.toBeInTheDocument()
  })

  it('moves the default to another vehicle', async () => {
    fakeApi.seed({ name: 'Golf' })
    fakeApi.seed({ name: 'Polo' })
    const { user } = renderApp('/vehicles')

    await user.click(await screen.findByRole('button', { name: 'Set Polo as default' }))

    await waitFor(() => {
      const [first] = screen.getAllByRole('listitem')
      expect(first).toBeDefined()
      if (!first) return
      expect(within(first).getByRole('heading', { name: 'Polo' })).toBeInTheDocument()
      expect(within(first).getByText('Default')).toBeInTheDocument()
    })
    expect(screen.getAllByText('Default')).toHaveLength(1)
  })

  it('leaves no default after the default is deleted', async () => {
    fakeApi.seed({ name: 'Golf' })
    fakeApi.seed({ name: 'Polo' })
    const { user } = renderApp('/vehicles')

    await user.click(await screen.findByRole('button', { name: 'Delete Golf' }))
    await user.click(screen.getByRole('button', { name: 'Yes, delete' }))

    expect(await screen.findByText(/No default vehicle/)).toBeInTheDocument()
    expect(screen.queryByText('Default')).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Golf' })).not.toBeInTheDocument()
  })

  it('edits a vehicle', async () => {
    fakeApi.seed({ name: 'Golf', year: 2015 })
    const { user } = renderApp('/vehicles')

    await user.click(await screen.findByRole('link', { name: 'Edit Golf' }))
    const name = await screen.findByLabelText(/^Name/)
    expect(name).toHaveValue('Golf')
    expect(screen.getByLabelText('Year')).toHaveValue('2015')
    await user.clear(name)
    await user.type(name, 'Golf GTI')
    await user.click(screen.getByRole('button', { name: 'Save vehicle' }))

    expect(await screen.findByRole('heading', { name: 'Golf GTI' })).toBeInTheDocument()
  })
})

describe('API errors', () => {
  it('shows a translated message chosen by reason, never the server detail', async () => {
    server.use(
      http.get(`${API}/api/v1/vehicles`, () =>
        problem(503, 'database_unavailable', 'sqlite3.OperationalError: disk I/O error'),
      ),
    )
    renderApp('/vehicles')

    expect(
      await screen.findByText('The service is having trouble right now. Please try again shortly.'),
    ).toBeInTheDocument()
    expect(screen.queryByText(/sqlite3/)).not.toBeInTheDocument()
  })

  it('falls back to a generic message for an unknown reason', async () => {
    fakeApi.seed({ name: 'Golf' })
    server.use(
      http.delete(`${API}/api/v1/vehicles/:id`, () => problem(500, 'kaboom', 'stack trace here')),
    )
    const { user } = renderApp('/vehicles')
    await user.click(await screen.findByRole('button', { name: 'Delete Golf' }))
    await user.click(screen.getByRole('button', { name: 'Yes, delete' }))

    expect(await screen.findByText('Something went wrong. Please try again.')).toBeInTheDocument()
    expect(screen.queryByText(/stack trace/)).not.toBeInTheDocument()
  })

  it('treats a fetch with no response as offline', async () => {
    server.use(http.get(`${API}/api/v1/vehicles`, () => HttpResponse.error()))
    renderApp('/vehicles')

    expect(await screen.findByText(/You're offline/)).toBeInTheDocument()
  })

  it('shows the form validation message when the server answers 422', async () => {
    server.use(
      http.post(`${API}/api/v1/vehicles`, () =>
        problem(422, 'validation_error', 'Invalid request'),
      ),
    )
    const { user } = renderApp('/vehicles/new')
    await user.type(await screen.findByLabelText(/^Name/), 'Golf')
    await user.click(screen.getByRole('button', { name: 'Save vehicle' }))

    expect(await screen.findByText(/Some details aren't valid/)).toBeInTheDocument()
    expect(screen.queryByText('Invalid request')).not.toBeInTheDocument()
  })
})

describe('vehicles on desktop (ADR 0012, #67)', () => {
  beforeEach(() => {
    asDesktop()
  })

  it('shows the list beside a prompt to pick a vehicle', async () => {
    fakeApi.seed({ name: 'Golf' })
    renderApp('/vehicles')

    expect(await screen.findByRole('list', { name: 'Your vehicles' })).toBeInTheDocument()
    expect(screen.getByText('Pick a vehicle to edit it, or add a new one.')).toBeInTheDocument()
  })

  it('edits a vehicle beside the list, which marks it as the one open', async () => {
    const golf = fakeApi.seed({ name: 'Golf' })
    fakeApi.seed({ name: 'Mini' })
    const { user } = renderApp(`/vehicles/${String(golf.id)}`)

    const list = await screen.findByRole('list', { name: 'Your vehicles' })
    const card = within(list).getByRole('heading', { name: 'Golf' }).closest('li')
    expect(card).toHaveAttribute('aria-current', 'true')
    // The form beside it is where this vehicle changes: no card action races its draft.
    expect(screen.queryByRole('button', { name: 'Delete Golf' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Set Golf as default' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Edit vehicle' })).toBeInTheDocument()
    const name = await screen.findByLabelText(/^Name/)
    expect(name).toHaveValue('Golf')

    await user.click(within(list).getByRole('link', { name: 'Edit Mini' }))
    expect(await screen.findByLabelText(/^Name/)).toHaveValue('Mini')
  })

  it('adds a vehicle beside the list', async () => {
    fakeApi.seed({ name: 'Golf' })
    renderApp('/vehicles/new')

    expect(await screen.findByRole('list', { name: 'Your vehicles' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'New vehicle' })).toBeInTheDocument()
    expect(await screen.findByLabelText(/^Name/)).toHaveValue('')
  })
})
