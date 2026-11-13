import { ArrowLeft, Loader } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, Navigate, useLocation, useNavigate, useParams } from 'react-router'
import type { Locale } from '../api/aiTurns'
import { useCreateDamageReport, useDamageReport } from '../api/damageReports'
import { useIncident } from '../api/incidents'
import {
  draftOnArrival,
  GenerateError,
  ReportEditor,
  StartReport,
  useOfferedLocales,
} from '../components/DamageReport'
import { ErrorNotice } from '../components/ErrorNotice'
import { EMPTY_CLAIMANT, loadClaimant, type Claimant } from '../lib/claimant'
import '../components/AiPanel.css'
import './IncidentScreen.css'

/**
 * `/incidents/:id/report`: the damage report (ADR 0009) on its own screen. Arriving from
 * "Draft the report" it drafts at once, in the language picked there; a direct link or a
 * reload with no report offers the same start controls.
 */
export function DamageReportScreen() {
  const { t } = useTranslation()
  const id = Number(useParams().id)
  const incident = useIncident(id)
  const location = useLocation()
  const navigate = useNavigate()
  // Read once: the router state is cleared on arrival, so a reload, Back or Forward never
  // drafts again.
  const [arrival] = useState(() => draftOnArrival(location.state))
  const claimed = useRef(false)
  const data = incident.data
  const pothole = data?.problem_type === 'pothole_damage'
  // A report kept after a type change still shows; no other incident can have one.
  const canHave = pothole || (data?.damage_report_status ?? null) !== null
  const report = useDamageReport(id, canHave)
  // For the start controls and "Draft again". The server offers none for an incident
  // that isn't a pothole, so a kept report's screen never waits on them.
  const locales = useOfferedLocales(data, canHave && report.isSuccess)
  const create = useCreateDamageReport(id)
  // Here, not in the editor, so a regenerated letter keeps the details typed for this visit.
  const [claimant, setClaimant] = useState<Claimant>(() => loadClaimant() ?? EMPTY_CLAIMANT)

  const generate = (locale: Locale, replace = false) =>
    create.generate(locale, replace).then(
      () => undefined,
      () => {
        // Shown below from `create.error`.
      },
    )

  // Once per arrival, when the incident and its report are known: the ref holds across
  // StrictMode's second effect run. A report made meanwhile (another tab) is just shown.
  useEffect(() => {
    if (arrival === null || claimed.current || !data || !canHave || report.isPending) return
    claimed.current = true
    void navigate(location.pathname, { replace: true, state: null })
    if (report.data) return
    void generate(arrival)
  })

  const incidentPath = `/incidents/${String(id)}`
  const back = (
    <Link to={incidentPath} className="back">
      <ArrowLeft size={20} aria-hidden="true" />
      {t('common.back')}
    </Link>
  )

  if (!data) {
    return (
      <>
        {back}
        {!incident.isEnabled ? (
          <p className="notice notice-error" role="alert">
            {t('errors.not_found')}
          </p>
        ) : incident.isError ? (
          <ErrorNotice error={incident.error} />
        ) : (
          <p className="muted">{t('common.loading')}</p>
        )}
      </>
    )
  }
  if (!canHave) return <Navigate to={incidentPath} replace />

  // From the first paint after "Draft the report" until that draft is under way. Only a
  // save resets the mutation to idle, and that needs a report, so this never comes back.
  const busy = create.isPending || (arrival !== null && create.isIdle && !report.data)

  return (
    <div className="result" aria-busy={busy}>
      {back}
      <h1>{t('report.title')}</h1>

      {busy && (
        <div className="panel report-busy" role="status">
          <p className="ai-line">
            <Loader size={20} className="spin" aria-hidden="true" />
            {t('report.drafting')}
          </p>
          <p className="muted">{t('report.draftingSub')}</p>
        </div>
      )}
      {create.isError && <GenerateError error={create.error} />}
      {report.isPending ? (
        !busy && <p className="muted">{t('common.loading')}</p>
      ) : report.isError ? (
        <ErrorNotice error={report.error} />
      ) : report.data ? (
        // Stays mounted while a new draft is written: a failed one keeps unsaved edits.
        <ReportEditor
          incidentId={id}
          report={report.data}
          photos={data.photos}
          busy={busy}
          // Only a pothole incident can be drafted again (ADR 0009).
          canRegenerate={pothole}
          locales={locales}
          claimant={claimant}
          onClaimantChange={setClaimant}
          onSaved={create.reset}
          onRegenerate={(locale) => {
            void generate(locale, true)
          }}
        />
      ) : (
        !busy && (
          <section className="panel">
            <StartReport
              locales={locales}
              onDraft={(locale) => {
                void generate(locale)
              }}
            />
          </section>
        )
      )}
    </div>
  )
}
