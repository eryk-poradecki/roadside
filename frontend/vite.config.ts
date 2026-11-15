import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { defineConfig } from 'vitest/config'
import { pwaOptions } from './pwa.config.ts'

export default defineConfig({
  plugins: [react(), VitePWA(pwaOptions)],
  build: {
    rolldownOptions: {
      output: {
        // React and the router change less often than the app: their own chunk stays cached
        // across releases and keeps the app chunk under the 500 kB warning (#67).
        codeSplitting: {
          groups: [
            {
              name: 'vendor-react',
              test: /node_modules[\\/](react|react-dom|scheduler|react-router)[\\/]/,
            },
          ],
        },
      },
    },
  },
  test: {
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./test/setup.ts'],
    css: false,
  },
})
