import { useQuery } from '@tanstack/react-query'
import { readConfigOptions } from './generated/@tanstack/react-query.gen'

/** `GET /config` loads once at app start and never goes stale. */
export function useConfig() {
  return useQuery({ ...readConfigOptions(), staleTime: Infinity })
}
