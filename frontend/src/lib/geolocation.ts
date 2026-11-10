import { useCallback, useEffect, useState } from 'react'

export type GeoState =
  | { status: 'detecting' }
  | { status: 'found'; lat: number; lon: number; accuracy: number }
  | { status: 'denied' }
  | { status: 'unavailable' }

const PERMISSION_DENIED = 1
const OPTIONS: PositionOptions = { enableHighAccuracy: true, timeout: 15_000, maximumAge: 60_000 }

const supported = () => typeof navigator !== 'undefined' && 'geolocation' in navigator

/** Ask the browser for one fix. Never rejects: a missing fix is a state, not an error. */
export function locateOnce(): Promise<Exclude<GeoState, { status: 'detecting' }>> {
  if (!supported()) return Promise.resolve({ status: 'unavailable' })
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        resolve({
          status: 'found',
          lat: coords.latitude,
          lon: coords.longitude,
          accuracy: coords.accuracy,
        })
      },
      (error) => {
        resolve({ status: error.code === PERMISSION_DENIED ? 'denied' : 'unavailable' })
      },
      OPTIONS,
    )
  })
}

/** The driver's position, detected on mount. A missing fix is a state, never an error. */
export function useGeolocation() {
  const [state, setState] = useState<GeoState>(() =>
    supported() ? { status: 'detecting' } : { status: 'unavailable' },
  )
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!supported()) return
    let active = true
    void locateOnce().then((next) => {
      if (active) setState(next)
    })
    return () => {
      active = false
    }
  }, [attempt])

  const retry = useCallback(() => {
    if (!supported()) return
    setState({ status: 'detecting' })
    setAttempt((n) => n + 1)
  }, [])

  return { state, retry, supported: supported() }
}
