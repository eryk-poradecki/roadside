import type { VitePWAOptions } from 'vite-plugin-pwa'

/**
 * The PWA (ADR 0008): installable, and its app shell loads with no signal.
 *
 * - Precache the app shell only: the build's JS (with the bundled i18n resources), CSS, the
 *   font, the icons and index.html.
 * - No `runtimeCaching`: the service worker answers only precached URLs and navigations, so
 *   `/api/*` and the OSM tiles always go to the network (tiles keep the browser's HTTP cache).
 * - Navigations to the API or the health check never get the shell.
 * - `devOptions` stays off: the dev server, and the tests run against it, have no service
 *   worker; the registration script is injected into production builds only.
 */
export const pwaOptions: Partial<VitePWAOptions> = {
  strategies: 'generateSW',
  registerType: 'autoUpdate',
  injectRegister: 'script-defer',
  devOptions: { enabled: false },
  // The icons already match `globPatterns`; listing them twice would duplicate precache entries.
  includeManifestIcons: false,
  manifest: {
    name: 'Roadside',
    short_name: 'Roadside',
    description: 'Calm, step-by-step help when your car breaks down.',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    // --bg from src/styles/tokens.css.
    theme_color: '#0b0d11',
    background_color: '#0b0d11',
    icons: [
      { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
      { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
      {
        src: 'maskable-icon-512x512.png',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'maskable',
      },
    ],
  },
  workbox: {
    globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
    navigateFallback: 'index.html',
    navigateFallbackDenylist: [/^\/api\//, /^\/health$/],
    cleanupOutdatedCaches: true,
  },
}
