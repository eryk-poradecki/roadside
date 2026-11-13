import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { setupServer } from 'msw/node'
import { createElement } from 'react'
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest'
import { configureApiClient } from '../src/api/client'
import { client } from '../src/api/generated/client.gen'
import { requestAnswered, requestSent } from '../src/api/offline'
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

// Leaflet needs a real layout engine (ADR 0008): the map module renders its labelled image,
// the pin ids in order and the selected one, so tests can check what the map would show. A
// selectable map also gets one "Pin <id>" button per pin, standing in for a click on it.
vi.mock('../src/components/map/PlacesMap', () => ({
  OSM_COPYRIGHT_URL: 'https://www.openstreetmap.org/copyright',
  PlacesMap: ({
    pins,
    label,
    attribution,
    showAttribution = true,
    selected = null,
    onSelect,
    interactive = true,
  }: {
    pins: { id: string }[]
    label: string
    attribution: string
    showAttribution?: boolean
    selected?: string | null
    onSelect?: (id: string) => void
    interactive?: boolean
  }) =>
    createElement(
      'div',
      {},
      createElement(
        'div',
        {
          role: 'img',
          'aria-label': label,
          'data-pins': pins.map((p) => p.id).join(' '),
          'data-selected': selected ?? '',
        },
        showAttribution ? attribution : null,
      ),
      interactive && onSelect
        ? pins.map((p) =>
            createElement(
              'button',
              {
                key: p.id,
                type: 'button',
                onClick: () => {
                  onSelect(p.id)
                },
              },
              `Pin ${p.id}`,
            ),
          )
        : null,
    ),
}))

export const server = setupServer(...fakeApi.handlers())

beforeAll(async () => {
  server.listen({ onUnhandledFrame: 'error' })
  configureApiClient(API)
  // msw can't intercept a streamed multipart body under Node's fetch (a photo upload): send
  // every body buffered instead. Browsers are unaffected; this is the test client only.
  client.setConfig({
    fetch: async (input: RequestInfo | URL, init?: RequestInit) => {
      if (!(input instanceof Request) || !input.body) return fetch(input, init)
      const { url, method, headers } = input
      try {
        return await fetch(
          new Request(url, { method, headers, body: await input.arrayBuffer() }),
          init,
        )
      } catch (error) {
        console.error('[DEBUG-ci-photo]', url, error)
        throw error
      }
    },
  })
  await initI18n()
})
beforeEach(async () => {
  localStorage.clear()
  sessionStorage.clear()
  await i18n.changeLanguage('en')
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  // The offline flag is module state: one test's lost network must not leak into the next.
  requestAnswered(requestSent())
  server.resetHandlers()
  fakeApi.reset()
})
afterAll(() => {
  server.close()
})
