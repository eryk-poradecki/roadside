import { pwaOptions } from '../pwa.config'

// The service worker is generated at build time, so these pin the options it's built from
// (ADR 0008): shell precache only, the API and the map tiles never answered from a cache.
describe('PWA config', () => {
  const workbox = pwaOptions.workbox ?? {}

  it('has no runtime caching, so /api and the tiles stay network-only', () => {
    expect(workbox.runtimeCaching).toBeUndefined()
  })

  it.each(['/api/v1/incidents/1', '/api/v1/config', '/health'])(
    'never answers a navigation to %s with the app shell',
    (path) => {
      expect(workbox.navigateFallbackDenylist?.some((re) => re.test(path))).toBe(true)
    },
  )

  it.each(['/', '/incidents/12', '/vehicles/new'])('serves the app shell offline at %s', (path) => {
    expect(workbox.navigateFallback).toBe('index.html')
    expect(workbox.navigateFallbackDenylist?.some((re) => re.test(path))).toBe(false)
  })

  it('precaches only the built shell', () => {
    expect(workbox.globPatterns).toEqual(['**/*.{js,css,html,svg,png,woff2}'])
  })

  it('keeps the service worker out of the dev server', () => {
    expect(pwaOptions.devOptions?.enabled).toBe(false)
  })

  it('is installable: standalone, with 192 and 512 icons and a maskable one', () => {
    const manifest = pwaOptions.manifest || {}
    expect(manifest.display).toBe('standalone')
    const icons = manifest.icons ?? []
    expect(icons.map((i) => i.sizes)).toEqual(expect.arrayContaining(['192x192', '512x512']))
    expect(icons.some((i) => i.purpose === 'maskable')).toBe(true)
  })
})
