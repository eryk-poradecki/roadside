import { screen, waitFor, within } from '@testing-library/react'
import { delay, http, HttpResponse } from 'msw'
import type { DemoScenario } from '../src/api/generated'
import { en } from '../src/i18n/en'
import { API, fakeApi, problem, SAMPLES } from './fakeApi'
import { renderApp } from './render'
import { server } from './setup'
import { asDesktop } from './viewport'

const scenario: DemoScenario = {
  id: 'tyre_parked_morning',
  problem_type: 'flat_tyre',
  vehicle_profile: 'golf_2017',
  situation: 'parked',
  sample_photo_ids: ['flat_tyre'],
  location: { lat: 52.4085, lon: 16.91, accuracy_m: 10 },
  locales: {
    en: {
      title: 'Flat tyre before work',
      summary: 'A parked Golf before work.',
      note: 'The front-left tyre is flat.',
    },
    pl: {
      title: 'Przebita opona przed pracą',
      summary: 'Golf stoi pod blokiem.',
      note: 'Lewe przednie koło jest całkiem flakiem.',
    },
  },
}

function demoConfig(scenarios = [scenario], publicDeploy = false) {
  server.use(
    http.get(`${API}/api/v1/config`, () =>
      HttpResponse.json({
        demo_mode: true,
        public_deploy: publicDeploy,
        demo_scenarios: scenarios,
        vision_enabled: true,
        max_photos: 5,
        max_photo_bytes: 1000,
        sample_photos: SAMPLES,
      }),
    ),
  )
}

const geo = vi.fn()
beforeEach(() => {
  geo.mockClear()
  Object.defineProperty(navigator, 'geolocation', {
    configurable: true,
    value: { getCurrentPosition: geo },
  })
})
afterEach(() => {
  Reflect.deleteProperty(navigator, 'geolocation')
})

it.each([false, true])(
  'shows a locked scenario and sends its exact request (desktop: %s)',
  async (desktop) => {
    if (desktop) asDesktop()
    const golf = fakeApi.seed({ name: 'Golf' })
    golf.demo_profile = 'golf_2017'
    fakeApi.seed({ name: 'Default car', is_default: true })
    demoConfig()
    const { user } = renderApp('/')
    await user.click(await screen.findByRole('button', { name: /Flat tyre before work/ }))
    const sheet = screen.getByRole('dialog')
    expect(within(sheet).getByLabelText('Anything we should know?')).toHaveValue(
      'The front-left tyre is flat.',
    )
    expect(within(sheet).getByLabelText('Anything we should know?')).toHaveAttribute('readonly')
    expect(within(sheet).getByRole('radio', { name: 'Golf' })).toBeChecked()
    expect(within(sheet).getByRole('radio', { name: /Parked/ })).toBeChecked()
    for (const radio of within(sheet).getAllByRole('radio')) expect(radio).toBeDisabled()
    expect(within(sheet).getByRole('img', { name: 'Photo 1' })).toBeInTheDocument()
    expect(within(sheet).queryByRole('button', { name: /Remove photo/ })).not.toBeInTheDocument()
    expect(within(sheet).queryByLabelText('Add photos')).not.toBeInTheDocument()
    expect(within(sheet).queryByRole('button', { name: 'Flat front tyre' })).not.toBeInTheDocument()
    expect(screen.queryByText(en.demo.publicNotice)).not.toBeInTheDocument()
    await user.click(within(sheet).getByRole('button', { name: 'Get help now' }))
    await waitFor(() => {
      expect(fakeApi.incidentRequests).toHaveLength(1)
    })
    expect(fakeApi.incidentRequests[0]?.body).toEqual({
      problem_type: 'flat_tyre',
      vehicle_id: golf.id,
      note: 'The front-left tyre is flat.',
      situation: 'parked',
      location: scenario.location,
    })
    await waitFor(() => {
      expect(fakeApi.photoRequests).toEqual([{ incidentId: 1, sampleId: 'flat_tyre' }])
    })
    expect(geo).not.toHaveBeenCalled()
  },
)

it('filters the list by locale, changes scenarios and uses No vehicle', async () => {
  demoConfig(
    [
      scenario,
      {
        ...scenario,
        id: 'no_vehicle',
        vehicle_profile: null,
        locales: {
          en: { title: 'No car details', summary: 'Unknown vehicle.', note: 'Unknown car.' },
        },
      },
    ],
    true,
  )
  const { user } = renderApp('/')
  expect(await screen.findByText(en.demo.publicNotice)).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: /No car details/ }))
  expect(
    within(screen.getByRole('dialog')).getByRole('radio', { name: 'No vehicle' }),
  ).toBeChecked()
  await user.click(screen.getByRole('button', { name: 'Change scenario' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Polski' }))
  expect(
    await screen.findByRole('button', { name: /Przebita opona przed pracą/ }),
  ).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /No car details/ })).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: /Przebita opona przed pracą/ }))
  expect(screen.getByRole('textbox')).toHaveValue('Lewe przednie koło jest całkiem flakiem.')
  expect(geo).not.toHaveBeenCalled()
})

it('shows the empty state in a locale without recordings', async () => {
  demoConfig([
    { ...scenario, locales: { pl: { title: 'Przebita opona', summary: 'Golf.', note: 'Opona.' } } },
  ])
  renderApp('/')
  expect(await screen.findByText(en.demo.noScenarios)).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Flat tyre' })).not.toBeInTheDocument()
  expect(geo).not.toHaveBeenCalled()
})

it('does not locate while config loads or fails, and lets the driver retry config', async () => {
  server.use(
    http.get(`${API}/api/v1/config`, async () => {
      await delay(30)
      return problem(503, 'database_unavailable', 'No config')
    }),
  )
  const { user } = renderApp('/')
  expect(screen.getByText('Loading…')).toHaveTextContent('Loading…')
  expect(await screen.findByRole('alert')).toBeInTheDocument()
  expect(geo).not.toHaveBeenCalled()
  demoConfig([])
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText(en.demo.noScenarios)).toBeInTheDocument()
  expect(geo).not.toHaveBeenCalled()
})

it('blocks scenario selection after a vehicle load failure and lets the driver retry', async () => {
  demoConfig()
  server.use(
    http.get(`${API}/api/v1/vehicles`, () => problem(503, 'database_unavailable', 'No vehicles')),
  )
  const { user } = renderApp('/')
  expect(await screen.findByRole('alert')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /Flat tyre before work/ })).toBeDisabled()
  server.use(http.get(`${API}/api/v1/vehicles`, () => HttpResponse.json([])))
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  await waitFor(() =>
    expect(screen.getByRole('button', { name: /Flat tyre before work/ })).toBeEnabled(),
  )
  await user.click(screen.getByRole('button', { name: /Flat tyre before work/ }))
  expect(screen.getByRole('radio', { name: 'No vehicle' })).toBeChecked()
})
