import { client } from './generated/client.gen'

/** The RFC 9457 problem the API sends for every error (ADR 0005). */
export interface Problem {
  status: number
  /** Stable snake_case code the UI switches on. */
  reason: string
  /** Server prose for logs and developers. Never shown to the driver. */
  detail: string | null
  errors: { field: string; message: string }[]
}

/** The one error every API call throws. */
export class ApiError extends Error {
  readonly problem: Problem

  constructor(problem: Problem) {
    super(problem.reason)
    this.name = 'ApiError'
    this.problem = problem
  }

  get reason(): string {
    return this.problem.reason
  }
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

function parseProblem(body: unknown, status: number): Problem {
  const record = isRecord(body) ? body : {}
  const errors = Array.isArray(record.errors)
    ? record.errors.filter(isRecord).map((e) => ({
        field: typeof e.field === 'string' ? e.field : '',
        message: typeof e.message === 'string' ? e.message : '',
      }))
    : []
  return {
    status,
    reason: typeof record.reason === 'string' ? record.reason : 'http_error',
    detail: typeof record.detail === 'string' ? record.detail : null,
    errors,
  }
}

/** Turn whatever the generated client caught into an ApiError. */
export function toApiError(error: unknown, response: Response | undefined): ApiError {
  if (error instanceof ApiError) return error
  // A fetch that fails without a response is a network failure.
  if (!response) return new ApiError({ status: 0, reason: 'offline', detail: null, errors: [] })
  return new ApiError(parseProblem(error, response.status))
}

/** `VITE_API_BASE_URL`: the API origin in dev, empty (same origin) in the compose build. */
const defaultBaseUrl = (): string => {
  const value: unknown = import.meta.env.VITE_API_BASE_URL
  return typeof value === 'string' ? value : ''
}

let configured = false

/** Point the generated client at the API and make it throw ApiError. Safe to call twice. */
export function configureApiClient(baseUrl: string = defaultBaseUrl()): void {
  client.setConfig({ baseUrl })
  if (configured) return
  configured = true
  client.interceptors.error.use((error, response) => toApiError(error, response))
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}
