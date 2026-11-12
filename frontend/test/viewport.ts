import { vi } from 'vitest'

/** Make `matchMedia` report a desktop-wide window (jsdom has none, which reads as mobile). */
export function asDesktop() {
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: query.includes('min-width'),
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }))
}
