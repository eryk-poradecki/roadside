import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { defineConfig } from 'vitest/config'
import { pwaOptions } from './pwa.config'

export default defineConfig({
  plugins: [react(), VitePWA(pwaOptions)],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./test/setup.ts'],
    css: false,
  },
})
