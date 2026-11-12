import { useCallback, useSyncExternalStore } from 'react'

/**
 * The one desktop breakpoint (ADR 0012), the same width as every `@media (min-width: 1024px)`
 * in the CSS. Below it, tablets included, the app is the mobile layout.
 */
export const DESKTOP_QUERY = '(min-width: 1024px)'

const media = (query: string): MediaQueryList | null =>
  typeof window.matchMedia === 'function' ? window.matchMedia(query) : null

/**
 * Whether a media query matches, kept live. Only for structure that CSS alone can't change
 * (ADR 0012: the desktop shell, the map beside the History list); layout otherwise stays in CSS. Without
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
