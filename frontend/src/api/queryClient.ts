import { QueryClient } from '@tanstack/react-query'
import { isApiError } from './client'

const MAX_RETRIES = 2

/**
 * Retry only on network errors and 5xx, up to twice. Queries use it by default; mutations
 * don't retry, except an idempotent one that opts in (`POST /incidents`, ADR 0008).
 */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_RETRIES) return false
  if (!isApiError(error)) return false
  return error.problem.status === 0 || error.problem.status >= 500
}

/**
 * `networkMode: 'always'`: never pause while the browser says it's offline. A request runs,
 * fails without a response, and the driver sees the offline message and banner instead of a
 * spinner, and a write never waits to be replayed later (no queued writes, ADR 0008).
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetry, refetchOnWindowFocus: false, networkMode: 'always' },
      mutations: { retry: false, networkMode: 'always' },
    },
  })
}
