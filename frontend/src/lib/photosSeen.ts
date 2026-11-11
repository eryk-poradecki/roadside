import type { TurnInputsRead } from '../api/generated/types.gen'

export type PhotosSeen = { kind: 'none' | 'some'; seen: number; total: number }

/**
 * Whether the advice was given without some of the incident's photos: a provider that can't
 * see them, or the cap on photos per request (ADR 0002). Read from the inputs snapshot, which
 * the backend fills in, never the model. Null when nothing was left out.
 */
export function photosSeen(
  inputs: Pick<TurnInputsRead, 'photo_ids_seen' | 'photos_not_sent'>,
): PhotosSeen | null {
  const seen = inputs.photo_ids_seen.length
  if (inputs.photos_not_sent === 0) return null
  return { kind: seen === 0 ? 'none' : 'some', seen, total: seen + inputs.photos_not_sent }
}
