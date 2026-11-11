import { useSyncExternalStore } from 'react'

/**
 * Whether the app is cut off (ADR 0008): the browser says it's offline, or the newest API
 * request to settle got no response at all. Any response, even an error status, means the
 * server was reached and clears it, and so does the browser coming back online. The API
 * client feeds it; the offline banner reads it.
 */
let sent = 0
/** The newest request that got a response: an older request failing late is stale news. */
let lastAnswered = 0
let unreachable = false
const listeners = new Set<() => void>()

function setUnreachable(value: boolean) {
  if (unreachable === value) return
  unreachable = value
  for (const listener of listeners) listener()
}

/** A request is about to go out. Returns its sequence number. */
export function requestSent(): number {
  sent += 1
  return sent
}

/** A request got a response, whatever its status. */
export function requestAnswered(seq: number): void {
  lastAnswered = Math.max(lastAnswered, seq)
  setUnreachable(false)
}

/** A request failed without a response. */
export function requestFailed(seq: number): void {
  if (seq > lastAnswered) setUnreachable(true)
}

// Back online: the last failure is no longer news, and the next request will tell.
window.addEventListener('online', () => {
  setUnreachable(false)
})

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  window.addEventListener('online', listener)
  window.addEventListener('offline', listener)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('online', listener)
    window.removeEventListener('offline', listener)
  }
}

export const isOffline = (): boolean => unreachable || !navigator.onLine

export const useOffline = (): boolean => useSyncExternalStore(subscribe, isOffline)
