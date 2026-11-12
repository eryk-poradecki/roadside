import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router'
import type { IncidentRead } from '../api/incidents'
import { useUpdateIncident } from '../api/incidents'
import { reportPath, StartReport, StatusBadge, type DraftOnArrival } from './DamageReport'
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

  if (status !== null) {
    return (
      <section className="panel report-card" aria-labelledby={titleId}>
        <h2 id={titleId}>{t('report.title')}</h2>
        <StatusBadge status={status} />
        <Link to={path} className="link-btn">
          {t('report.open')}
        </Link>
      </section>
    )
  }
  if (incident.problem_type !== 'pothole_damage') return null
  return (
    <section className="panel" aria-labelledby={titleId}>
      <h2 id={titleId}>{t('report.title')}</h2>
      <StartReport
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
 * which the damage report card offers the report (ADR 0009).
 */
export function PotholeHint({ incident }: { incident: IncidentRead }) {
  const { t } = useTranslation()
  const update = useUpdateIncident(incident.id)
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
