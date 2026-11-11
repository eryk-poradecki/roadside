import { render } from '@testing-library/react'
import type * as PlacesMapModule from '../src/components/map/PlacesMap'

// The other tests stand in for the map; these render the real Leaflet one.
const { PlacesMap } = await vi.importActual<typeof PlacesMapModule>(
  '../src/components/map/PlacesMap',
)

beforeAll(() => {
  // jsdom has no ResizeObserver.
  globalThis.ResizeObserver = class {
    observe() {
      // jsdom lays nothing out.
    }
    unobserve() {
      // jsdom lays nothing out.
    }
    disconnect() {
      // jsdom lays nothing out.
    }
  }
})

const props = {
  pins: [{ id: 'node/1', lat: 52.23, lon: 21.01 }],
  user: { lat: 52.2297, lon: 21.0122 },
  label: 'Map of nearby places',
  attribution: '© OpenStreetMap contributors',
}

describe('PlacesMap with real Leaflet', () => {
  it('renders the preview with its attribution', () => {
    const { container } = render(<PlacesMap {...props} interactive={false} />)
    expect(container.querySelector('.leaflet-control-attribution')).toHaveTextContent(
      props.attribution,
    )
  })

  it('renders the full map, whose attribution sits on the sheet instead', () => {
    const { container } = render(
      <PlacesMap {...props} showAttribution={false} onSelect={() => undefined} padBottom={300} />,
    )
    expect(container.querySelector('.leaflet-container')).not.toBeNull()
    expect(container.querySelector('.leaflet-control-attribution')).toBeNull()
  })

  it('opens on a chosen place, as when the driver taps one in the list', () => {
    const { container } = render(
      <PlacesMap {...props} selected="node/1" showAttribution={false} onSelect={() => undefined} />,
    )
    expect(container.querySelector('.pin-active')).toHaveTextContent('1')
  })
})
