import { lazy, Suspense, type ComponentProps } from 'react'
import type { PlacesMap as EagerPlacesMap } from './PlacesMap'

const Loaded = lazy(() => import('./PlacesMap').then((m) => ({ default: m.PlacesMap })))

/**
 * The map, with Leaflet loaded on first use rather than with the app (#67): no first screen
 * shows a map, and the service worker precaches the chunk for offline use. Until it arrives
 * the box holds the map's place.
 */
export function PlacesMap(props: ComponentProps<typeof EagerPlacesMap>) {
  return (
    <Suspense fallback={<div className="places-map" aria-hidden="true" />}>
      <Loaded {...props} />
    </Suspense>
  )
}
