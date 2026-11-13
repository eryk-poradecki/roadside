import { act, screen, within } from '@testing-library/react'
import { fakeApi } from './fakeApi'
import { renderApp } from './render'
import { asDesktop, atWidth, resizableViewport } from './viewport'

const EMERGENCY = 'Call emergency number 112'

describe('desktop shell (ADR 0012)', () => {
  beforeEach(() => {
    fakeApi.seed({ name: 'Golf' })
  })

  it('switches to the sidebar at 1024 px', async () => {
    atWidth(1024)
    renderApp('/incidents')
    const nav = await screen.findByRole('navigation', { name: 'Main' })
    expect(nav.closest('aside')).not.toBeNull()
    expect(within(nav).getByRole('link', { name: 'History' })).toHaveAttribute(
      'aria-current',
      'page',
    )
  })

  it('keeps the mobile layout at 1023 px: tab bar and 112', async () => {
    atWidth(1023)
    renderApp('/incidents')
    const nav = await screen.findByRole('navigation', { name: 'Main' })
    expect(nav.closest('aside')).toBeNull()
    expect(screen.getByRole('link', { name: EMERGENCY })).toBeInTheDocument()
  })

  it('keeps what the driver typed when the window crosses the breakpoint', async () => {
    const viewport = resizableViewport(1023)
    const { user } = renderApp('/vehicles/new')
    await user.type(await screen.findByLabelText('Name *'), 'Golf')
    act(() => {
      viewport.resize(1280)
    })
    expect(await screen.findByRole('navigation', { name: 'Main' })).toBeInTheDocument()
    expect(screen.getByLabelText('Name *')).toHaveValue('Golf')
  })

  it.each([
    ['/', 'Help'],
    ['/incidents', 'History'],
    ['/incidents/1', 'History'],
    ['/incidents/1/report', 'History'],
    ['/vehicles', 'Vehicles'],
    ['/vehicles/new', 'Vehicles'],
    ['/vehicles/1', 'Vehicles'],
  ])('shows the sidebar on %s with %s highlighted', async (route, current) => {
    asDesktop()
    renderApp(route)
    const nav = await screen.findByRole('navigation', { name: 'Main' })
    for (const name of ['Help', 'History', 'Vehicles']) {
      const link = within(nav).getByRole('link', { name })
      if (name === current) expect(link).toHaveAttribute('aria-current', 'page')
      else expect(link).not.toHaveAttribute('aria-current')
    }
    const sidebar = nav.closest('aside')
    expect(sidebar).not.toBeNull()
    if (sidebar) expect(within(sidebar).getByRole('group', { name: 'Language' })).toBeVisible()
  })

  it.each(['/incidents', '/vehicles', '/vehicles/new', '/vehicles/1'])(
    'has no 112 control on %s',
    async (route) => {
      asDesktop()
      renderApp(route)
      await screen.findByRole('navigation', { name: 'Main' })
      await screen.findByRole('heading', { level: 1 })
      expect(screen.queryByRole('link', { name: EMERGENCY })).not.toBeInTheDocument()
    },
  )

  it('shows 112 on Start only inside the trial column', async () => {
    asDesktop()
    renderApp('/')
    const trial = await screen.findByRole('region', { name: 'Try it here' })
    expect(screen.getAllByRole('link', { name: EMERGENCY })).toHaveLength(1)
    expect(within(trial).getByRole('link', { name: EMERGENCY })).toHaveAttribute('href', 'tel:112')
  })
})

// jsdom runs on localhost: a phone couldn't open it, so there is no QR code (ADR 0012).
// The left side explains the roadside flow instead, beside the trial column.
describe('desktop Start on localhost', () => {
  it('shows how it works at the roadside beside the trial column, with no QR code', async () => {
    asDesktop()
    renderApp('/')
    const how = await screen.findByRole('region', { name: 'How it works at the roadside' })
    expect(within(how).getByRole('heading', { level: 1 })).toBeInTheDocument()
    const steps = within(how).getAllByRole('listitem')
    expect(steps).toHaveLength(3)
    expect(steps[0]).toHaveTextContent('Pick what happened')
    expect(steps[1]).toHaveTextContent('Safety steps appear at once')
    expect(steps[2]).toHaveTextContent('AI advice and real places nearby')
    expect(within(how).getByText(/device mode/)).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /QR code/ })).not.toBeInTheDocument()

    const trial = screen.getByRole('region', { name: 'Try it here' })
    expect(
      await within(trial).findByRole('heading', { name: 'What happened?' }),
    ).toBeInTheDocument()
  })
})
