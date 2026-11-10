import { useEffect, useId, useRef, useState } from 'react'
import { Copy, Loader, Locate, MapPin, Phone, X } from 'lucide-react'
import { useT } from './i18n'
import { MOCK_ACCURACY, MOCK_ACCURACY_FOUND, MOCK_COORDS, MOCK_LAT, MOCK_LOC, MOCK_LON, type LocState } from './mock'

export function useLocation() {
  const [state, setState] = useState<LocState>(MOCK_LOC ?? 'detecting')
  const [manual, setManual] = useState<string | null>(null)
  const timer = useRef<number>(0)

  const settle = () => {
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(
      () => setState(MOCK_LOC === 'denied' || MOCK_LOC === 'weak' ? MOCK_LOC : 'found'),
      1400,
    )
  }

  useEffect(() => {
    if (!MOCK_LOC) settle()
    return () => window.clearTimeout(timer.current)
  }, [])

  const retry = () => {
    setManual(null)
    setState('detecting')
    settle()
  }

  return { state, manual, setManual, retry }
}

/** Full-width emergency bar, outside the scrolling area so it never covers content. */
export function EmergencyBar({ label }: { label?: string }) {
  const t = useT()
  return (
    <div className="sos-dock">
      <a className="sos" href="tel:112" aria-label={t.call112Label}>
        <Phone size={22} strokeWidth={2.25} aria-hidden="true" />
        <span>{label ?? t.callEmergency}</span>
      </a>
    </div>
  )
}

type Props = {
  state: LocState
  manual: string | null
  setManual: (v: string | null) => void
  retry: () => void
}

const EMPTY = '––.––––'

/** Dashboard-style location readout: the numbers are the instrument. */
export function LocationBar({ state, manual, setManual, retry }: Props) {
  const t = useT()
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  const tone = manual ? 'manual' : state
  const hasFix = !manual && (state === 'found' || state === 'weak')
  const label = copied
    ? t.loc.copied
    : manual || state === 'found'
      ? t.loc.found
      : state === 'weak'
        ? t.loc.weak
        : state === 'detecting'
          ? t.loc.detecting
          : t.loc.denied
  const action = state === 'detecting' && !manual ? null : state === 'denied' && !manual ? t.loc.set : t.loc.change
  const accuracyValue = state === 'weak' ? MOCK_ACCURACY : MOCK_ACCURACY_FOUND

  useEffect(() => {
    if (!copied) return
    const id = window.setTimeout(() => setCopied(false), 1600)
    return () => window.clearTimeout(id)
  }, [copied])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(MOCK_COORDS)
      setCopied(true)
    } catch {
      /* clipboard unavailable */
    }
  }

  const coords = (
    <>
      <p className="coord">
        <span className="num">{hasFix ? MOCK_LAT.value : EMPTY}</span>
        <small>° {MOCK_LAT.dir}</small>
      </p>
      <p className="coord">
        <span className="num">{hasFix ? MOCK_LON.value : EMPTY}</span>
        <small>° {MOCK_LON.dir}</small>
      </p>
    </>
  )

  return (
    <section className={`readout readout-${tone}`} aria-label={t.loc.found}>
      <div className="readout-head">
        <p className="readout-label" role="status">
          {tone === 'detecting' ? (
            <Loader size={18} className="spin" aria-hidden="true" />
          ) : tone === 'weak' ? (
            <Locate size={20} aria-hidden="true" />
          ) : tone === 'denied' ? (
            <MapPin size={18} aria-hidden="true" />
          ) : (
            <Locate size={22} aria-hidden="true" className="fix" />
          )}
          <span>{label}</span>
        </p>
        {action && (
          <button type="button" className="link-btn readout-action" onClick={() => setOpen(true)}>
            {action}
          </button>
        )}
      </div>

      {manual ? (
        <p className="readout-place">{manual}</p>
      ) : hasFix ? (
        <button type="button" className="coords coords-copy" onClick={copy} aria-label={`${t.loc.copy}: ${MOCK_COORDS}`}>
          {coords}
        </button>
      ) : (
        <div className="coords" aria-hidden="true">
          {coords}
        </div>
      )}

      {hasFix && (
        <p className="readout-foot">
          <span className="readout-place-sm">{state === 'weak' ? t.loc.weakSub : t.loc.mockPlace}</span>
          <span className="accuracy">
            {t.loc.accuracy}
            {accuracyValue}
          </span>
        </p>
      )}

      <LocationSheet
        open={open}
        onClose={() => setOpen(false)}
        initial={manual ?? ''}
        hasCoords={state === 'found' || state === 'weak'}
        onUse={(v) => {
          setManual(v)
          setOpen(false)
        }}
        onRetry={() => {
          retry()
          setOpen(false)
        }}
      />
    </section>
  )
}

type SheetProps = {
  open: boolean
  onClose: () => void
  initial: string
  hasCoords: boolean
  onUse: (v: string) => void
  onRetry: () => void
}

function LocationSheet({ open, onClose, initial, hasCoords, onUse, onRetry }: SheetProps) {
  const t = useT()
  const ref = useRef<HTMLDialogElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [value, setValue] = useState(initial)
  const [copied, setCopied] = useState(false)
  const titleId = useId()
  const inputId = useId()

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) {
      setValue(initial)
      setCopied(false)
      d.showModal()
      inputRef.current?.focus()
    } else if (!open && d.open) {
      d.close()
    }
  }, [open, initial])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(MOCK_COORDS)
      setCopied(true)
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <dialog
      ref={ref}
      className="sheet"
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault()
        onClose()
      }}
      onClick={(e) => {
        if (e.target === ref.current) onClose()
      }}
    >
      <div className="sheet-grab">
        <span className="sheet-handle" aria-hidden="true" />
      </div>
      <form
        className="sheet-body loc-panel"
        onSubmit={(e) => {
          e.preventDefault()
          if (value.trim()) onUse(value.trim())
        }}
      >
        <header className="sheet-head">
          <h2 id={titleId}>{t.loc.panelTitle}</h2>
          <button type="button" className="icon-btn" onClick={onClose} aria-label={t.loc.close}>
            <X size={22} aria-hidden="true" />
          </button>
        </header>
        <label htmlFor={inputId} className="note-label">
          {t.loc.deniedHelp}
        </label>
        <input
          ref={inputRef}
          id={inputId}
          type="text"
          className="field"
          placeholder={t.loc.addressPlaceholder}
          aria-label={t.loc.addressLabel}
          autoComplete="off"
          enterKeyHint="go"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <button type="submit" className="btn btn-primary" disabled={!value.trim()}>
          {t.loc.useThis}
        </button>
        <div className="loc-panel-links">
          <button type="button" className="link-btn" onClick={onRetry}>
            {t.loc.retry}
          </button>
          {hasCoords && (
            <button type="button" className="link-btn" onClick={copy}>
              <Copy size={16} aria-hidden="true" />
              &nbsp;{copied ? t.loc.copied : t.loc.copy}
            </button>
          )}
        </div>
      </form>
    </dialog>
  )
}
