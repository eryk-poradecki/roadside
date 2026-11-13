import { cleanup, screen, waitFor, within } from '@testing-library/react'
import { http } from 'msw'
import { i18n } from '../src/i18n'
import { en } from '../src/i18n/en'
import { ADVICE, API, fakeApi } from './fakeApi'
import { renderApp } from './render'
import { server } from './setup'

const aiPanel = () => screen.getByRole('region', { name: 'Personalised steps' })
const checklist = () => screen.getByRole('region', { name: 'Do this first' })

async function getHelp(tile = 'Flat tyre', strict = false) {
  const { user } = renderApp('/', { strict })
  await user.click(await screen.findByRole('button', { name: tile }))
  const sheet = await screen.findByRole('dialog', { name: tile })
  await user.click(within(sheet).getByRole('button', { name: 'Get help now' }))
  await screen.findByRole('heading', { level: 1, name: tile })
  return { user }
}

describe('AI answer on the Result screen', () => {
  it('asks the assistant once after "Get help now" and shows the advice, labelled as AI', async () => {
    await getHelp('Flat tyre', true)

    expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
    const panel = aiPanel()
    expect(within(panel).getByText('AI')).toBeInTheDocument()
    expect(within(panel).getByText('Most likely')).toBeInTheDocument()
    expect(
      within(panel).getByText('How sure the assistant is:', { exact: false }),
    ).toBeInTheDocument()
    expect(within(panel).getByText('A damaged valve')).toBeInTheDocument()

    const steps = within(panel).getByRole('heading', { name: 'What to do' }).nextElementSibling
    expect(steps?.tagName).toBe('OL')
    const items = within(steps as HTMLElement).getAllByRole('listitem')
    expect(items.map((li) => li.textContent)).toEqual(
      ADVICE.steps.map((s, i) => `${String(i + 1)}${s}`),
    )

    expect(
      within(panel).getByRole('heading', { name: 'Stop and call for help if' }),
    ).toBeInTheDocument()
    for (const condition of ADVICE.escalate_if)
      expect(within(panel).getByText(condition)).toBeInTheDocument()
    expect(within(panel).getByText(en.ai.disclaimer)).toBeInTheDocument()

    // StrictMode runs the effect twice; still one turn.
    expect(fakeApi.turnRequests).toEqual([{ incidentId: 1, body: { locale: 'en' } }])
  })

  it('asks in the UI language', async () => {
    await i18n.changeLanguage('pl')
    const { user } = renderApp('/')
    await user.click(await screen.findByRole('button', { name: 'Przebita opona' }))
    const sheet = await screen.findByRole('dialog', { name: 'Przebita opona' })
    await user.click(within(sheet).getByRole('button', { name: 'Potrzebuję pomocy' }))

    expect(await screen.findByText(ADVICE.cause)).toBeInTheDocument()
    expect(fakeApi.turnRequests[0]?.body).toEqual({ locale: 'pl' })
  })

  it('shows a waiting state while the assistant works, with the checklist already there', async () => {
    let finish!: () => void
    const response = new Promise<void>((resolve) => {
      finish = resolve
    })
    let arrived!: () => void
    const requestStarted = new Promise<void>((resolve) => {
      arrived = resolve
    })
    server.use(
      http.post(`${API}/api/v1/incidents/:id/ai-turns`, async () => {
        arrived()
        await response
        // Fall through to the fake API, which stores the answer before returning it.
      }),
    )
    await getHelp()

    try {
      await requestStarted
      expect(await within(aiPanel()).findByText(en.ai.loading)).toBeInTheDocument()
      await waitFor(() => expect(aiPanel()).toHaveAttribute('aria-busy', 'true'))
      expect(within(checklist()).getByText(en.checklist.lists.tyre.first)).toBeInTheDocument()
    } finally {
      // Finish this test's request before resetting the shared fake API for the next test.
      finish()
      await within(aiPanel()).findByText(ADVICE.cause)
    }
  })

  it('a timed-out turn shows a translated message and "Try again"; the checklist stays', async () => {
    fakeApi.turnScript = [{ status: 504, reason: 'timeout' }]
    const { user } = await getHelp()

    const alert = await within(aiPanel()).findByRole('alert')
    expect(within(alert).getByText("The assistant couldn't answer")).toBeInTheDocument()
    expect(alert).toHaveTextContent(en.errors.timeout)
    expect(alert).not.toHaveTextContent('internal detail')
    // The whole checklist is still shown, not folded.
    for (const item of en.checklist.lists.tyre.items)
      expect(within(checklist()).getByText(item)).toBeVisible()

    await user.click(within(alert).getByRole('button', { name: 'Try again' }))

    expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
    expect(within(aiPanel()).queryByRole('alert')).not.toBeInTheDocument()
    expect(fakeApi.turnRequests).toHaveLength(2)
    expect(fakeApi.turnRequests[1]?.body).toEqual({ locale: 'en' })
  })

  it.each([
    [502, 'provider_error'],
    [502, 'invalid_output'],
    [409, 'turn_in_progress'],
  ] as const)('a %i %s shows its own message', async (status, reason) => {
    fakeApi.turnScript = [{ status, reason }]
    await getHelp()

    const alert = await within(aiPanel()).findByRole('alert')
    expect(alert).toHaveTextContent(en.errors[reason])
    expect(within(alert).getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })

  it('a demo-mode key miss is labelled as demo mode, with no "Try again"; the checklist stays', async () => {
    fakeApi.turnScript = [{ status: 503, reason: 'no_recording' }]
    await getHelp()

    const alert = await within(aiPanel()).findByRole('alert')
    expect(within(alert).getByText(en.ai.noRecordingTitle)).toBeInTheDocument()
    expect(alert).not.toHaveTextContent("The assistant couldn't answer")
    expect(alert).not.toHaveTextContent('internal detail')
    expect(within(alert).queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
    for (const item of en.checklist.lists.tyre.items)
      expect(within(checklist()).getByText(item)).toBeVisible()
    expect(fakeApi.turnRequests).toHaveLength(1)
  })

  it('the demo-mode label is translated', async () => {
    await i18n.changeLanguage('pl')
    fakeApi.turnScript = [{ status: 503, reason: 'no_recording' }]
    const { user } = renderApp('/')
    await user.click(await screen.findByRole('button', { name: 'Przebita opona' }))
    const sheet = await screen.findByRole('dialog', { name: 'Przebita opona' })
    await user.click(within(sheet).getByRole('button', { name: 'Potrzebuję pomocy' }))

    expect(
      await screen.findByText('Brak nagranej odpowiedzi dla tego przypadku — tryb demo'),
    ).toBeInTheDocument()
  })

  it('an incident opened later does not ask on its own', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'flat_battery' })
    const { user } = renderApp(`/incidents/${String(incident.id)}`)

    const ask = await within(
      await screen.findByRole('region', { name: 'Personalised steps' }),
    ).findByRole('button', { name: 'Get steps from the assistant' })
    expect(fakeApi.turnRequests).toEqual([])

    await user.click(ask)

    expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
    expect(fakeApi.turnRequests).toHaveLength(1)
  })

  it('a stored advice is shown without asking again', async () => {
    const stored = { ...ADVICE, cause: 'A flat 12 V battery', confidence: 'possible' as const }
    const incident = fakeApi.seedIncident({ problem_type: 'flat_battery' })
    incident.ai_turns = [fakeApi.adviceTurn(stored)]

    renderApp(`/incidents/${String(incident.id)}`)

    expect(await screen.findByText('A flat 12 V battery')).toBeInTheDocument()
    expect(within(aiPanel()).getByText('Possibly')).toBeInTheDocument()
    expect(within(aiPanel()).queryByRole('button')).not.toBeInTheDocument()
    expect(fakeApi.turnRequests).toEqual([])
  })

  it('labels a stored answer in another language than the UI, and marks its language', async () => {
    await i18n.changeLanguage('pl')
    const incident = fakeApi.seedIncident({ problem_type: 'flat_battery' })
    incident.ai_turns = [fakeApi.adviceTurn(ADVICE, 'en')]

    renderApp(`/incidents/${String(incident.id)}`)

    const panel = await screen.findByRole('region', { name: 'Kroki dopasowane do Ciebie' })
    expect(await within(panel).findByText('Odpowiedź po angielsku')).toBeInTheDocument()
    expect(within(panel).getByText(ADVICE.cause).closest('[lang]')).toHaveAttribute('lang', 'en')
  })

  it('adds no language label when the answer is in the UI language', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'flat_battery' })
    incident.ai_turns = [fakeApi.adviceTurn(ADVICE, 'en')]

    renderApp(`/incidents/${String(incident.id)}`)

    const panel = await screen.findByRole('region', { name: 'Personalised steps' })
    expect(await within(panel).findByText(ADVICE.cause)).toBeInTheDocument()
    expect(within(panel).queryByText('Answer in English')).not.toBeInTheDocument()
    expect(within(panel).queryByText('Answer in Polish')).not.toBeInTheDocument()
  })

  it('does not post again on its own after a failed turn and a remount', async () => {
    fakeApi.turnScript = [{ status: 504, reason: 'timeout' }]
    await getHelp()
    await within(aiPanel()).findByRole('alert')

    // Come back to the same history entry (Back/forward, or a reload): same state.
    cleanup()
    renderApp({ pathname: '/incidents/1', state: { fromHelp: true } })
    await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })

    expect(
      await within(aiPanel()).findByRole('button', { name: 'Get steps from the assistant' }),
    ).toBeInTheDocument()
    expect(fakeApi.turnRequests).toHaveLength(1)
  })

  it('still asks on its own when a reused incident id was asked for before in this tab', async () => {
    // An earlier incident 1, deleted (or its database wiped) while the tab stayed open:
    // SQLite gives the next incident the same id.
    const earlier = fakeApi.seedIncident(
      { problem_type: 'flat_tyre' },
      { created_at: '2026-11-09T08:00:00.000Z' },
    )
    renderApp({ pathname: '/incidents/1', state: { fromHelp: true } })
    expect(
      await within(await screen.findByRole('region', { name: 'Personalised steps' })).findByText(
        ADVICE.cause,
      ),
    ).toBeInTheDocument()
    cleanup()
    fakeApi.reset()
    expect(earlier.id).toBe(1)

    await getHelp()

    expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
    expect(fakeApi.turnRequests).toEqual([{ incidentId: 1, body: { locale: 'en' } }])
  })

  it('a turn still running elsewhere (409) shows its advice once it is stored', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    try {
      fakeApi.turnScript = [{ status: 409, reason: 'turn_in_progress' }]
      const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre' })
      const { user } = renderApp(`/incidents/${String(incident.id)}`)
      await screen.findByRole('region', { name: 'Personalised steps' })
      await user.click(
        await within(aiPanel()).findByRole('button', { name: 'Get steps from the assistant' }),
      )
      expect(await within(aiPanel()).findByRole('alert')).toHaveTextContent(
        en.errors.turn_in_progress,
      )

      // The other request stores the advice; the next poll picks it up.
      fakeApi.incidents = fakeApi.incidents.map((i) =>
        i.id === incident.id ? { ...i, ai_turns: [fakeApi.adviceTurn()] } : i,
      )
      await vi.advanceTimersByTimeAsync(5_000)

      expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
      expect(fakeApi.turnRequests).toHaveLength(1)
    } finally {
      vi.useRealTimers()
    }
  })
})
