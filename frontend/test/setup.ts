import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { setupServer } from 'msw/node'
import { createElement } from 'react'
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest'
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
// Nor scrolling.
Element.prototype.scrollIntoView = function () {
  // jsdom lays nothing out.
}

// Leaflet needs a real layout engine (ADR 0008): the map module renders its labelled image
// and the pin ids in order, so tests can check what the map would show.
vi.mock('../src/components/map/PlacesMap', () => ({
  OSM_COPYRIGHT_URL: 'https://www.openstreetmap.org/copyright',
  PlacesMap: ({
    pins,
    label,
    attribution,
    showAttribution = true,
  }: {
    pins: { id: string }[]
    label: string
    attribution: string
    showAttribution?: boolean
  }) =>
    createElement(
      'div',
      { role: 'img', 'aria-label': label, 'data-pins': pins.map((p) => p.id).join(' ') },
      showAttribution ? attribution : null,
    ),
}))

export const server = setupServer(...fakeApi.handlers())

beforeAll(async () => {
  server.listen({ onUnhandledFrame: 'error' })
  configureApiClient(API)
  await initI18n()
})
beforeEach(async () => {
  localStorage.clear()
  sessionStorage.clear()
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
