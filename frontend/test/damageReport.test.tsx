import { screen, waitFor, within } from '@testing-library/react'
import { i18n } from '../src/i18n'
import { en } from '../src/i18n/en'
import { pl } from '../src/i18n/pl'
import { fakeApi, reportBody } from './fakeApi'
import { renderApp } from './render'

const panel = () => screen.getByRole('region', { name: en.report.title })
const letter = () => within(panel()).getByRole('textbox', { name: en.report.bodyLabel })

const JAN = {
  name: 'Jan Kowalski',
  address: 'ul. Długa 1, Warszawa',
  phone: '+48 600 100 200',
  bankAccount: 'PL61109010140000071219812874',
}

async function openPothole() {
  const incident = fakeApi.seedIncident({ problem_type: 'pothole_damage' })
  const rendered = renderApp(`/incidents/${String(incident.id)}`)
  await screen.findByRole('region', { name: en.report.title })
  return { ...rendered, incident }
}

async function draft(user: ReturnType<typeof renderApp>['user']) {
  await user.click(await within(panel()).findByRole('button', { name: en.report.draft }))
  return within(panel()).findByRole('textbox', { name: en.report.bodyLabel })
}

describe('damage report (ADR 0009)', () => {
  it('drafts a Polish letter by default with the assistant label and the addressee help', async () => {
    const { user, incident } = await openPothole()
    await waitFor(() => {
      expect(fakeApi.reportGets).toBe(1)
    })
    expect(await within(panel()).findByText(en.report.intro)).toBeInTheDocument()
    expect(within(panel()).getByRole('button', { name: 'Polish' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )

    const body = await draft(user)

    expect(fakeApi.reportRequests).toEqual([
      { method: 'POST', incidentId: incident.id, body: { locale: 'pl', replace: false } },
    ])
    expect(body).toHaveValue(reportBody('pl'))
    expect(within(panel()).getByText(en.report.label)).toBeInTheDocument()
    expect(within(panel()).getByText(en.report.status.draft)).toBeInTheDocument()
    expect(within(panel()).getByText(en.report.addressee.title)).toBeInTheDocument()
    for (const item of en.report.addressee.items)
      expect(within(panel()).getByText(item)).toBeInTheDocument()
    expect(within(panel()).getByRole('link', { name: en.report.addressee.lookup })).toHaveAttribute(
      'href',
      'https://www.gov.pl/web/gddkia/kto-jest-zarzadca-tej-drogi2',
    )
  })

  it('drafts in English when the driver picks it', async () => {
    const { user } = await openPothole()

    await user.click(await within(panel()).findByRole('button', { name: 'English' }))
    const body = await draft(user)

    expect(fakeApi.reportRequests[0]?.body).toEqual({ locale: 'en', replace: false })
    expect(body).toHaveValue(reportBody('en'))
  })

  it('shows the label and the help line in Polish too', async () => {
    await i18n.changeLanguage('pl')
    const incident = fakeApi.seedIncident({ problem_type: 'pothole_damage' })
    const { user } = renderApp(`/incidents/${String(incident.id)}`)
    const region = await screen.findByRole('region', { name: pl.report.title })

    await user.click(await within(region).findByRole('button', { name: pl.report.draft }))

    expect(await within(region).findByText(pl.report.label)).toBeInTheDocument()
    expect(within(region).getByText(pl.report.addressee.title)).toBeInTheDocument()
    for (const item of pl.report.addressee.items)
      expect(within(region).getByText(item)).toBeInTheDocument()
  })

  it('saves an edited letter and marks it sent, and back to draft', async () => {
    const { user, incident } = await openPothole()
    await draft(user)

    await user.clear(letter())
    await user.type(letter(), 'My own letter')
    await user.click(within(panel()).getByRole('button', { name: en.report.save }))
    await waitFor(() => {
      expect(fakeApi.reports.get(incident.id)?.body).toBe('My own letter')
    })
    await user.click(within(panel()).getByRole('button', { name: en.report.markSent }))

    expect(await within(panel()).findByText(en.report.status.sent)).toBeInTheDocument()
    expect(fakeApi.reportRequests.slice(1).map((r) => r.body)).toEqual([
      { body: 'My own letter' },
      { status: 'sent' },
    ])
    expect(letter()).toHaveValue('My own letter')

    await user.click(within(panel()).getByRole('button', { name: en.report.markDraft }))
    expect(await within(panel()).findByText(en.report.status.draft)).toBeInTheDocument()
  })

  it('fills the claimant details from the browser only when copying', async () => {
    const { user, incident } = await openPothole()
    await draft(user)

    await user.type(within(panel()).getByLabelText(en.report.details.name), JAN.name)
    await user.type(within(panel()).getByLabelText(en.report.details.address), JAN.address)
    await user.type(within(panel()).getByLabelText(en.report.details.phone), JAN.phone)
    await user.type(within(panel()).getByLabelText(en.report.details.bankAccount), JAN.bankAccount)
    await user.click(within(panel()).getByRole('button', { name: en.report.copy }))

    expect(await within(panel()).findByText(en.report.copied)).toBeInTheDocument()
    const copied = await navigator.clipboard.readText()
    expect(copied).toContain(`${JAN.name}\n${JAN.address}\nTel.: ${JAN.phone}`)
    expect(copied).toContain(`Rachunek: ${JAN.bankAccount}`)
    expect(copied).toContain('[Adresat: zarządca drogi]')
    expect(copied).not.toContain('[Imię i nazwisko]')
    // The stored letter keeps its placeholders, and no detail ever reached the server.
    expect(fakeApi.reports.get(incident.id)?.body).toBe(reportBody('pl'))
    expect(letter()).toHaveValue(reportBody('pl'))
    const sent = JSON.stringify([fakeApi.reportRequests, fakeApi.requests, fakeApi.turnRequests])
    for (const detail of Object.values(JAN)) expect(sent).not.toContain(detail)
    expect(localStorage.getItem('roadside.claimant')).toBeNull()
  })

  it('remembers the details on this device only when asked', async () => {
    const { user } = await openPothole()
    await draft(user)

    await user.click(within(panel()).getByLabelText(en.report.details.remember))
    await user.type(within(panel()).getByLabelText(en.report.details.name), JAN.name)

    expect(JSON.parse(localStorage.getItem('roadside.claimant') ?? '{}')).toMatchObject({
      name: JAN.name,
    })

    await user.click(within(panel()).getByLabelText(en.report.details.remember))
    expect(localStorage.getItem('roadside.claimant')).toBeNull()
  })

  it('drafts again only after a confirmation, back to draft', async () => {
    const { user, incident } = await openPothole()
    await draft(user)
    await user.click(within(panel()).getByRole('button', { name: en.report.markSent }))
    await within(panel()).findByText(en.report.status.sent)

    await user.click(within(panel()).getByRole('button', { name: en.report.regenerate }))
    expect(fakeApi.reportRequests).toHaveLength(2)
    const confirm = within(panel()).getByRole('group', { name: en.report.regenerate })
    expect(within(confirm).getByText(en.report.confirmRegenerate)).toBeInTheDocument()
    await user.click(within(confirm).getByRole('button', { name: 'English' }))
    await user.click(within(confirm).getByRole('button', { name: en.report.confirmRegenerateYes }))

    await waitFor(() => {
      expect(letter()).toHaveValue(reportBody('en'))
    })
    expect(fakeApi.reportRequests.at(-1)).toEqual({
      method: 'POST',
      incidentId: incident.id,
      body: { locale: 'en', replace: true },
    })
    expect(within(panel()).getByText(en.report.status.draft)).toBeInTheDocument()
  })

  it('shows the labelled demo-mode fallback when no draft is recorded', async () => {
    fakeApi.reportScript = [{ status: 503, reason: 'no_recording' }]
    const { user } = await openPothole()

    await user.click(await within(panel()).findByRole('button', { name: en.report.draft }))

    expect(await within(panel()).findByText(en.report.noRecordingTitle)).toBeInTheDocument()
    expect(within(panel()).getByText(en.report.noRecordingBody)).toBeInTheDocument()
    expect(within(panel()).queryByRole('textbox')).not.toBeInTheDocument()
  })

  it('says why a draft failed and stores nothing', async () => {
    fakeApi.reportScript = [{ status: 502, reason: 'provider_error' }]
    const { user, incident } = await openPothole()

    await user.click(await within(panel()).findByRole('button', { name: en.report.draft }))

    expect(await within(panel()).findByText(en.report.errorTitle)).toBeInTheDocument()
    expect(fakeApi.reports.has(incident.id)).toBe(false)
    // Trying again works.
    await draft(user)
    expect(fakeApi.reports.has(incident.id)).toBe(true)
  })

  it('offers no report for other problem types', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'flat_battery' })
    renderApp(`/incidents/${String(incident.id)}`)
    await screen.findByRole('heading', { level: 1, name: 'Flat battery' })

    expect(screen.queryByRole('region', { name: en.report.title })).not.toBeInTheDocument()
    expect(screen.queryByText(en.report.potholeHint)).not.toBeInTheDocument()
  })

  it('switches a flat tyre to pothole damage, then offers the report', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre' })
    const { user } = renderApp(`/incidents/${String(incident.id)}`)
    expect(await screen.findByText(en.report.potholeHint)).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: en.report.title })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: en.report.potholeSwitch }))

    expect(await screen.findByRole('region', { name: en.report.title })).toBeInTheDocument()
    expect(fakeApi.requests).toContainEqual({
      method: 'PATCH',
      body: { problem_type: 'pothole_damage' },
    })
    expect(screen.queryByText(en.report.potholeHint)).not.toBeInTheDocument()
    await draft(user)
    expect(fakeApi.reports.has(incident.id)).toBe(true)
  })

  it('shows a report the incident kept after its type changed', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'other' })
    fakeApi.reports.set(incident.id, {
      status: 'sent',
      locale: 'pl',
      body: reportBody('pl'),
      created_at: '2026-11-10T10:05:00.000Z',
      updated_at: '2026-11-10T10:05:00.000Z',
    })
    renderApp(`/incidents/${String(incident.id)}`)

    expect(await screen.findByRole('region', { name: en.report.title })).toBeInTheDocument()
    expect(await within(panel()).findByText(en.report.status.sent)).toBeInTheDocument()
    // Only a pothole incident can be drafted again.
    expect(
      within(panel()).queryByRole('button', { name: en.report.regenerate }),
    ).not.toBeInTheDocument()
  })

  it('marks sent the letter on screen, unsaved edits included', async () => {
    const { user, incident } = await openPothole()
    await draft(user)

    await user.type(letter(), ' Edited.')
    await user.click(within(panel()).getByRole('button', { name: en.report.markSent }))

    expect(await within(panel()).findByText(en.report.status.sent)).toBeInTheDocument()
    expect(fakeApi.reports.get(incident.id)?.body).toBe(`${reportBody('pl')} Edited.`)
    expect(within(panel()).queryByRole('button', { name: en.report.save })).not.toBeInTheDocument()
  })

  it('keeps unsaved edits when drafting again fails', async () => {
    const { user } = await openPothole()
    await draft(user)
    fakeApi.reportScript = [{ status: 502, reason: 'provider_error' }]

    await user.type(letter(), ' Edited.')
    await user.click(within(panel()).getByRole('button', { name: en.report.regenerate }))
    await user.click(within(panel()).getByRole('button', { name: en.report.confirmRegenerateYes }))

    expect(await within(panel()).findByText(en.report.errorTitle)).toBeInTheDocument()
    expect(letter()).toHaveValue(`${reportBody('pl')} Edited.`)

    // A later successful save clears the drafting error.
    await user.click(within(panel()).getByRole('button', { name: en.report.save }))
    await waitFor(() => {
      expect(within(panel()).queryByText(en.report.errorTitle)).not.toBeInTheDocument()
    })
  })

  it('asks for no report on an incident that cannot have one', async () => {
    const incident = fakeApi.seedIncident({ problem_type: 'out_of_fuel' })
    renderApp(`/incidents/${String(incident.id)}`)
    await screen.findByRole('heading', { level: 1 })
    await screen.findByRole('region', { name: en.ai.title })

    expect(fakeApi.reportGets).toBe(0)
  })

  it('shows the report status in History', async () => {
    const draftOne = fakeApi.seedIncident({ problem_type: 'pothole_damage' })
    const sentOne = fakeApi.seedIncident({ problem_type: 'pothole_damage' })
    fakeApi.seedIncident({ problem_type: 'flat_tyre' })
    const report = {
      locale: 'pl' as const,
      body: reportBody('pl'),
      created_at: '2026-11-10T10:05:00.000Z',
      updated_at: '2026-11-10T10:05:00.000Z',
    }
    fakeApi.reports.set(draftOne.id, { ...report, status: 'draft' })
    fakeApi.reports.set(sentOne.id, { ...report, status: 'sent' })
    renderApp('/incidents')

    const list = await screen.findByRole('list', { name: 'Your incidents' })
    expect(within(list).getByText(en.history.reportChip.draft)).toBeInTheDocument()
    expect(within(list).getByText(en.history.reportChip.sent)).toBeInTheDocument()
    expect(within(list).getAllByText(/^Report:/)).toHaveLength(2)
  })
})
