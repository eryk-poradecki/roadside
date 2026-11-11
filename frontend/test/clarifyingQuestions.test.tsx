import { screen, within } from '@testing-library/react'
import { i18n } from '../src/i18n'
import { ADVICE, fakeApi, QUESTION } from './fakeApi'
import { renderApp } from './render'

const PANEL = /^(Personalised steps|Kroki dopasowane do Ciebie)$/
const aiPanel = () => screen.getByRole('region', { name: PANEL })

async function getHelp(tile = 'Flat tyre', help = 'Get help now') {
  const { user } = renderApp('/')
  await user.click(await screen.findByRole('button', { name: tile }))
  const sheet = await screen.findByRole('dialog', { name: tile })
  await user.click(within(sheet).getByRole('button', { name: help }))
  await screen.findByRole('heading', { level: 1, name: tile })
  return { user }
}

/** The open question's options, found by the question. */
async function findQuestion(text = QUESTION.question) {
  const panel = await screen.findByRole('region', { name: PANEL })
  return within(panel).findByRole('group', { name: text })
}

describe('clarifying questions', () => {
  it('shows the "Right now" step, the options, Other and "Just give me the steps"', async () => {
    fakeApi.turnScript = [{ ask: QUESTION }]
    await getHelp()

    const options = await findQuestion()
    const panel = aiPanel()
    expect(within(panel).getByText('Right now')).toBeInTheDocument()
    expect(within(panel).getByText(QUESTION.now)).toBeInTheDocument()
    expect(within(panel).getByRole('heading', { name: QUESTION.question })).toBeInTheDocument()
    expect(
      within(options)
        .getAllByRole('button')
        .map((b) => b.textContent),
    ).toEqual(QUESTION.options)
    expect(within(panel).getByRole('textbox', { name: 'Or type a short answer' })).toHaveAttribute(
      'maxlength',
      '280',
    )
    expect(within(panel).getByRole('button', { name: 'Send answer' })).toBeDisabled()
    expect(within(panel).getByRole('button', { name: 'Just give me the steps' })).toBeEnabled()
    // Still no advice: the checklist stays unfolded.
    expect(screen.queryByRole('button', { name: /more safety steps/ })).not.toBeInTheDocument()
  })

  it('an ask turn → tapping an option → the advice, with the reply kept above it', async () => {
    fakeApi.turnScript = [{ ask: QUESTION }]
    const { user } = await getHelp()

    await user.click(within(await findQuestion()).getByRole('button', { name: 'No, off the road' }))

    expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
    expect(fakeApi.turnRequests.map((r) => r.body)).toEqual([
      { locale: 'en' },
      { locale: 'en', reply: { option: 'No, off the road' } },
    ])
    const answered = within(aiPanel()).getByRole('list', { name: 'Your answers' })
    expect(within(answered).getByRole('listitem')).toHaveTextContent(
      `${QUESTION.question}No, off the road`,
    )
    expect(within(aiPanel()).queryByText('Right now')).not.toBeInTheDocument()
  })

  it('replies with the driver\'s own short text ("Other")', async () => {
    fakeApi.turnScript = [{ ask: QUESTION }]
    const { user } = await getHelp()
    await findQuestion()

    const other = within(aiPanel()).getByRole('textbox', { name: 'Or type a short answer' })
    await user.type(other, '  In a car park  {Enter}')

    expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
    expect(fakeApi.turnRequests[1]?.body).toEqual({
      locale: 'en',
      reply: { text: 'In a car park' },
    })
  })

  it('"Just give me the steps" skips to the advice', async () => {
    fakeApi.turnScript = [{ ask: QUESTION }]
    const { user } = await getHelp()
    await findQuestion()

    await user.click(within(aiPanel()).getByRole('button', { name: 'Just give me the steps' }))

    expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
    expect(fakeApi.turnRequests[1]?.body).toEqual({ locale: 'en', reply: { skip: true } })
    const answered = within(aiPanel()).getByRole('list', { name: 'Your answers' })
    expect(answered).toHaveTextContent('Skipped to the steps')
  })

  it('asks a second question after the first reply', async () => {
    const second = { ...QUESTION, question: 'Which tyre is flat?', options: ['Front', 'Rear'] }
    fakeApi.turnScript = [{ ask: QUESTION }, { ask: second }]
    const { user } = await getHelp()

    await user.click(within(await findQuestion()).getByRole('button', { name: 'No, off the road' }))
    await user.click(
      within(await findQuestion(second.question)).getByRole('button', { name: 'Rear' }),
    )

    expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
    const answered = within(aiPanel()).getByRole('list', { name: 'Your answers' })
    expect(within(answered).getAllByRole('listitem')).toHaveLength(2)
  })

  it('reloading mid-conversation shows the open question again, without posting', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre' })
    incident.ai_turns = [fakeApi.questionTurn()]
    const { user } = renderApp({
      pathname: `/incidents/${String(incident.id)}`,
      state: { fromHelp: true },
    })

    const options = await findQuestion()
    expect(within(aiPanel()).getByText(QUESTION.now)).toBeInTheDocument()
    expect(fakeApi.turnRequests).toEqual([])

    await user.click(within(options).getByRole('button', { name: 'Yes, on the hard shoulder' }))

    expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
    expect(fakeApi.turnRequests).toHaveLength(1)
  })

  it('a reply followed by a failed turn keeps the reply; "Try again" asks without one', async () => {
    fakeApi.turnScript = [{ ask: QUESTION }, { status: 504, reason: 'timeout' }]
    const { user } = await getHelp()

    await user.click(within(await findQuestion()).getByRole('button', { name: 'No, off the road' }))

    const alert = await within(aiPanel()).findByRole('alert')
    const answered = await within(aiPanel()).findByRole('list', { name: 'Your answers' })
    expect(answered).toHaveTextContent('No, off the road')
    expect(within(aiPanel()).queryByRole('group')).not.toBeInTheDocument()

    await user.click(within(alert).getByRole('button', { name: 'Try again' }))

    expect(await within(aiPanel()).findByText(ADVICE.cause)).toBeInTheDocument()
    expect(fakeApi.turnRequests.map((r) => r.body)).toEqual([
      { locale: 'en' },
      { locale: 'en', reply: { option: 'No, off the road' } },
      { locale: 'en' },
    ])
  })

  it('reads in Polish', async () => {
    await i18n.changeLanguage('pl')
    fakeApi.turnScript = [{ ask: QUESTION }]
    await getHelp('Przebita opona', 'Potrzebuję pomocy')

    await findQuestion()
    expect(within(aiPanel()).getByText('Teraz')).toBeInTheDocument()
    expect(
      within(aiPanel()).getByRole('button', { name: 'Po prostu podaj kroki' }),
    ).toBeInTheDocument()
  })
})
