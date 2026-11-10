import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createIncidentMutation,
  getIncidentOptions,
  getIncidentQueryKey,
} from './generated/@tanstack/react-query.gen'
import type { IncidentCreate } from './generated/types.gen'
import { shouldRetry } from './queryClient'

export type { IncidentCreate, IncidentRead, LocationIn } from './generated/types.gen'

export const useIncident = (id: number) =>
  useQuery({
    ...getIncidentOptions({ path: { incident_id: id } }),
    enabled: Number.isSafeInteger(id) && id > 0,
  })

/**
 * "Get help now". The one mutation that retries (network errors and 5xx): the
 * `Idempotency-Key` makes a repeat return the incident the first attempt created (ADR 0005).
 * The caller keeps one key per help request, so a re-tap after a failure reuses it too.
 */
export function useCreateIncident() {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    ...createIncidentMutation(),
    retry: shouldRetry,
    onSuccess: (incident) => {
      queryClient.setQueryData(
        getIncidentQueryKey({ path: { incident_id: incident.id } }),
        incident,
      )
    },
  })
  return {
    ...mutation,
    create: (body: IncidentCreate, idempotencyKey: string) =>
      mutation.mutateAsync({ body, headers: { 'Idempotency-Key': idempotencyKey } }),
  }
}
