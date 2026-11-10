import { screen, waitFor, within } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { API, fakeApi, problem } from './fakeApi'
import { renderApp } from './render'
import { server } from './setup'

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
