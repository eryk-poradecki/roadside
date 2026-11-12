import { Copy, ExternalLink, FileText, Info, Printer, RotateCw, Send, Sparkles } from 'lucide-react'
import { useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from 'react-i18next'
import type { Locale } from '../api/aiTurns'
import { isApiError } from '../api/client'
import { useUpdateDamageReport, type DamageReportRead } from '../api/damageReports'
import { photoSrc, type PhotoRead } from '../api/photos'
import {
  fillClaimant,
  forgetClaimant,
  loadClaimant,
  rememberClaimant,
  type Claimant,
} from '../lib/claimant'
import { ErrorNotice, useErrorMessage } from './ErrorNotice'
import { Fold } from './Fold'
import './DamageReport.css'

/**
 * The pieces of the damage report (ADR 0009) shared by its card on Incident detail and its
 * own screen, `/incidents/:id/report`.
 */

/** GDDKiA's "Who manages this road?" page ([GD-WHO] in docs/copy/safety-checklist.md). */
const WHO_MANAGES_URL = 'https://www.gov.pl/web/gddkia/kto-jest-zarzadca-tej-drogi2'

const LOCALES: Locale[] = ['pl', 'en']

export const reportPath = (incidentId: number) => `/incidents/${String(incidentId)}/report`

/** Router state from "Draft the report": the report screen drafts in this language on arrival. */
export interface DraftOnArrival {
  draftLocale: Locale
}

export function draftOnArrival(state: unknown): Locale | null {
  if (typeof state !== 'object' || state === null || !('draftLocale' in state)) return null
  const locale = (state as DraftOnArrival).draftLocale
  return LOCALES.includes(locale) ? locale : null
}

export function GenerateError({ error }: { error: unknown }) {
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

/** What the report is, the letter's language and "Draft the report". */
export function StartReport({ onDraft }: { onDraft: (locale: Locale) => void }) {
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

export function StatusBadge({ status }: { status: DamageReportRead['status'] }) {
  const { t } = useTranslation()
  return (
    <span className={status === 'sent' ? 'badge' : 'badge badge-accent'}>
      {t(`report.status.${status}`)}
    </span>
  )
}

/**
 * The report itself: the assistant label and status, the editable letter, "Your details",
 * "Who manages this road?" and the actions, Copy first.
 */
export function ReportEditor({
  incidentId,
  report,
  photos,
  busy,
  canRegenerate,
  claimant,
  onClaimantChange,
  onSaved,
  onRegenerate,
}: {
  incidentId: number
  report: DamageReportRead
  photos: PhotoRead[]
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
  const printView = useRef<HTMLElement>(null)
  const [printState, setPrintState] = useState<'idle' | 'loading' | 'failed'>('idle')
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
  const print = async () => {
    setPrintState('loading')
    try {
      // Eager images also support the browser's own Print command. The button waits for
      // decoding so a slow connection cannot silently produce an attachment without photos.
      await Promise.all(
        Array.from(printView.current?.querySelectorAll('img') ?? []).map((img) => {
          // A failed image does not retry its request just because decode is called again.
          if (printState === 'failed') img.setAttribute('src', img.src)
          return img.decode()
        }),
      )
      window.print()
      setPrintState('idle')
    } catch {
      setPrintState('failed')
    }
  }

  return (
    <>
      <div className="panel report-letter">
        <div className="report-head">
          <p className="report-label">
            <Sparkles size={16} aria-hidden="true" />
            {t('report.label')}
          </p>
          <StatusBadge status={report.status} />
        </div>

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
      </div>

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
          className="btn btn-secondary"
          disabled={busy || printState === 'loading'}
          onClick={() => void print()}
        >
          <Printer size={18} aria-hidden="true" />
          {t('report.print')}
        </button>
        {printState === 'loading' && <p role="status">{t('report.printLoading')}</p>}
        {printState === 'failed' && <p role="alert">{t('report.printFailed')}</p>}
        <button
          type="button"
          className="btn btn-secondary"
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
          // Overwrites the driver's edits, so it stays out of the way.
          <button
            type="button"
            className="link-btn report-regenerate"
            disabled={busy}
            onClick={() => {
              setConfirming(true)
            }}
          >
            <RotateCw size={16} aria-hidden="true" />
            {t('report.regenerate')}
          </button>
        )}
      </div>
      {createPortal(
        <article className="report-print" lang={report.locale} ref={printView}>
          <p className="report-print-body">{fillClaimant(body, claimant)}</p>
          {photos.map((photo, index) => (
            <figure key={photo.id}>
              <img
                src={photoSrc(photo.url)}
                alt={t('photos.photo', { n: index + 1, lng: report.locale })}
                loading="eager"
              />
              <figcaption>{t('photos.photo', { n: index + 1, lng: report.locale })}</figcaption>
            </figure>
          ))}
        </article>,
        document.body,
      )}
    </>
  )
}

const CLAIMANT_FIELDS = [
  { field: 'name', autoComplete: 'name' },
  { field: 'address', autoComplete: 'street-address' },
  { field: 'phone', autoComplete: 'tel' },
  { field: 'bankAccount', autoComplete: 'off' },
] as const

/**
 * "Your details": kept in this browser only, never sent to the server (ADR 0009). Open
 * until they are saved on this device; after that the copy fills them in on its own.
 */
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
  // Decided once: ticking "Remember" must not fold the form away while it is being filled.
  const [open] = useState(() => !remember)

  const change = (next: Claimant) => {
    onChange(next)
    if (remember) rememberClaimant(next)
  }

  return (
    <Fold summary={t('report.details.title')} open={open}>
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
    </Fold>
  )
}

/** Static copy, approved in docs/copy/safety-checklist.md: no guess at the road manager. */
function AddresseeHelp() {
  const { t } = useTranslation()
  const help = t('report.addressee', { returnObjects: true })
  return (
    <Fold summary={help.title} open={false}>
      <ul className="report-addressee">
        {help.items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      <a className="report-lookup" href={WHO_MANAGES_URL} target="_blank" rel="noreferrer">
        {help.lookup}
        <ExternalLink size={14} aria-hidden="true" />
      </a>
    </Fold>
  )
}
