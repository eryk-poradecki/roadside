import { QueryClient } from '@tanstack/react-query'
import { isApiError } from './client'

const MAX_RETRIES = 2

/** Queries retry only on network errors and 5xx, up to twice. Mutations never retry. */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_RETRIES) return false
  if (!isApiError(error)) return false
  return error.problem.status === 0 || error.problem.status >= 500
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetry, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  })
}
