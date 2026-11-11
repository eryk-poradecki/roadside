import { useIsMutating, useMutation, useQueryClient } from '@tanstack/react-query'
import { isApiError } from './client'
import { findNearbyMutation, getIncidentQueryKey } from './generated/@tanstack/react-query.gen'
import type { IncidentRead } from './generated/types.gen'

export type { NearbyCategory, NearbyRead, PlaceRead } from './generated/types.gen'

/** 5 km first; the driver can ask for 25 km (ADR 0005). */
export const FIRST_RADIUS_KM = 5
export const WIDE_RADIUS_KM = 25

const nearbyKey = (incidentId: number) => ['findNearby', incidentId] as const

/** Fallback when session storage is blocked: covers remounts, not reloads. */
const autoStarted = new Set<string>()

/**
 * The incident and the point as this tab remembers them: a new location (a PATCH clears the
 * snapshot) looks up again, and a reused id of a deleted incident doesn't match.
 */
const autoStartKey = (incident: IncidentRead) => {
  const loc = incident.location
  return `nearby-autostart-${String(incident.id)}-${incident.created_at}-${String(loc?.lat)},${String(loc?.lon)}`
}

/**
 * True the first time for this incident and location in this browser session, so a failed
 * lookup is repeated only when the driver taps "Try again".
 */
export function claimNearbyAutoStart(incident: IncidentRead): boolean {
  const key = autoStartKey(incident)
  try {
    if (sessionStorage.getItem(key) !== null) return false
    sessionStorage.setItem(key, '1')
    return true
  } catch {
    if (autoStarted.has(key)) return false
    autoStarted.add(key)
    return true
  }
}

export function nearbyAutoStartClaimed(incident: IncidentRead): boolean {
  const key = autoStartKey(incident)
  try {
    return sessionStorage.getItem(key) !== null
  } catch {
    return autoStarted.has(key)
  }
}

/**
 * `POST /incidents/{id}/nearby`: the server asks OpenStreetMap and stores the result on the
 * incident. Never retried on its own (a lookup can take most of a minute); a failure keeps
 * the previous places and the driver taps "Try again".
 */
export function useFindNearby(incidentId: number) {
  const queryClient = useQueryClient()
  const incidentKey = getIncidentQueryKey({ path: { incident_id: incidentId } })
  const mutation = useMutation({
    ...findNearbyMutation(),
    mutationKey: nearbyKey(incidentId),
    networkMode: 'always',
    onSuccess: (nearby) => {
      queryClient.setQueryData<IncidentRead>(incidentKey, (incident) =>
        incident ? { ...incident, nearby } : incident,
      )
    },
    onError: (error) => {
      // The location was removed or moved meanwhile: show what the server has now.
      const reason = isApiError(error) ? error.reason : undefined
      if (reason === 'no_location' || reason === 'location_changed')
        return queryClient.invalidateQueries({ queryKey: incidentKey })
    },
  })
  return {
    ...mutation,
    find: (radiusKm: number) =>
      mutation.mutateAsync({ path: { incident_id: incidentId }, body: { radius_km: radiusKm } }),
  }
}

export const useNearbyInFlight = (incidentId: number) =>
  useIsMutating({ mutationKey: nearbyKey(incidentId) }) > 0
