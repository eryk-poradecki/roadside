import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isApiError } from './client'
import { getDamageReport, getDamageReportLocales } from './generated/sdk.gen'
import {
  createDamageReportMutation,
  getDamageReportQueryKey,
  getIncidentQueryKey,
  updateDamageReportMutation,
} from './generated/@tanstack/react-query.gen'
import type { DamageReportPatch, DamageReportRead } from './generated/types.gen'
import type { Locale } from './aiTurns'
import { useInvalidateLists, type IncidentRead } from './incidents'

export type { DamageReportPatch, DamageReportRead, DamageReportStatus } from './generated/types.gen'

const reportKey = (incidentId: number) =>
  getDamageReportQueryKey({ path: { incident_id: incidentId } })

/** The incident's damage report, or null while it has none (the API answers 404). */
export const useDamageReport = (incidentId: number, enabled: boolean) =>
  useQuery({
    queryKey: reportKey(incidentId),
    enabled,
    queryFn: async ({ signal }): Promise<DamageReportRead | null> => {
      try {
        const { data } = await getDamageReport({
          path: { incident_id: incidentId },
          signal,
          throwOnError: true,
        })
        return data
      } catch (error) {
        if (isApiError(error) && error.reason === 'not_found') return null
        throw error
      }
    },
  })

/**
 * The letter languages a draft can be made in now, Polish first: both with a live model, in
 * demo mode only those recorded for the incident (#143). Asked again whenever the incident,
 * its photos or its answers change, since they pick the recording.
 */
export const useDamageReportLocales = (incident: IncidentRead | undefined, enabled: boolean) =>
  useQuery({
    queryKey: [
      'damageReportLocales',
      incident?.id,
      incident?.updated_at,
      incident?.photos.map((p) => p.id).join(','),
      incident?.ai_turns.length,
    ],
    enabled: enabled && incident !== undefined,
    queryFn: async ({ signal }): Promise<Locale[]> => {
      const { data } = await getDamageReportLocales({
        path: { incident_id: incident?.id ?? 0 },
        signal,
        throwOnError: true,
      })
      return data.locales
    },
  })

/** The incident's and History's report status follow every report write. */
function useRefreshAfterReportWrite(incidentId: number) {
  const queryClient = useQueryClient()
  const invalidateLists = useInvalidateLists()
  return () => {
    void queryClient.invalidateQueries({
      queryKey: getIncidentQueryKey({ path: { incident_id: incidentId } }),
    })
    void invalidateLists()
  }
}

/**
 * `POST /damage-report`: one synchronous model call, like an AI turn, never retried on its
 * own. `replace` overwrites the existing report after the driver confirmed it.
 */
export function useCreateDamageReport(incidentId: number) {
  const queryClient = useQueryClient()
  const refreshIncident = useRefreshAfterReportWrite(incidentId)
  const mutation = useMutation({
    ...createDamageReportMutation(),
    onSuccess: (report) => {
      queryClient.setQueryData(reportKey(incidentId), report)
      refreshIncident()
    },
  })
  return {
    ...mutation,
    generate: (locale: Locale, replace = false) =>
      mutation.mutateAsync({ path: { incident_id: incidentId }, body: { locale, replace } }),
  }
}

/** PATCH the body, or mark it sent (or back to draft). */
export function useUpdateDamageReport(incidentId: number) {
  const queryClient = useQueryClient()
  const refreshIncident = useRefreshAfterReportWrite(incidentId)
  const mutation = useMutation({
    ...updateDamageReportMutation(),
    onSuccess: (report) => {
      queryClient.setQueryData(reportKey(incidentId), report)
      refreshIncident()
    },
  })
  return {
    ...mutation,
    update: (body: DamageReportPatch) =>
      mutation.mutateAsync({ path: { incident_id: incidentId }, body }),
  }
}
