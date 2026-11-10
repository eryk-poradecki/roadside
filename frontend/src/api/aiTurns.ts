import { useIsMutating, useMutation, useQueryClient } from '@tanstack/react-query'
import { isApiError } from './client'
import { getIncidentQueryKey, takeAiTurnMutation } from './generated/@tanstack/react-query.gen'
import type { AiTurnRead, IncidentRead } from './generated/types.gen'

export type { AdviceRead, AiTurnRead, Confidence, TurnInputsRead } from './generated/types.gen'

export type Locale = 'pl' | 'en'

const turnKey = (incidentId: number) => ['takeAiTurn', incidentId] as const

/** How long a turn already running elsewhere can take: the server's budget is under 100 s. */
const OTHER_TURN_MAX_MS = 100_000
const OTHER_TURN_POLL_MS = 5_000

/** Fallback when session storage is blocked: covers remounts, not reloads. */
const autoStarted = new Set<number>()

/** Whether `claimAutoStart` was already used for this incident, without claiming it. */
export function autoStartClaimed(incidentId: number): boolean {
  try {
    return sessionStorage.getItem(`ai-autostart-${String(incidentId)}`) !== null
  } catch {
    return autoStarted.has(incidentId)
  }
}

/**
 * True the first time it is called for an incident in this browser session, also across
 * remounts and reloads, so a failed turn is repeated only when the driver taps "Try again".
 */
export function claimAutoStart(incidentId: number): boolean {
  const key = `ai-autostart-${String(incidentId)}`
  try {
    if (sessionStorage.getItem(key) !== null) return false
    sessionStorage.setItem(key, '1')
    return true
  } catch {
    if (autoStarted.has(incidentId)) return false
    autoStarted.add(incidentId)
    return true
  }
}

/** The advice closes the AI answer, so an incident has at most one (ADR 0004). */
export const findAdvice = (incident: IncidentRead): AiTurnRead | undefined =>
  incident.ai_turns.find((turn) => turn.kind === 'advice' && turn.advice !== null)

/**
 * `POST /incidents/{id}/ai-turns`: one synchronous turn, held until the server has validated
 * and stored it or failed. Never retried on its own: a failed turn stores nothing and the
 * driver taps "Try again", which repeats the same request.
 */
export function useTakeAiTurn(incidentId: number) {
  const queryClient = useQueryClient()
  const incidentKey = getIncidentQueryKey({ path: { incident_id: incidentId } })
  const mutation = useMutation({
    ...takeAiTurnMutation(),
    mutationKey: turnKey(incidentId),
    networkMode: 'always',
    onSuccess: (turn) => {
      queryClient.setQueryData<IncidentRead>(incidentKey, (incident) =>
        incident && !incident.ai_turns.some((t) => t.id === turn.id)
          ? { ...incident, ai_turns: [...incident.ai_turns, turn] }
          : incident,
      )
    },
    onError: (error) => {
      if (!isApiError(error)) return
      // Another tab or an earlier request got there first: show what is stored.
      if (error.reason === 'advice_exists')
        void queryClient.invalidateQueries({ queryKey: incidentKey })
      // A turn started before a reload or in another tab is still running: pick up its
      // advice when it lands. The panel shows the advice over the error.
      if (error.reason === 'turn_in_progress') {
        const deadline = Date.now() + OTHER_TURN_MAX_MS
        const poll = () => {
          const incident = queryClient.getQueryData<IncidentRead>(incidentKey)
          if ((incident && findAdvice(incident)) || Date.now() > deadline) return
          void queryClient.invalidateQueries({ queryKey: incidentKey })
          setTimeout(poll, OTHER_TURN_POLL_MS)
        }
        setTimeout(poll, OTHER_TURN_POLL_MS)
      }
    },
  })
  return {
    ...mutation,
    take: (locale: Locale) =>
      mutation.mutateAsync({ path: { incident_id: incidentId }, body: { locale } }),
  }
}

/** A turn for this incident is in flight, from this screen or one left mid-request. */
export const useTurnInFlight = (incidentId: number) =>
  useIsMutating({ mutationKey: turnKey(incidentId) }) > 0
