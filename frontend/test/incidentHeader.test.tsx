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
  })

  it('has no 112 once the incident is resolved', async () => {
    const incident = answered('resolved', true)
    renderApp(`/incidents/${String(incident.id)}`)
    await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })
    expect(screen.queryByRole('link', { name: EMERGENCY })).not.toBeInTheDocument()
  })
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
