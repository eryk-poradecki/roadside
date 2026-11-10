import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { setupServer } from 'msw/node'
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest'
import { configureApiClient } from '../src/api/client'
import { i18n, initI18n } from '../src/i18n'
import { API, fakeApi } from './fakeApi'

// jsdom has no modal dialogs: open and close them like the browser would.
HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
  this.open = true
}
HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
  this.open = false
}

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
