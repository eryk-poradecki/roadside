import { screen, within } from '@testing-library/react'
import { fakeApi } from './fakeApi'
import { renderApp } from './render'
import { asDesktop } from './viewport'

const EMERGENCY = 'Call emergency number 112'
const AT = { lat: 51.80123, lon: 19.29408, accuracy_m: 12 }
/** The incident's header: its title, vehicle, place and, on desktop, 112. */
const header = () => {
  const head = screen.getByRole('heading', { level: 1, name: 'Flat tyre' }).closest('header')
  if (!head) throw new Error('no incident header')
  return head
}

/** An incident with a stored advice turn, `urgent` or not. */
function answered(status: 'open' | 'resolved', urgent = false) {
  return fakeApi.seedIncident(
    { problem_type: 'flat_tyre', location: AT },
    { status, ai_turns: [fakeApi.adviceTurn(undefined, 'en', { urgent })] },
  )
}

describe('incident header on desktop (ADR 0012)', () => {
  beforeEach(() => {
    asDesktop()
  })

  it('has a 112 link while the incident is open', async () => {
    const incident = answered('open')
    renderApp(`/incidents/${String(incident.id)}`)
    await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })
    const link = within(header()).getByRole('link', { name: EMERGENCY })
    expect(link).toHaveAttribute('href', 'tel:112')
    expect(link).not.toHaveClass('head-sos-urgent')
    expect(screen.getAllByRole('link', { name: EMERGENCY })).toHaveLength(1)
  })

  it('styles the 112 link as urgent when the AI answer is urgent', async () => {
    const incident = answered('open', true)
    renderApp(`/incidents/${String(incident.id)}`)
    await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })
    expect(within(header()).getByRole('link', { name: EMERGENCY })).toHaveClass('head-sos-urgent')
    expect(
      within(screen.getByRole('alert')).getByRole('link', { name: EMERGENCY }),
    ).toHaveAttribute('href', 'tel:112')
  })

  it('has no 112 once the incident is resolved', async () => {
    const incident = answered('resolved', true)
    renderApp(`/incidents/${String(incident.id)}`)
    await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })
    expect(screen.queryByRole('link', { name: EMERGENCY })).not.toBeInTheDocument()
  })
})

describe('desktop assistance from the incident vehicle', () => {
  beforeEach(() => {
    asDesktop()
  })

  it('uses current assistance details of the incident vehicle, never the default', async () => {
    fakeApi.seed({
      name: 'Default',
      assistance_phone: '999999',
      assistance_insurer: 'Default insurer',
    })
    const vehicle = fakeApi.seed({
      name: 'Family',
      assistance_phone: '+48 123 456',
      assistance_insurer: 'Family insurer',
      policy_number: 'POL-42',
    })
    const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre', vehicle_id: vehicle.id })
    renderApp(`/incidents/${String(incident.id)}`)
    const phone = await screen.findByRole('link', { name: '+48 123 456' })
    expect(phone).toHaveAttribute('href', 'tel:+48123456')
    expect(header()).toHaveTextContent('Assistance: Family insurer')
    expect(header()).toHaveTextContent('Policy POL-42')
    expect(screen.queryByText('Default insurer')).not.toBeInTheDocument()
  })

  it.each(['resolved', 'no phone', 'no vehicle', 'deleted vehicle'] as const)(
    'hides assistance with %s',
    async (scenario) => {
      fakeApi.seed({ name: 'Default', assistance_phone: '999999' })
      const vehicle = fakeApi.seed({
        name: 'Family',
        assistance_phone: scenario === 'no phone' ? null : '123456',
      })
      const incident = fakeApi.seedIncident(
        { problem_type: 'flat_tyre', vehicle_id: scenario === 'no vehicle' ? null : vehicle.id },
        { status: scenario === 'resolved' ? 'resolved' : 'open' },
      )
      if (scenario === 'deleted vehicle')
        fakeApi.vehicles = fakeApi.vehicles.filter((v) => v.id !== vehicle.id)
      renderApp(`/incidents/${String(incident.id)}`)
      await screen.findByRole('heading', { name: 'Flat tyre', level: 1 })
      expect(screen.queryByRole('link', { name: '123456' })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: '999999' })).not.toBeInTheDocument()
      expect(header()).not.toHaveTextContent('Assistance:')
    },
  )
})

describe('incident header on mobile', () => {
  it('leaves 112 to the dock', async () => {
    const incident = answered('open')
    renderApp(`/incidents/${String(incident.id)}`)
    await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })
    expect(within(header()).queryByRole('link', { name: EMERGENCY })).not.toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: EMERGENCY })).toHaveLength(1)
  })
})

describe('incident location', () => {
  it('shows the place name instead of coordinates after the first AI turn', async () => {
    fakeApi.geocodeLabel = 'Krzywa, Aleksandrów Łódzki'
    const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre', location: AT })
    renderApp({ pathname: `/incidents/${String(incident.id)}`, state: { fromHelp: true } })
    await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })
    expect(header()).toHaveTextContent('51.80123, 19.29408')
    expect(await within(header()).findByText('Krzywa, Aleksandrów Łódzki')).toBeInTheDocument()
    expect(header()).not.toHaveTextContent('51.80123')
  })
})
