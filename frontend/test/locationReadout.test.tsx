import { render, screen } from '@testing-library/react'
import { i18n } from '../src/i18n'
import { LocationReadout } from '../src/components/LocationReadout'

const card = () => screen.getByRole('region', { name: 'Your location' })

describe('location readout', () => {
  it('shows a precise fix to five decimals with its accuracy in metres', () => {
    render(
      <LocationReadout geo={{ status: 'found', lat: 51.80123, lon: 19.29408, accuracy: 12 }} />,
    )
    expect(screen.getByRole('status')).toHaveTextContent('Your location')
    expect(card()).toHaveTextContent('51.80123')
    expect(card()).toHaveTextContent('19.29408')
    expect(card()).toHaveTextContent('Accurate to ~12 m')
  })

  it('keeps a fix of exactly 1 km precise', () => {
    render(<LocationReadout geo={{ status: 'found', lat: 51.8, lon: 19.3, accuracy: 1000 }} />)
    expect(screen.getByRole('status')).toHaveTextContent('Your location')
  })

  it('calls a fix worse than 1 km approximate and doesn’t imply precision', () => {
    render(
      <LocationReadout geo={{ status: 'found', lat: 51.80123, lon: 19.29408, accuracy: 4600 }} />,
    )
    expect(screen.getByRole('status')).toHaveTextContent('Approximate location')
    expect(card()).toHaveTextContent('51.80')
    expect(card()).not.toHaveTextContent('51.80123')
    expect(card()).toHaveTextContent('Within about 5 km')
  })

  it('says it in Polish too', async () => {
    await i18n.changeLanguage('pl')
    render(
      <LocationReadout geo={{ status: 'found', lat: 51.80123, lon: 19.29408, accuracy: 4600 }} />,
    )
    expect(screen.getByRole('status')).toHaveTextContent('Przybliżona lokalizacja')
    expect(screen.getByText('W promieniu ok. 5 km')).toBeInTheDocument()
  })
})
