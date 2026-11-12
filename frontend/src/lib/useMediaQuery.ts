import { useCallback, useSyncExternalStore } from 'react'

/** The desktop breakpoint, the same width as the shell's `@media (min-width: 900px)`. */
export const DESKTOP_QUERY = '(min-width: 900px)'

const media = (query: string): MediaQueryList | null =>
  typeof window.matchMedia === 'function' ? window.matchMedia(query) : null

/**
 * Whether a media query matches, kept live. Only for structure that CSS alone can't change
 * (ADR 0008: the map beside the History list); layout otherwise stays in CSS. Without
 * `matchMedia` (jsdom) it reads false, the mobile layout.
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const list = media(query)
      list?.addEventListener('change', onChange)
      return () => {
        list?.removeEventListener('change', onChange)
      }
    },
    [query],
  )
  return useSyncExternalStore(subscribe, () => media(query)?.matches ?? false)
}

/** True on a desktop-wide window. */
export const useDesktop = () => useMediaQuery(DESKTOP_QUERY)
