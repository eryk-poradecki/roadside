import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  forbidOnly: true,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  globalTimeout: 60_000,
  use: {
    ...devices['iPhone 13'],
    defaultBrowserType: 'chromium',
    baseURL: 'http://localhost:18080',
    locale: 'en-GB',
    geolocation: { latitude: 52.23, longitude: 21.01 },
    permissions: ['geolocation'],
    serviceWorkers: 'block',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
})
