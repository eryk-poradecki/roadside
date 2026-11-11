import { notifyManager, useIsMutating, useMutation, useQueryClient } from '@tanstack/react-query'
import { isApiError } from './client'
import { getIncidentQueryKey, takeAiTurnMutation } from './generated/@tanstack/react-query.gen'
import type { AiTurnRead, IncidentRead, ReplyCreate, ReplyRead } from './generated/types.gen'

export type {
  AdviceRead,
  AiTurnRead,
  Confidence,
  QuestionRead,
  ReplyCreate,
  TurnInputsRead,
} from './generated/types.gen'

export type Locale = 'pl' | 'en'

const turnKey = (incidentId: number) => ['takeAiTurn', incidentId] as const

/** How long a turn already running elsewhere can take: the server's budget is under 100 s. */
const OTHER_TURN_MAX_MS = 100_000
const OTHER_TURN_POLL_MS = 5_000

/** Fallback when session storage is blocked: covers remounts, not reloads. */
const autoStarted = new Set<string>()

/**
 * The incident as this tab remembers it. SQLite reuses the id of a deleted newest incident,
 * and a wiped database starts again at 1, so the id alone could match an earlier incident.
 */
const autoStartKey = (incident: IncidentRead) =>
  `ai-autostart-${String(incident.id)}-${incident.created_at}`

/** Whether `claimAutoStart` was already used for this incident, without claiming it. */
export function autoStartClaimed(incident: IncidentRead): boolean {
  const key = autoStartKey(incident)
  try {
    return sessionStorage.getItem(key) !== null
  } catch {
    return autoStarted.has(key)
  }
}

/**
 * True the first time it is called for an incident in this browser session, also across
 * remounts and reloads, so a failed turn is repeated only when the driver taps "Try again".
 */
export function claimAutoStart(incident: IncidentRead): boolean {
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

/** The advice closes the AI answer, so an incident has at most one (ADR 0004). */
export const findAdvice = (incident: IncidentRead): AiTurnRead | undefined =>
  incident.ai_turns.find((turn) => turn.kind === 'advice' && turn.advice !== null)

/** The clarifying question waiting for the driver's reply: the last turn, when it is one. */
export const openQuestion = (incident: IncidentRead): AiTurnRead | undefined => {
  const last = incident.ai_turns.at(-1)
  return last?.kind === 'question' && last.question !== null ? last : undefined
}

/** A clarifying question already asked, with the driver's reply to it. */
export type QuestionWithReply = { id: number; question: string; reply: ReplyRead }

export const questionsWithReplies = (incident: IncidentRead): QuestionWithReply[] =>
  incident.ai_turns.flatMap((turn, i) => {
    const next = incident.ai_turns[i + 1]
    return turn.question && next?.reply
      ? [{ id: turn.id, question: turn.question.question, reply: next.reply }]
      : []
  })

/**
 * Resolves once react-query has delivered the updates already queued for its observers. The
 * screen then shows the refetched incident before the mutation settles, never the question
 * the reply was for next to the reply's own error or result.
 */
const afterQueuedUpdates = () =>
  new Promise<void>((resolve) => {
    notifyManager.schedule(resolve)
  })

/** A model turn (a question or the advice) stored after the first `seen` turns. */
const modelTurnSince = (incident: IncidentRead | undefined, seen: number) => {
  if (!incident) return false
  const last = incident.ai_turns.at(-1)
  return incident.ai_turns.length > seen && (last?.kind === 'question' || last?.kind === 'advice')
}

/**
 * `POST /incidents/{id}/ai-turns`: one synchronous turn, held until the server has validated
 * and stored it or failed. Never retried on its own: a failed turn stores nothing and the
 * driver taps "Try again", which posts `{locale}` only. A reply is stored before the turn and
 * stays when it fails, so after a request with a reply the incident is read again before the
 * mutation settles: the panel then shows the stored reply, not the question it replied to.
 */
export function useTakeAiTurn(incidentId: number) {
  const queryClient = useQueryClient()
  const incidentKey = getIncidentQueryKey({ path: { incident_id: incidentId } })
  const refetchIncident = async () => {
    await queryClient.invalidateQueries({ queryKey: incidentKey })
    await afterQueuedUpdates()
  }
  const mutation = useMutation({
    ...takeAiTurnMutation(),
    mutationKey: turnKey(incidentId),
    networkMode: 'always',
    onSuccess: (turn, variables) => {
      queryClient.setQueryData<IncidentRead>(incidentKey, (incident) =>
        incident && !incident.ai_turns.some((t) => t.id === turn.id)
          ? { ...incident, ai_turns: [...incident.ai_turns, turn] }
          : incident,
      )
      // The first turn also stores the location label (ADR 0004): refetch it for the
      // incident and History.
      void queryClient.invalidateQueries({ queryKey: [{ _id: 'listIncidents' }] })
      // With a reply, wait for it: the cache doesn't have the stored reply row yet.
      const refetch = refetchIncident()
      return variables.body.reply ? refetch : undefined
    },
    onError: (error, variables) => {
      const reason = isApiError(error) ? error.reason : undefined
      // A turn started before a reload or in another tab is still running: pick up its
      // question or advice when it lands. The panel shows it over the error.
      if (reason === 'turn_in_progress') {
        const seen = queryClient.getQueryData<IncidentRead>(incidentKey)?.ai_turns.length ?? 0
        const deadline = Date.now() + OTHER_TURN_MAX_MS
        const poll = () => {
          const incident = queryClient.getQueryData<IncidentRead>(incidentKey)
          if (modelTurnSince(incident, seen) || Date.now() > deadline) return
          void refetchIncident()
          setTimeout(poll, OTHER_TURN_POLL_MS)
        }
        setTimeout(poll, OTHER_TURN_POLL_MS)
      }
      // The reply may be stored although the turn failed, or another tab got there first:
      // show what the server has before the error does.
      const stale =
        reason === 'advice_exists' || reason === 'reply_required' || reason === 'no_open_question'
      if (variables.body.reply || stale) return refetchIncident()
    },
  })
  return {
    ...mutation,
    take: (locale: Locale, reply?: ReplyCreate) =>
      mutation.mutateAsync({
        path: { incident_id: incidentId },
        body: reply ? { locale, reply } : { locale },
      }),
  }
}

/** A turn for this incident is in flight, from this screen or one left mid-request. */
export const useTurnInFlight = (incidentId: number) =>
  useIsMutating({ mutationKey: turnKey(incidentId) }) > 0
