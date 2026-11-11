import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createIncidentMutation,
  deleteIncidentMutation,
  getIncidentOptions,
  getIncidentQueryKey,
  listIncidentsInfiniteOptions,
  updateIncidentMutation,
} from './generated/@tanstack/react-query.gen'
import type { IncidentCreate, IncidentPatch, IncidentStatus } from './generated/types.gen'
import { shouldRetry } from './queryClient'

export type {
  IncidentCreate,
  IncidentPatch,
  IncidentRead,
  IncidentStatus,
  IncidentSummary,
  LocationIn,
} from './generated/types.gen'

/** One History page. The API caps `limit` at 100. */
export const PAGE_SIZE = 20

export const useIncident = (id: number) =>
  useQuery({
    ...getIncidentOptions({ path: { incident_id: id } }),
    enabled: Number.isSafeInteger(id) && id > 0,
  })

/** History: newest first, a page at a time, optionally one status only. */
export function useIncidents(status: IncidentStatus | null) {
  return useInfiniteQuery({
    ...listIncidentsInfiniteOptions({
      query: { limit: PAGE_SIZE, ...(status ? { status } : {}) },
    }),
    initialPageParam: 0,
    getNextPageParam: (last) => {
      const next = last.offset + last.items.length
      return last.items.length > 0 && next < last.total ? next : undefined
    },
  })
}

/** Every History list, whatever its filter, is stale after any incident write. */
export function useInvalidateLists() {
  const queryClient = useQueryClient()
  // Partial key match: every list, whatever its filters or paging.
  return () => queryClient.invalidateQueries({ queryKey: [{ _id: 'listIncidents' }] })
}

/** "Get help now". The one mutation that retries (network errors and 5xx): the
 * `Idempotency-Key` makes a repeat return the incident the first attempt created (ADR 0005).
 * The caller keeps one key per help request, so a re-tap after a failure reuses it too.
 */
export function useCreateIncident() {
  const queryClient = useQueryClient()
  const invalidateLists = useInvalidateLists()
  const mutation = useMutation({
    ...createIncidentMutation(),
    retry: shouldRetry,
    // Never pause while the browser says it's offline: fail, show the offline message, and
    // let the driver tap again.
    networkMode: 'always',
    onSuccess: (incident) => {
      queryClient.setQueryData(
        getIncidentQueryKey({ path: { incident_id: incident.id } }),
        incident,
      )
      void invalidateLists()
    },
  })
  return {
    ...mutation,
    create: (body: IncidentCreate, idempotencyKey: string) =>
      mutation.mutateAsync({ body, headers: { 'Idempotency-Key': idempotencyKey } }),
  }
}

/** PATCH: status, note, problem type, location or vehicle. Only the sent fields change. */
export function useUpdateIncident(id: number) {
  const queryClient = useQueryClient()
  const invalidateLists = useInvalidateLists()
  const mutation = useMutation({
    ...updateIncidentMutation(),
    onSuccess: (incident) => {
      queryClient.setQueryData(getIncidentQueryKey({ path: { incident_id: id } }), incident)
    },
    onSettled: invalidateLists,
  })
  return {
    ...mutation,
    update: (body: IncidentPatch) => mutation.mutateAsync({ path: { incident_id: id }, body }),
  }
}

/**
 * Hard delete (ADR 0001). `leave` runs first (navigate away), then the detail entry is
 * dropped, so the screen still showing it doesn't refetch a 404 and nothing shows it later.
 */
export function useDeleteIncident(id: number) {
  const queryClient = useQueryClient()
  const invalidateLists = useInvalidateLists()
  const mutation = useMutation({ ...deleteIncidentMutation(), onSettled: invalidateLists })
  return {
    ...mutation,
    remove: async (leave: () => void) => {
      await mutation.mutateAsync({ path: { incident_id: id } })
      leave()
      queryClient.removeQueries({ queryKey: getIncidentQueryKey({ path: { incident_id: id } }) })
    },
  }
}
