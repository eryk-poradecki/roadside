import { useCallback, useEffect, useState } from 'react'

export type GeoState =
  | { status: 'detecting' }
  | { status: 'found'; lat: number; lon: number; accuracy: number }
  | { status: 'denied' }
  | { status: 'unavailable' }

const PERMISSION_DENIED = 1
const OPTIONS: PositionOptions = { enableHighAccuracy: true, timeout: 15_000, maximumAge: 60_000 }

const supported = () => typeof navigator !== 'undefined' && 'geolocation' in navigator

/** The driver's position, detected on mount. A missing fix is a state, never an error. */
export function useGeolocation() {
  const [state, setState] = useState<GeoState>(() =>
    supported() ? { status: 'detecting' } : { status: 'unavailable' },
  )
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!supported()) return
    let active = true
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        if (active)
          setState({
            status: 'found',
            lat: coords.latitude,
            lon: coords.longitude,
            accuracy: coords.accuracy,
          })
      },
      (error) => {
        if (active)
          setState({ status: error.code === PERMISSION_DENIED ? 'denied' : 'unavailable' })
      },
      OPTIONS,
    )
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
