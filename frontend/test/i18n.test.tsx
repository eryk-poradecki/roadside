import { screen } from '@testing-library/react'
import { i18n } from '../src/i18n'
import { renderApp } from './render'

describe('Polish plurals', () => {
  it.each([
    [1, '1 pojazd'],
    [2, '2 pojazdy'],
    [3, '3 pojazdy'],
    [4, '4 pojazdy'],
    [5, '5 pojazdów'],
    [11, '11 pojazdów'],
    [12, '12 pojazdów'],
    [13, '13 pojazdów'],
    [14, '14 pojazdów'],
    [22, '22 pojazdy'],
    [25, '25 pojazdów'],
  ])('%i → %s', (count, expected) => {
    expect(i18n.t('vehicles.count', { count, lng: 'pl' })).toBe(expected)
  })

  it('uses one and other in English', () => {
    expect(i18n.t('vehicles.count', { count: 1, lng: 'en' })).toBe('1 vehicle')
    expect(i18n.t('vehicles.count', { count: 2, lng: 'en' })).toBe('2 vehicles')
  })
})

describe('language switch', () => {
  it('switches the whole UI to Polish and remembers it', async () => {
    const { user } = renderApp('/')
    expect(await screen.findByRole('heading', { name: 'What happened?' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Polski' }))

    expect(await screen.findByRole('heading', { name: 'Co się stało?' })).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('pl')
    expect(localStorage.getItem('lang')).toBe('pl')
    expect(screen.getByRole('button', { name: 'Polski' })).toHaveAttribute('aria-pressed', 'true')
  })
})
