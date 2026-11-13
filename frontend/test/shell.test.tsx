import { screen } from '@testing-library/react'
import { fakeApi } from './fakeApi'
import { renderApp } from './render'

const TOP_LEVEL = ['/', '/incidents', '/vehicles']
const FLOW = ['/incidents/1', '/incidents/1/report', '/vehicles/new', '/vehicles/1']

describe('app shell', () => {
  beforeEach(() => {
    fakeApi.seed({ name: 'Golf' })
  })

  it.each(['/', '/incidents', '/incidents/1'])('shows the 112 control on %s', async (route) => {
    renderApp(route)
    expect(await screen.findByRole('link', { name: 'Call emergency number 112' })).toHaveAttribute(
      'href',
      'tel:112',
    )
  })

  it.each(['/vehicles', '/vehicles/new', '/vehicles/1', '/incidents/1/report'])(
    'hides the 112 control on at-home screen %s',
    (route) => {
      renderApp(route)
      expect(
        screen.queryByRole('link', { name: 'Call emergency number 112' }),
      ).not.toBeInTheDocument()
    },
  )

  it.each(TOP_LEVEL)('shows the tab bar on top-level screen %s', async (route) => {
    renderApp(route)
    const nav = await screen.findByRole('navigation', { name: 'Main' })
    expect(nav).toHaveTextContent('Help')
    expect(nav).toHaveTextContent('History')
    expect(nav).toHaveTextContent('Vehicles')
  })

  it.each(FLOW)('hides the tab bar on flow screen %s', async (route) => {
    renderApp(route)
    expect(await screen.findByRole('link', { name: 'Back' })).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: 'Main' })).not.toBeInTheDocument()
  })
})
