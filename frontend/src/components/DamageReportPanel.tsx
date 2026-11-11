import { Copy, ExternalLink, FileText, Info, Loader, RotateCw, Send, Sparkles } from 'lucide-react'
import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { Locale } from '../api/aiTurns'
import { isApiError } from '../api/client'
import {
  useCreateDamageReport,
  useDamageReport,
  useUpdateDamageReport,
  type DamageReportRead,
} from '../api/damageReports'
import type { IncidentRead } from '../api/incidents'
import { useUpdateIncident } from '../api/incidents'
import {
  EMPTY_CLAIMANT,
  fillClaimant,
  forgetClaimant,
  loadClaimant,
  rememberClaimant,
  type Claimant,
} from '../lib/claimant'
import { ErrorNotice, useErrorMessage } from './ErrorNotice'
import './DamageReportPanel.css'

/** GDDKiA's "Who manages this road?" page ([GD-WHO] in docs/copy/safety-checklist.md). */
const WHO_MANAGES_URL = 'https://www.gov.pl/web/gddkia/kto-jest-zarzadca-tej-drogi2'

const LOCALES: Locale[] = ['pl', 'en']

/**
 * The damage report on Incident detail (ADR 0009): a letter to the road manager the assistant
 * drafts from the incident, which the driver edits, copies with their own details and marks
 * sent. Created only for pothole damage; a report kept after a type change still shows.
 */
export function DamageReportPanel({ incident }: { incident: IncidentRead }) {
  const { t } = useTranslation()
  const titleId = useId()
  const pothole = incident.problem_type === 'pothole_damage'
  // A report kept after a type change still shows; no other incident asks for one.
  const shown = pothole || incident.damage_report_status !== null
  const report = useDamageReport(incident.id, shown)
  const create = useCreateDamageReport(incident.id)
  // Here, not in the editor, so a regenerated letter keeps the details typed for this visit.
  const [claimant, setClaimant] = useState<Claimant>(() => loadClaimant() ?? EMPTY_CLAIMANT)
  if (!shown) return null

  const generate = (locale: Locale, replace = false) => {
    create.generate(locale, replace).catch(() => {
      // Shown below from `create.error`.
    })
  }
  const data = report.data
  const busy = create.isPending

  return (
    <section className="panel panel-report" aria-labelledby={titleId} aria-busy={busy}>
      <div className="panel-head">
        <h2 id={titleId}>{t('report.title')}</h2>
        {data && (
          <span className={data.status === 'sent' ? 'badge' : 'badge badge-accent'}>
            {t(`report.status.${data.status}`)}
          </span>
        )}
      </div>

      {busy && (
        <div className="report-busy" role="status">
          <p className="ai-line">
            <Loader size={20} className="spin" aria-hidden="true" />
            {t('report.drafting')}
          </p>
          <p className="muted">{t('report.draftingSub')}</p>
        </div>
      )}
      {create.isError && <GenerateError error={create.error} />}
      {report.isPending ? (
        <p className="muted">{t('common.loading')}</p>
      ) : report.isError ? (
        <ErrorNotice error={report.error} />
      ) : data ? (
        // Stays mounted while a new draft is written: a failed one keeps unsaved edits.
        <ReportEditor
          incidentId={incident.id}
          report={data}
          busy={busy}
          // Only a pothole incident can be drafted again (ADR 0009).
          canRegenerate={pothole}
          claimant={claimant}
          onClaimantChange={setClaimant}
          onSaved={create.reset}
          onRegenerate={(locale) => {
            generate(locale, true)
          }}
        />
      ) : (
        !busy && (
          <StartReport
            onDraft={(locale) => {
              generate(locale)
            }}
          />
        )
      )}
    </section>
  )
}

function GenerateError({ error }: { error: unknown }) {
  const { t } = useTranslation()
  const message = useErrorMessage()
  // Demo mode with no recording for this case: labelled, never another case's draft.
  if (isApiError(error) && error.reason === 'no_recording') {
    return (
      <div className="ai-error" role="alert">
        <p className="ai-line">
          <Info size={20} aria-hidden="true" />
          <strong>{t('report.noRecordingTitle')}</strong>
        </p>
        <p className="muted">{t('report.noRecordingBody')}</p>
      </div>
    )
  }
  return (
    <div className="ai-error" role="alert">
      <p className="ai-line">
        <strong>{t('report.errorTitle')}</strong>
      </p>
      <p className="muted">
        {message(error)} {t('report.errorBody')}
      </p>
    </div>
  )
}

/** The letter's language: Polish by default, because it goes to a Polish road manager. */
function LanguagePick({ value, onChange }: { value: Locale; onChange: (l: Locale) => void }) {
  const { t } = useTranslation()
  return (
    <div className="report-language">
      <span className="muted">{t('report.languageLabel')}</span>
      <div className="segmented" role="group" aria-label={t('report.languageLabel')}>
        {LOCALES.map((locale) => (
          <button
            key={locale}
            type="button"
            aria-pressed={value === locale}
            onClick={() => {
              onChange(locale)
            }}
          >
            {t(`report.languages.${locale}`)}
          </button>
        ))}
      </div>
    </div>
  )
}

function StartReport({ onDraft }: { onDraft: (locale: Locale) => void }) {
  const { t } = useTranslation()
  const [locale, setLocale] = useState<Locale>('pl')
  return (
    <>
      <p className="muted">{t('report.intro')}</p>
      <LanguagePick value={locale} onChange={setLocale} />
      <button
        type="button"
        className="btn btn-quiet"
        onClick={() => {
          onDraft(locale)
        }}
      >
        <Sparkles size={18} aria-hidden="true" />
        {t('report.draft')}
      </button>
    </>
  )
}

function ReportEditor({
  incidentId,
  report,
  busy,
  canRegenerate,
  claimant,
  onClaimantChange,
  onSaved,
  onRegenerate,
}: {
  incidentId: number
  report: DamageReportRead
  /** A new draft is being written. */
  busy: boolean
  canRegenerate: boolean
  claimant: Claimant
  onClaimantChange: (c: Claimant) => void
  /** A save succeeded: an old drafting error no longer applies. */
  onSaved: () => void
  onRegenerate: (locale: Locale) => void
}) {
  const { t } = useTranslation()
  const bodyId = useId()
  const update = useUpdateDamageReport(incidentId)
  const [body, setBody] = useState(report.body)
  const [stored, setStored] = useState(report.body)
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle')
  const [confirming, setConfirming] = useState(false)
  const [locale, setLocale] = useState<Locale>(report.locale)
  // A new body from the server (saved, or drafted again) replaces the text being edited; a
  // status change alone keeps unsaved edits.
  if (report.body !== stored) {
    setStored(report.body)
    setBody(report.body)
    setConfirming(false)
    setLocale(report.locale)
  }
  // The server trims the body, so whitespace at the ends is not an edit.
  const dirty = body.trim() !== report.body
  const sent = report.status === 'sent'

  const save = (patch: Parameters<typeof update.update>[0]) => {
    update.update(patch).then(onSaved, () => {
      // Shown below from `update.error`.
    })
  }
  const copy = async () => {
    try {
      // The stored body keeps its placeholders: the details are filled in here only.
      await navigator.clipboard.writeText(fillClaimant(body, claimant))
      setCopyState('copied')
    } catch {
      setCopyState('failed')
    }
  }

  return (
    <>
      <p className="report-label">
        <Sparkles size={16} aria-hidden="true" />
        {t('report.label')}
      </p>

      <div className="report-field">
        <label htmlFor={bodyId}>{t('report.bodyLabel')}</label>
        <textarea
          id={bodyId}
          className="field report-body"
          rows={14}
          value={body}
          onChange={(e) => {
            setBody(e.target.value)
            setCopyState('idle')
          }}
        />
      </div>
      {dirty && (
        <button
          type="button"
          className="btn btn-quiet"
          disabled={busy || update.isPending || !body.trim()}
          onClick={() => {
            save({ body })
          }}
        >
          {t('report.save')}
        </button>
      )}

      <ClaimantForm claimant={claimant} onChange={onClaimantChange} />

      <AddresseeHelp />

      <div className="report-actions">
        <button type="button" className="btn btn-primary" onClick={() => void copy()}>
          <Copy size={20} aria-hidden="true" />
          {t('report.copy')}
        </button>
        <p className="report-copy-state" role="status">
          {copyState === 'copied'
            ? t('report.copied')
            : copyState === 'failed'
              ? t('report.copyFailed')
              : ''}
        </p>
        <button
          type="button"
          className="btn btn-quiet"
          disabled={busy || update.isPending || (dirty && !body.trim())}
          onClick={() => {
            // The letter marked sent is the one on screen, unsaved edits included.
            save({ status: sent ? 'draft' : 'sent', ...(dirty ? { body } : {}) })
          }}
        >
          {sent ? <FileText size={18} aria-hidden="true" /> : <Send size={18} aria-hidden="true" />}
          {sent ? t('report.markDraft') : t('report.markSent')}
        </button>
        {update.isError && <ErrorNotice error={update.error} />}

        {!canRegenerate ? null : confirming ? (
          <div className="report-confirm" role="group" aria-label={t('report.regenerate')}>
            <p>{t('report.confirmRegenerate')}</p>
            <LanguagePick value={locale} onChange={setLocale} />
            <div className="upkeep-row">
              <button
                type="button"
                className="btn btn-danger"
                disabled={busy}
                onClick={() => {
                  setConfirming(false)
                  onRegenerate(locale)
                }}
              >
                {t('report.confirmRegenerateYes')}
              </button>
              <button
                type="button"
                className="btn btn-quiet"
                onClick={() => {
                  setConfirming(false)
                }}
              >
                {t('common.cancel')}
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            className="btn btn-quiet"
            disabled={busy}
            onClick={() => {
              setConfirming(true)
            }}
          >
            <RotateCw size={18} aria-hidden="true" />
            {t('report.regenerate')}
          </button>
        )}
      </div>
    </>
  )
}

const CLAIMANT_FIELDS = [
  { field: 'name', autoComplete: 'name' },
  { field: 'address', autoComplete: 'street-address' },
  { field: 'phone', autoComplete: 'tel' },
  { field: 'bankAccount', autoComplete: 'off' },
] as const

/** "Your details": kept in this browser only, never sent to the server (ADR 0009). */
function ClaimantForm({
  claimant,
  onChange,
}: {
  claimant: Claimant
  onChange: (c: Claimant) => void
}) {
  const { t } = useTranslation()
  const id = useId()
  const [remember, setRemember] = useState(() => loadClaimant() !== null)

  const change = (next: Claimant) => {
    onChange(next)
    if (remember) rememberClaimant(next)
  }

  return (
    <fieldset className="report-details">
      <legend>{t('report.details.title')}</legend>
      <p className="muted">{t('report.details.hint')}</p>
      {CLAIMANT_FIELDS.map(({ field, autoComplete }) => (
        <div className="report-field" key={field}>
          <label htmlFor={`${id}-${field}`}>{t(`report.details.${field}`)}</label>
          <input
            id={`${id}-${field}`}
            className="field"
            autoComplete={autoComplete}
            value={claimant[field]}
            onChange={(e) => {
              change({ ...claimant, [field]: e.target.value })
            }}
          />
        </div>
      ))}
      <label className="report-remember">
        <input
          type="checkbox"
          checked={remember}
          onChange={(e) => {
            setRemember(e.target.checked)
            if (e.target.checked) rememberClaimant(claimant)
            else forgetClaimant()
          }}
        />
        {t('report.details.remember')}
      </label>
    </fieldset>
  )
}

/** Static copy, approved in docs/copy/safety-checklist.md: no guess at the road manager. */
function AddresseeHelp() {
  const { t } = useTranslation()
  const help = t('report.addressee', { returnObjects: true })
  return (
    <div className="report-addressee">
      <p>
        <strong>{help.title}</strong>
      </p>
      <ul>
        {help.items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <a href={WHO_MANAGES_URL} target="_blank" rel="noreferrer">
        {help.lookup}
        <ExternalLink size={14} aria-hidden="true" />
      </a>
    </div>
  )
}

/**
 * On a flat-tyre incident: "Was this caused by a pothole?" switches the problem type, after
 * which the damage report panel offers the report (ADR 0009).
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
