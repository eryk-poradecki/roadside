/**
 * @vitest-environment-options {"url": "https://roadside.example.com/"}
 */
import { screen, within } from '@testing-library/react'
import { fakeApi } from './fakeApi'
import { renderApp } from './render'
import { asDesktop, atWidth } from './viewport'

// A public origin: a phone could open it, so desktop Start offers the QR code (ADR 0012).
describe('desktop Start on a public host', () => {
  beforeEach(() => {
    fakeApi.seed({ name: 'Golf' })
  })

  it('shows a QR code for the current origin beside the trial column', async () => {
    asDesktop()
    renderApp('/')
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Open it on your phone' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('img', { name: 'QR code for https://roadside.example.com' }),
    ).toBeInTheDocument()
    const trial = screen.getByRole('region', { name: 'Or try it here' })
    expect(
      await within(trial).findByRole('heading', { name: 'What happened?' }),
    ).toBeInTheDocument()
    expect(within(trial).getByRole('link', { name: 'Call emergency number 112' })).toBeVisible()
  })

  it('shows no QR code on mobile', async () => {
    atWidth(1023)
    renderApp('/')
    expect(await screen.findByRole('heading', { name: 'What happened?' })).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /QR code/ })).not.toBeInTheDocument()
  })

  it('opens the help sheet from the trial column and lands on the Result', async () => {
    asDesktop()
    const { user } = renderApp('/')
    const trial = await screen.findByRole('region', { name: 'Or try it here' })
    await user.click(await within(trial).findByRole('button', { name: 'Flat tyre' }))
    const sheet = await screen.findByRole('dialog', { name: 'Flat tyre' })
    await user.click(within(sheet).getByRole('button', { name: 'Get help now' }))
    expect(await screen.findByRole('region', { name: 'Do this first' })).toBeInTheDocument()
  })
})
