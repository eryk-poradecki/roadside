import { screen, waitFor, within } from '@testing-library/react'
import { i18n } from '../src/i18n'
import type { ProblemType } from '../src/lib/problemType'
import type { PhotoRead } from '../src/api/photos'
import { en } from '../src/i18n/en'
import { pl } from '../src/i18n/pl'
import { fakeApi, reportBody } from './fakeApi'
import { renderApp } from './render'

/** The damage report card on Incident detail. */
const card = () => screen.getByRole('region', { name: en.report.title })
const letter = () => screen.getByRole('textbox', { name: en.report.bodyLabel })
/** The compact card is one link, named by its whole content: title, status and "Open". */
const openName = (status: 'draft' | 'sent') =>
  new RegExp(`${en.report.title}\\s*${en.report.status[status]}\\s*${en.report.open}`)
const fold = (summary: string) => {
  const details = screen.getByText(summary).closest('details')
  if (!details) throw new Error(`No fold "${summary}"`)
  return details
}

const JAN = {
  name: 'Jan Kowalski',
  address: 'ul. Długa 1, Warszawa',
  phone: '+48 600 100 200',
  bankAccount: 'PL61109010140000071219812874',
}

const STORED = {
  locale: 'pl' as const,
  body: reportBody('pl'),
  created_at: '2026-11-10T10:05:00.000Z',
  updated_at: '2026-11-10T10:05:00.000Z',
}

async function openPothole(options?: { strict?: boolean }) {
  const incident = fakeApi.seedIncident({ problem_type: 'pothole_damage' })
  const rendered = renderApp(`/incidents/${String(incident.id)}`, options)
  await screen.findByRole('region', { name: en.report.title })
  return { ...rendered, incident }
}

/** From Incident detail: "Draft the report" opens the report screen, which drafts. */
async function draft(user: ReturnType<typeof renderApp>['user']) {
  await user.click(await within(card()).findByRole('button', { name: en.report.draft }))
  return screen.findByRole('textbox', { name: en.report.bodyLabel })
}

/** Straight onto the report screen of an incident that already has a report. */
async function openReport(
  status: 'draft' | 'sent' = 'draft',
  problem: ProblemType = 'pothole_damage',
  photos: PhotoRead[] = [],
) {
  const incident = fakeApi.seedIncident({ problem_type: problem }, { photos })
  fakeApi.reports.set(incident.id, { ...STORED, status })
  const rendered = renderApp(`/incidents/${String(incident.id)}/report`)
  await screen.findByRole('textbox', { name: en.report.bodyLabel })
  return { ...rendered, incident }
}

describe('damage report (ADR 0009)', () => {
  describe('on Incident detail', () => {
    it('offers the report with a Polish letter by default and fetches nothing yet', async () => {
      await openPothole()

      expect(await within(card()).findByText(en.report.intro)).toBeInTheDocument()
      expect(within(card()).getByRole('button', { name: 'Polish' })).toHaveAttribute(
        'aria-pressed',
        'true',
      )
      expect(fakeApi.reportGets).toBe(0)
    })

    it('shows only a compact card once a report exists, and Open goes to the report', async () => {
      const incident = fakeApi.seedIncident({ problem_type: 'pothole_damage' })
      fakeApi.reports.set(incident.id, { ...STORED, status: 'sent' })
      const { user } = renderApp(`/incidents/${String(incident.id)}`)

      const region = await screen.findByRole('region', { name: en.report.title })
      expect(within(region).getByText(en.report.status.sent)).toBeInTheDocument()
      expect(within(card()).queryByRole('textbox')).not.toBeInTheDocument()
      expect(within(card()).queryByRole('button')).not.toBeInTheDocument()
      // The whole card is the link: a tap on its title opens the report.
      const open = within(card()).getByRole('link', { name: openName('sent') })
      expect(open).toHaveAttribute('href', `/incidents/${String(incident.id)}/report`)
      expect(open).toContainElement(within(card()).getByRole('heading', { name: en.report.title }))
      expect(open).toContainElement(within(card()).getByText(en.report.status.sent))

      await user.click(within(card()).getByRole('heading', { name: en.report.title }))
      expect(await screen.findByRole('textbox', { name: en.report.bodyLabel })).toHaveValue(
        reportBody('pl'),
      )
    })

    it('offers no report for other problem types', async () => {
      const incident = fakeApi.seedIncident({ problem_type: 'flat_battery' })
      renderApp(`/incidents/${String(incident.id)}`)
      await screen.findByRole('heading', { level: 1, name: 'Flat battery' })

      expect(screen.queryByRole('region', { name: en.report.title })).not.toBeInTheDocument()
      expect(screen.queryByText(en.report.potholeHint)).not.toBeInTheDocument()
      expect(fakeApi.reportGets).toBe(0)
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

    it('offers only the letter languages a draft is recorded in (#143)', async () => {
      fakeApi.reportLocales = ['en']
      const { user } = await openPothole()

      expect(within(card()).queryByRole('button', { name: 'Polish' })).not.toBeInTheDocument()
      await draft(user)

      expect(fakeApi.reportRequests[0]?.body).toEqual({ locale: 'en', replace: false })
    })

    it('says the report is not part of a demo scenario with none recorded (#143)', async () => {
      fakeApi.reportLocales = []
      await openPothole()

      expect(await within(card()).findByText(en.report.notInDemo)).toBeInTheDocument()
      expect(
        within(card()).queryByRole('button', { name: en.report.draft }),
      ).not.toBeInTheDocument()
      expect(within(card()).queryByRole('group')).not.toBeInTheDocument()
    })

    it('does not ask about a pothole in demo mode, where the scenario is fixed', async () => {
      fakeApi.config = { demo_mode: true, vision_enabled: false }
      const incident = fakeApi.seedIncident({ problem_type: 'flat_tyre' })
      renderApp(`/incidents/${String(incident.id)}`)

      await screen.findByRole('heading', { level: 1, name: 'Flat tyre' })
      await waitFor(() => {
        expect(screen.queryByText(en.report.potholeHint)).not.toBeInTheDocument()
      })
      expect(
        screen.queryByRole('button', { name: en.report.potholeSwitch }),
      ).not.toBeInTheDocument()
    })

    it('shows the card for a report the incident kept after its type changed', async () => {
      const incident = fakeApi.seedIncident({ problem_type: 'other' })
      fakeApi.reports.set(incident.id, { ...STORED, status: 'sent' })
      const { user } = renderApp(`/incidents/${String(incident.id)}`)

      const region = await screen.findByRole('region', { name: en.report.title })
      expect(within(region).getByText(en.report.status.sent)).toBeInTheDocument()
      await user.click(within(card()).getByRole('link', { name: openName('sent') }))

      await screen.findByRole('textbox', { name: en.report.bodyLabel })
      // Only a pothole incident can be drafted again.
      expect(screen.queryByRole('button', { name: en.report.regenerate })).not.toBeInTheDocument()
    })
  })

  describe('drafting', () => {
    it('opens the report screen, shows the drafting state there, then the letter', async () => {
      const { user, incident } = await openPothole({ strict: true })
      let release = () => {}
      fakeApi.reportGate = new Promise((resolve) => {
        release = resolve
      })

      await user.click(await within(card()).findByRole('button', { name: en.report.draft }))

      expect(await screen.findByText(en.report.drafting)).toBeInTheDocument()
      expect(screen.getByRole('heading', { level: 1, name: en.report.title })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: en.report.draft })).not.toBeInTheDocument()
      release()

      expect(await screen.findByRole('textbox', { name: en.report.bodyLabel })).toHaveValue(
        reportBody('pl'),
      )
      // Once, even with StrictMode running the arrival effect twice.
      expect(fakeApi.reportRequests).toEqual([
        { method: 'POST', incidentId: incident.id, body: { locale: 'pl', replace: false } },
      ])
    })

    it('drafts in the language picked on Incident detail', async () => {
      const { user } = await openPothole()

      await user.click(await within(card()).findByRole('button', { name: 'English' }))
      const body = await draft(user)

      expect(fakeApi.reportRequests[0]?.body).toEqual({ locale: 'en', replace: false })
      expect(body).toHaveValue(reportBody('en'))
    })

    it('does not draft again on a later visit, a Back or a reload', async () => {
      const { user, incident } = await openPothole()
      await draft(user)

      await user.click(screen.getByRole('link', { name: en.common.back }))
      await user.click(await within(card()).findByRole('link', { name: openName('draft') }))
      await screen.findByRole('textbox', { name: en.report.bodyLabel })

      expect(fakeApi.reportRequests).toHaveLength(1)
      expect(fakeApi.reports.get(incident.id)?.body).toBe(reportBody('pl'))
    })

    it('leaves the drafting state for good once the arrival draft is in', async () => {
      const { user } = await openPothole()
      await draft(user)

      await user.click(screen.getByRole('button', { name: en.report.markSent }))

      expect(await screen.findByText(en.report.status.sent)).toBeInTheDocument()
      expect(screen.queryByText(en.report.drafting)).not.toBeInTheDocument()
      expect(screen.getByRole('button', { name: en.report.markDraft })).toBeEnabled()
    })

    it('shows a report made meanwhile instead of drafting over it', async () => {
      const incident = fakeApi.seedIncident({ problem_type: 'pothole_damage' })
      fakeApi.reports.set(incident.id, { ...STORED, status: 'draft' })
      renderApp({
        pathname: `/incidents/${String(incident.id)}/report`,
        state: { draftLocale: 'en' },
      })

      expect(await screen.findByRole('textbox', { name: en.report.bodyLabel })).toHaveValue(
        reportBody('pl'),
      )
      expect(screen.queryByText(en.report.drafting)).not.toBeInTheDocument()
      expect(fakeApi.reportRequests).toHaveLength(0)
    })

    it('offers to draft on a direct link to a pothole incident with no report', async () => {
      const incident = fakeApi.seedIncident({ problem_type: 'pothole_damage' })
      const { user } = renderApp(`/incidents/${String(incident.id)}/report`)

      await user.click(await screen.findByRole('button', { name: en.report.draft }))

      expect(await screen.findByRole('textbox', { name: en.report.bodyLabel })).toBeInTheDocument()
      expect(fakeApi.reportRequests).toHaveLength(1)
    })

    it('says why a draft failed and lets the driver try again there', async () => {
      fakeApi.reportScript = [{ status: 502, reason: 'provider_error' }]
      const { user, incident } = await openPothole()

      await user.click(await within(card()).findByRole('button', { name: en.report.draft }))

      expect(await screen.findByText(en.report.errorTitle)).toBeInTheDocument()
      expect(fakeApi.reports.has(incident.id)).toBe(false)
      await user.click(screen.getByRole('button', { name: en.report.draft }))
      expect(await screen.findByRole('textbox', { name: en.report.bodyLabel })).toBeInTheDocument()
      expect(fakeApi.reports.has(incident.id)).toBe(true)
    })

    it('shows the labelled demo-mode fallback when no draft is recorded', async () => {
      fakeApi.reportScript = [{ status: 503, reason: 'no_recording' }]
      const { user } = await openPothole()

      await user.click(await within(card()).findByRole('button', { name: en.report.draft }))

      expect(await screen.findByText(en.report.noRecordingTitle)).toBeInTheDocument()
      expect(screen.getByText(en.report.noRecordingBody)).toBeInTheDocument()
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    })

    it('keeps the places found after a draft fails (#143)', async () => {
      fakeApi.reportScript = [{ status: 503, reason: 'no_recording' }]
      const incident = fakeApi.seedIncident({
        problem_type: 'pothole_damage',
        location: { lat: 52.2297, lon: 21.0122, accuracy_m: 12 },
      })
      const { user } = renderApp(`/incidents/${String(incident.id)}`)
      expect(await screen.findByText('Wulkanizacja Nowa')).toBeInTheDocument()

      await user.click(await within(card()).findByRole('button', { name: en.report.draft }))
      await screen.findByText(en.report.noRecordingTitle)
      await user.click(screen.getByRole('link', { name: en.common.back }))

      expect(await screen.findByText('Wulkanizacja Nowa')).toBeInTheDocument()
      expect(fakeApi.nearbyRequests).toHaveLength(1)
    })

    it('redirects a direct link for an incident that cannot have a report', async () => {
      const incident = fakeApi.seedIncident({ problem_type: 'flat_battery' })
      renderApp(`/incidents/${String(incident.id)}/report`)

      expect(
        await screen.findByRole('heading', { level: 1, name: 'Flat battery' }),
      ).toBeInTheDocument()
      expect(fakeApi.reportRequests).toHaveLength(0)
    })
  })

  describe('the report screen', () => {
    afterEach(() => {
      vi.restoreAllMocks()
      Reflect.deleteProperty(HTMLImageElement.prototype, 'decode')
    })

    it('keeps the print dialog closed if a photo fails, and lets the driver retry', async () => {
      const { user } = await openReport('draft', 'pothole_damage', [
        {
          id: 42,
          url: '/photos/42',
          content_type: 'image/jpeg',
          width: 1200,
          height: 900,
          created_at: STORED.created_at,
        },
      ])
      const decode = vi
        .fn()
        .mockRejectedValueOnce(new Error('Offline'))
        .mockResolvedValue(undefined)
      Object.defineProperty(HTMLImageElement.prototype, 'decode', {
        configurable: true,
        value: decode,
      })
      const print = vi.spyOn(window, 'print').mockImplementation(() => {})
      await user.click(screen.getByRole('button', { name: en.report.print }))
      expect(await screen.findByRole('alert')).toHaveTextContent(en.report.printFailed)
      expect(print).not.toHaveBeenCalled()
      await user.click(screen.getByRole('button', { name: en.report.print }))
      await waitFor(() => {
        expect(print).toHaveBeenCalledOnce()
      })
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })

    it('waits for full-size photos before printing them inline', async () => {
      const photo = {
        id: 42,
        url: '/photos/42',
        content_type: 'image/jpeg',
        width: 1200,
        height: 900,
        created_at: STORED.created_at,
      }
      const { user } = await openReport('draft', 'pothole_damage', [photo])
      let release = () => {}
      const decode = vi.fn(
        () =>
          new Promise<void>((resolve) => {
            release = resolve
          }),
      )
      Object.defineProperty(HTMLImageElement.prototype, 'decode', {
        configurable: true,
        value: decode,
      })
      const print = vi.spyOn(window, 'print').mockImplementation(() => {})
      await user.click(screen.getByRole('button', { name: 'Print / Save as PDF' }))
      expect(decode).toHaveBeenCalledOnce()
      expect(print).not.toHaveBeenCalled()
      const attachment = screen.getByRole('article', { hidden: true })
      expect(within(attachment).getByRole('img', { hidden: true })).toHaveAttribute(
        'src',
        'http://api.test/photos/42',
      )
      release()
      await waitFor(() => {
        expect(print).toHaveBeenCalledOnce()
      })
      print.mockRestore()
      Reflect.deleteProperty(HTMLImageElement.prototype, 'decode')
    })

    it('prints unsaved edits with browser-only details without saving the letter', async () => {
      const { user, incident } = await openReport()
      const print = vi.spyOn(window, 'print').mockImplementation(() => {})
      await user.type(letter(), ' Edited.')
      await user.type(screen.getByLabelText(en.report.details.name), JAN.name)
      await user.type(screen.getByLabelText(en.report.details.address), JAN.address)
      await user.type(screen.getByLabelText(en.report.details.phone), JAN.phone)
      await user.type(screen.getByLabelText(en.report.details.bankAccount), JAN.bankAccount)
      await user.click(screen.getByRole('button', { name: 'Print / Save as PDF' }))

      expect(print).toHaveBeenCalledOnce()
      const attachment = screen.getByRole('article', { hidden: true })
      expect(attachment.textContent).toContain(JAN.name)
      for (const value of Object.values(JAN)) expect(attachment.textContent).toContain(value)
      expect(attachment.textContent).toContain(' Edited.')
      expect(attachment.textContent).not.toContain('[Imię i nazwisko]')
      expect(letter()).toHaveValue(`${reportBody('pl')} Edited.`)
      expect(fakeApi.reports.get(incident.id)?.body).toBe(reportBody('pl'))
      expect(fakeApi.reportRequests).toHaveLength(0)
      expect(localStorage.getItem('roadside.claimant')).toBeNull()
      print.mockRestore()
    })

    it('shows label and status, letter, details, road manager help, then the actions', async () => {
      const { incident } = await openReport()

      const order = [
        screen.getByText(en.report.label),
        screen.getByText(en.report.status.draft),
        letter(),
        screen.getByText(en.report.details.title),
        screen.getByText(en.report.addressee.title),
        screen.getByRole('button', { name: en.report.copy }),
        screen.getByRole('button', { name: en.report.markSent }),
        screen.getByRole('button', { name: en.report.regenerate }),
      ]
      order.slice(1).forEach((next, i) => {
        expect(order[i]?.compareDocumentPosition(next)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
      })

      expect(screen.getByRole('link', { name: en.common.back })).toHaveAttribute(
        'href',
        `/incidents/${String(incident.id)}`,
      )
      // The 112 control stays, as on every screen.
      expect(screen.getByRole('link', { name: /112/ })).toBeInTheDocument()
    })

    it('ranks Copy first, Mark as sent second and Draft again last', async () => {
      await openReport()

      expect(screen.getByRole('button', { name: en.report.copy })).toHaveClass('btn-primary')
      expect(screen.getByRole('button', { name: en.report.markSent })).toHaveClass('btn-secondary')
      expect(screen.getByRole('button', { name: en.report.regenerate })).toHaveClass('link-btn')
    })

    it('opens "Your details" when nothing is saved on this device', async () => {
      await openReport()

      expect(fold(en.report.details.title)).toHaveAttribute('open')
      expect(fold(en.report.addressee.title)).not.toHaveAttribute('open')
    })

    it('keeps "Your details" folded when they are saved on this device', async () => {
      localStorage.setItem('roadside.claimant', JSON.stringify(JAN))
      await openReport()

      expect(fold(en.report.details.title)).not.toHaveAttribute('open')
      expect(fold(en.report.addressee.title)).not.toHaveAttribute('open')
      expect(screen.getByLabelText(en.report.details.name)).toHaveValue(JAN.name)
    })

    it('links to the road manager lookup', async () => {
      await openReport()

      for (const item of en.report.addressee.items)
        expect(screen.getByText(item)).toBeInTheDocument()
      expect(screen.getByRole('link', { name: en.report.addressee.lookup })).toHaveAttribute(
        'href',
        'https://www.gov.pl/web/gddkia/kto-jest-zarzadca-tej-drogi2',
      )
    })

    it('shows the label and the help in Polish too', async () => {
      await i18n.changeLanguage('pl')
      const incident = fakeApi.seedIncident({ problem_type: 'pothole_damage' })
      fakeApi.reports.set(incident.id, { ...STORED, status: 'draft' })
      renderApp(`/incidents/${String(incident.id)}/report`)

      expect(await screen.findByText(pl.report.label)).toBeInTheDocument()
      expect(screen.getByText(pl.report.addressee.title)).toBeInTheDocument()
      for (const item of pl.report.addressee.items)
        expect(screen.getByText(item)).toBeInTheDocument()
    })

    it('saves an edited letter and marks it sent, and back to draft', async () => {
      const { user, incident } = await openReport()

      await user.clear(letter())
      await user.type(letter(), 'My own letter')
      await user.click(screen.getByRole('button', { name: en.report.save }))
      await waitFor(() => {
        expect(fakeApi.reports.get(incident.id)?.body).toBe('My own letter')
      })
      await user.click(screen.getByRole('button', { name: en.report.markSent }))

      expect(await screen.findByText(en.report.status.sent)).toBeInTheDocument()
      expect(fakeApi.reportRequests.map((r) => r.body)).toEqual([
        { body: 'My own letter' },
        { status: 'sent' },
      ])
      expect(letter()).toHaveValue('My own letter')

      await user.click(screen.getByRole('button', { name: en.report.markDraft }))
      expect(await screen.findByText(en.report.status.draft)).toBeInTheDocument()
    })

    it('fills the claimant details from the browser only when copying', async () => {
      const { user, incident } = await openReport()

      await user.type(screen.getByLabelText(en.report.details.name), JAN.name)
      await user.type(screen.getByLabelText(en.report.details.address), JAN.address)
      await user.type(screen.getByLabelText(en.report.details.phone), JAN.phone)
      await user.type(screen.getByLabelText(en.report.details.bankAccount), JAN.bankAccount)
      await user.click(screen.getByRole('button', { name: en.report.copy }))

      expect(await screen.findByText(en.report.copied)).toBeInTheDocument()
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
      const { user } = await openReport()

      await user.click(screen.getByLabelText(en.report.details.remember))
      await user.type(screen.getByLabelText(en.report.details.name), JAN.name)

      expect(JSON.parse(localStorage.getItem('roadside.claimant') ?? '{}')).toMatchObject({
        name: JAN.name,
      })

      await user.click(screen.getByLabelText(en.report.details.remember))
      expect(localStorage.getItem('roadside.claimant')).toBeNull()
    })

    it('drafts again only in a recorded language, and not at all with none (#143)', async () => {
      fakeApi.reportLocales = ['pl']
      const { user } = await openReport()

      await user.click(await screen.findByRole('button', { name: en.report.regenerate }))
      const confirm = screen.getByRole('group', { name: en.report.regenerate })
      expect(within(confirm).queryByRole('button', { name: 'English' })).not.toBeInTheDocument()
      await user.click(
        within(confirm).getByRole('button', { name: en.report.confirmRegenerateYes }),
      )
      await waitFor(() => {
        expect(fakeApi.reportRequests[0]?.body).toEqual({ locale: 'pl', replace: true })
      })
    })

    it('offers no "Draft again" where demo mode recorded no draft (#143)', async () => {
      fakeApi.reportLocales = []
      await openReport()

      await waitFor(() => {
        expect(screen.queryByRole('button', { name: en.report.regenerate })).not.toBeInTheDocument()
      })
    })

    it('drafts again in place only after a confirmation, back to draft', async () => {
      const { user, incident } = await openReport('sent')

      await user.click(screen.getByRole('button', { name: en.report.regenerate }))
      expect(fakeApi.reportRequests).toHaveLength(0)
      const confirm = screen.getByRole('group', { name: en.report.regenerate })
      expect(within(confirm).getByText(en.report.confirmRegenerate)).toBeInTheDocument()
      await user.click(within(confirm).getByRole('button', { name: 'English' }))
      await user.click(
        within(confirm).getByRole('button', { name: en.report.confirmRegenerateYes }),
      )

      await waitFor(() => {
        expect(letter()).toHaveValue(reportBody('en'))
      })
      expect(fakeApi.reportRequests).toEqual([
        { method: 'POST', incidentId: incident.id, body: { locale: 'en', replace: true } },
      ])
      expect(screen.getByText(en.report.status.draft)).toBeInTheDocument()
    })

    it('marks sent the letter on screen, unsaved edits included', async () => {
      const { user, incident } = await openReport()

      await user.type(letter(), ' Edited.')
      await user.click(screen.getByRole('button', { name: en.report.markSent }))

      expect(await screen.findByText(en.report.status.sent)).toBeInTheDocument()
      expect(fakeApi.reports.get(incident.id)?.body).toBe(`${reportBody('pl')} Edited.`)
      expect(screen.queryByRole('button', { name: en.report.save })).not.toBeInTheDocument()
    })

    it('keeps unsaved edits when drafting again fails', async () => {
      const { user } = await openReport()
      fakeApi.reportScript = [{ status: 502, reason: 'provider_error' }]

      await user.type(letter(), ' Edited.')
      await user.click(screen.getByRole('button', { name: en.report.regenerate }))
      await user.click(screen.getByRole('button', { name: en.report.confirmRegenerateYes }))

      expect(await screen.findByText(en.report.errorTitle)).toBeInTheDocument()
      expect(letter()).toHaveValue(`${reportBody('pl')} Edited.`)

      // A later successful save clears the drafting error.
      await user.click(screen.getByRole('button', { name: en.report.save }))
      await waitFor(() => {
        expect(screen.queryByText(en.report.errorTitle)).not.toBeInTheDocument()
      })
    })
  })

  it('shows the report status in History', async () => {
    const draftOne = fakeApi.seedIncident({ problem_type: 'pothole_damage' })
    const sentOne = fakeApi.seedIncident({ problem_type: 'pothole_damage' })
    fakeApi.seedIncident({ problem_type: 'flat_tyre' })
    fakeApi.reports.set(draftOne.id, { ...STORED, status: 'draft' })
    fakeApi.reports.set(sentOne.id, { ...STORED, status: 'sent' })
    renderApp('/incidents')

    const list = await screen.findByRole('list', { name: 'Your incidents' })
    expect(within(list).getByText(en.history.reportChip.draft)).toBeInTheDocument()
    expect(within(list).getByText(en.history.reportChip.sent)).toBeInTheDocument()
    expect(within(list).getAllByText(/^Report:/)).toHaveLength(2)
  })
})
