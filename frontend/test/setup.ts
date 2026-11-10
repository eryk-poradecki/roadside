import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest'
import { configureApiClient } from '../src/api/client'
import { i18n, initI18n } from '../src/i18n'
import { API, fakeApi } from './fakeApi'

export const server = setupServer(...fakeApi.handlers())

beforeAll(async () => {
  server.listen({ onUnhandledFrame: 'error' })
  configureApiClient(API)
  await initI18n()
})
beforeEach(async () => {
  localStorage.clear()
  await i18n.changeLanguage('en')
})
afterEach(() => {
  cleanup()
  server.resetHandlers()
  fakeApi.reset()
})
afterAll(() => {
  server.close()
})
