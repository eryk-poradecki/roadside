import { screen, within } from '@testing-library/react'
import { delay, http, HttpResponse } from 'msw'
import { i18n } from '../src/i18n'
import { en } from '../src/i18n/en'
import { pl } from '../src/i18n/pl'
import { ADVICE, API, fakeApi } from './fakeApi'
import { renderApp } from './render'
import { server } from './setup'

const aiPanel = () => screen.getByRole('region', { name: 'Personalised steps' })
const checklist = () => screen.getByRole('region', { name: 'Do this first' })
const tyreItems = en.checklist.lists.tyre.items

async function getHelp(tile = 'Flat tyre', help = 'Get help now') {
  const { user } = renderApp('/')
  await user.click(await screen.findByRole('button', { name: tile }))
  const sheet = await screen.findByRole('dialog', { name: tile })
  await user.click(within(sheet).getByRole('button', { name: help }))
  await screen.findByRole('heading', { level: 1, name: tile })
  return { user }
}

describe('checklist folding (ADR 0010)', () => {
  it('shows the whole checklist while the assistant works', async () => {
    server.use(
      http.post(`${API}/api/v1/incidents/:id/ai-turns`, async () => {
        await delay('infinite')
        return HttpResponse.json({})
      }),
    )
    await getHelp()
    await within(aiPanel()).findByText(en.ai.loading)

    expect(within(checklist()).getByText(en.checklist.lists.tyre.first)).toBeVisible()
    for (const item of tyreItems) expect(within(checklist()).getByText(item)).toBeVisible()
    expect(within(checklist()).queryByRole('button')).not.toBeInTheDocument()
  })

  it('folds the rest under "N more safety steps" once the AI answers; the first step stays', async () => {
    const { user } = await getHelp()
    await within(aiPanel()).findByText(ADVICE.cause)

    expect(within(checklist()).getByText(en.checklist.lists.tyre.first)).toBeVisible()
    const toggle = within(checklist()).getByRole('button', { name: /4 more safety steps/ })
    expect(toggle).toHaveAttribute('aria-expanded', 'false')
    for (const item of tyreItems) expect(within(checklist()).getByText(item)).not.toBeVisible()

    await user.click(toggle)

    expect(toggle).toHaveAttribute('aria-expanded', 'true')
    for (const item of tyreItems) expect(within(checklist()).getByText(item)).toBeVisible()
    expect(within(checklist()).getByText(en.checklist.lists.tyre.first)).toBeVisible()

    await user.click(toggle)
    expect(within(checklist()).getByText(tyreItems[0] ?? '')).not.toBeVisible()
  })

  it('folds a stored answer when the incident is opened later, first step still shown', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre' })
    incident.ai_turns = [fakeApi.adviceTurn()]
    renderApp(`/incidents/${String(incident.id)}`)

    expect(await screen.findByText(en.checklist.lists.tyre.first)).toBeVisible()
    expect(
      within(checklist()).getByRole('button', { name: /4 more safety steps/ }),
    ).toHaveAttribute('aria-expanded', 'false')
  })

  it('stays expanded after a failed turn', async () => {
    fakeApi.turnScript = [{ status: 504, reason: 'timeout' }]
    await getHelp()
    await within(aiPanel()).findByRole('alert')

    for (const item of tyreItems) expect(within(checklist()).getByText(item)).toBeVisible()
    expect(within(checklist()).queryByRole('button')).not.toBeInTheDocument()
  })

  it('reads "Jeszcze 4 kroki bezpieczeństwa" in Polish', async () => {
    await i18n.changeLanguage('pl')
    await getHelp('Przebita opona', 'Potrzebuję pomocy')
    await screen.findByText(ADVICE.cause)

    expect(
      within(screen.getByRole('region', { name: pl.checklist.firstLabel })).getByRole('button', {
        name: /Jeszcze 4 kroki bezpieczeństwa/,
      }),
    ).toBeInTheDocument()
  })

  it.each([
    [1, 'Jeszcze 1 krok bezpieczeństwa'],
    [2, 'Jeszcze 2 kroki bezpieczeństwa'],
    [4, 'Jeszcze 4 kroki bezpieczeństwa'],
    [5, 'Jeszcze 5 kroków bezpieczeństwa'],
    [12, 'Jeszcze 12 kroków bezpieczeństwa'],
    [22, 'Jeszcze 22 kroki bezpieczeństwa'],
  ])('Polish plural %i → %s', (count, expected) => {
    expect(i18n.t('checklist.checklistSummary', { count, lng: 'pl' })).toBe(expected)
  })

  it('folds everything under "Safety steps" once resolved, even with an answer', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre' }, { status: 'resolved' })
    incident.ai_turns = [fakeApi.adviceTurn()]
    renderApp(`/incidents/${String(incident.id)}`)

    const summary = await screen.findByText('Safety steps')
    expect(summary.closest('details')).not.toHaveAttribute('open')
    expect(screen.queryByRole('button', { name: /more safety steps/ })).not.toBeInTheDocument()
  })
})

describe('urgent advice', () => {
  it('shows a banner and moves 112 to the primary dock slot, before "Call <insurer>"', async () => {
    fakeApi.seed({
      name: 'Golf',
      assistance_insurer: 'PZU Pomoc',
      assistance_phone: '+48 22 111 22 33',
    })
    fakeApi.turnScript = [{ advice: ADVICE, urgent: true }]
    await getHelp()
    await within(aiPanel()).findByText(ADVICE.cause)

    const banner = screen.getByRole('alert')
    expect(banner).toHaveTextContent(en.ai.urgentTitle)
    expect(banner).toHaveTextContent(en.ai.urgentBody)

    const sos = screen.getByRole('link', { name: 'Call emergency number 112' })
    expect(sos).toHaveTextContent(en.callEmergency)
    const insurer = screen.getByRole('link', { name: /Call PZU Pomoc/ })
    expect(sos.compareDocumentPosition(insurer) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('keeps the usual dock and no banner when the advice is not urgent', async () => {
    fakeApi.seed({
      name: 'Golf',
      assistance_insurer: 'PZU Pomoc',
      assistance_phone: '+48 22 111 22 33',
    })
    await getHelp()
    await within(aiPanel()).findByText(ADVICE.cause)

    expect(screen.queryByText(en.ai.urgentTitle)).not.toBeInTheDocument()
    const sos = screen.getByRole('link', { name: 'Call emergency number 112' })
    expect(sos).toHaveTextContent(/^112$/)
    const insurer = screen.getByRole('link', { name: /Call PZU Pomoc/ })
    expect(insurer.compareDocumentPosition(sos) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('without an assistance number, 112 still leads with the full label', async () => {
    fakeApi.turnScript = [{ advice: ADVICE, urgent: true }]
    await getHelp()
    await within(aiPanel()).findByText(ADVICE.cause)

    expect(screen.getByText(en.ai.urgentTitle)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Call emergency number 112' })).toHaveTextContent(
      en.callEmergency,
    )
  })
})

describe('"Answered for …"', () => {
  it('names the vehicle and problem type the advice was based on', async () => {
    fakeApi.seed({ name: 'Golf' })
    await getHelp()
    await within(aiPanel()).findByText(ADVICE.cause)

    expect(within(aiPanel()).getByText('Answered for Golf · Flat tyre')).toBeInTheDocument()
  })

  it('reflects the inputs snapshot, not the incident as edited later', async () => {
    fakeApi.seed({ name: 'Golf' })
    const leaf = fakeApi.seed({ name: 'Leaf', fuel_type: 'electric', is_default: false })
    const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre', vehicle_id: 1 })
    const snapshot = fakeApi.inputsFor(incident)
    // Later the driver changed the vehicle and the problem type.
    incident.vehicle_id = leaf.id
    incident.problem_type = 'out_of_fuel'
    incident.ai_turns = [fakeApi.adviceTurn(ADVICE, 'en', { inputs: snapshot })]
    renderApp(`/incidents/${String(incident.id)}`)

    await screen.findByRole('heading', { level: 1, name: 'Out of charge' })
    expect(within(aiPanel()).getByText('Answered for Golf · Flat tyre')).toBeInTheDocument()
  })

  it('says the advice was for a parked car, even after the situation is edited', async () => {
    fakeApi.seed({ name: 'Golf' })
    const incident = fakeApi.seedIncident({
      problem_type: 'flat_tyre',
      vehicle_id: 1,
      situation: 'parked',
    })
    const snapshot = fakeApi.inputsFor(incident)
    // Later the driver said the car is on the road after all.
    incident.situation = 'on_road'
    incident.ai_turns = [fakeApi.adviceTurn(ADVICE, 'en', { inputs: snapshot })]
    renderApp(`/incidents/${String(incident.id)}`)

    await screen.findByText(en.checklist.lists.tyre.first)
    expect(
      within(aiPanel()).getByText('Answered for Golf · Flat tyre (parked)'),
    ).toBeInTheDocument()
  })

  it('says the steps are general when the advice had no vehicle', async () => {
    await getHelp()
    await within(aiPanel()).findByText(ADVICE.cause)

    expect(
      within(aiPanel()).getByText(en.ai.answeredForNoVehicle.replace('{{problem}}', 'Flat tyre')),
    ).toBeInTheDocument()
  })
})

describe('an incident without an AI answer', () => {
  it('offers to finish it from the incident detail', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre' })
    const { user } = renderApp(`/incidents/${String(incident.id)}`)

    const panel = await screen.findByRole('region', { name: 'Personalised steps' })
    expect(within(panel).getByText(en.ai.notAnswered)).toBeInTheDocument()
    await user.click(within(panel).getByRole('button', { name: en.ai.ask }))

    expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
    expect(fakeApi.turnRequests).toHaveLength(1)
  })
})
