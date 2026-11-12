import { vi } from 'vitest'

/**
 * Make `matchMedia` answer as a window `width` px wide would, for `(min-width: Npx)` queries
 * (jsdom has no `matchMedia`, which reads as mobile).
 */
export function atWidth(width: number) {
  vi.stubGlobal('matchMedia', (query: string) => {
    const min = /min-width:\s*(\d+)px/.exec(query)
    return {
      matches: min ? width >= Number(min[1]) : false,
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    }
  })
}

/** A desktop-wide window (ADR 0012: from 1024 px). */
export function asDesktop() {
  atWidth(1280)
}

/** A window that can be resized: `resize(px)` fires the media queries' change events. */
export function resizableViewport(width: number) {
  let current = width
  const listeners = new Set<() => void>()
  vi.stubGlobal('matchMedia', (query: string) => {
    const min = /min-width:\s*(\d+)px/.exec(query)
    return {
      get matches() {
        return min ? current >= Number(min[1]) : false
      },
      media: query,
      addEventListener: (_: string, fn: () => void) => listeners.add(fn),
      removeEventListener: (_: string, fn: () => void) => listeners.delete(fn),
    }
  })
  return {
    resize(px: number) {
      current = px
      listeners.forEach((fn) => {
        fn()
      })
    },
  }
}
