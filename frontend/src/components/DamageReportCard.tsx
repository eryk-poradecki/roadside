import { ChevronRight } from 'lucide-react'
import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router'
import type { IncidentRead } from '../api/incidents'
import { useUpdateIncident } from '../api/incidents'
import { useConfig } from '../api/config'
import {
  reportPath,
  StartReport,
  StatusBadge,
  useOfferedLocales,
  type DraftOnArrival,
} from './DamageReport'
import { ErrorNotice } from './ErrorNotice'

/**
 * The damage report's entry point on Incident detail (ADR 0009). With no report, a pothole
 * incident offers one: "Draft the report" opens the report screen, which drafts it. With a
 * report, only "Damage report · Draft|Sent · Open". A report kept after a type change still
 * shows; no other incident asks for one.
 */
export function DamageReportCard({ incident }: { incident: IncidentRead }) {
  const { t } = useTranslation()
  const titleId = useId()
  const navigate = useNavigate()
  const status = incident.damage_report_status
  const path = reportPath(incident.id)
  const offered = status === null && incident.problem_type === 'pothole_damage'
  const locales = useOfferedLocales(incident, offered)

  if (status !== null) {
    return (
      // The whole card opens the report, not just "Open".
      <section aria-labelledby={titleId}>
        <Link to={path} className="panel report-card">
          <h2 id={titleId}>{t('report.title')}</h2>
          <StatusBadge status={status} />
          <span className="report-card-open">
            {t('report.open')}
            <ChevronRight size={18} aria-hidden="true" />
          </span>
        </Link>
      </section>
    )
  }
  if (incident.problem_type !== 'pothole_damage') return null
  return (
    <section className="panel" aria-labelledby={titleId}>
      <h2 id={titleId}>{t('report.title')}</h2>
      <StartReport
        locales={locales}
        onDraft={(locale) => {
          const state: DraftOnArrival = { draftLocale: locale }
          void navigate(path, { state })
        }}
      />
    </section>
  )
}

/**
 * On a flat-tyre incident: "Was this caused by a pothole?" switches the problem type, after
 * which the damage report card offers the report (ADR 0009). Not in demo mode.
 */
export function PotholeHint({ incident }: { incident: IncidentRead }) {
  const { t } = useTranslation()
  const update = useUpdateIncident(incident.id)
  const config = useConfig()
  // Demo mode fixes the scenario (#131): a new problem type would drop its recorded places
  // and answers, and no report is recorded for it (#143).
  if (config.isPending || config.data?.demo_mode === true) return null
  return (
    <div className="notice report-hint">
      <p>
        <strong>{t('report.potholeHint')}</strong> {t('report.potholeHintSub')}
      </p>
      <button
        type="button"
        className="btn btn-quiet"
        disabled={update.isPending}
        onClick={() => {
          update.update({ problem_type: 'pothole_damage' }).catch(() => {
            // Shown below from `update.error`.
          })
        }}
      >
        {t('report.potholeSwitch')}
      </button>
      {update.isError && <ErrorNotice error={update.error} />}
    </div>
  )
}
