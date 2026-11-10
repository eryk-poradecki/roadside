import { X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { useCreateIncident } from '../api/incidents'
import type { VehicleRead } from '../api/vehicles'
import type { GeoState } from '../lib/geolocation'
import { problemKey, type ProblemType } from '../lib/problemType'
import { uuid } from '../lib/uuid'
import { ErrorNotice } from './ErrorNotice'
import { TILE_ICONS } from './tiles'
import './HelpSheet.css'

/** Same cap as the API's `note`. */
export const NOTE_MAX = 280

type Props = {
  problemType: ProblemType
  vehicles: VehicleRead[]
  geo: GeoState
  onClose: () => void
}

/**
 * The help sheet: optional note, the vehicle for this request, and "Get help now".
 * Mounted fresh for every tile tap, so each help request gets its own idempotency key.
 */
export function HelpSheet({ problemType, vehicles, geo, onClose }: Props) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const create = useCreateIncident()
  const ref = useRef<HTMLDialogElement>(null)
  const titleRef = useRef<HTMLHeadingElement>(null)
  // One key per help request: a double tap or a re-tap after a failure reuses it.
  const key = useRef<string | null>(null)
  const [note, setNote] = useState('')
  // `undefined` until the driver picks: follow the default vehicle, even if it loads late.
  const [picked, setPicked] = useState<number | null | undefined>(undefined)
  const titleId = useId()
  const noteId = useId()

  const defaultId = vehicles.find((v) => v.is_default)?.id ?? null
  const vehicleId = picked === undefined ? defaultId : picked
  const vehicle = vehicles.find((v) => v.id === vehicleId) ?? null
  const label = problemKey(problemType, vehicle?.fuel_type)
  const Icon = TILE_ICONS[label]

  useEffect(() => {
    const dialog = ref.current
    if (dialog && !dialog.open) dialog.showModal()
    titleRef.current?.focus()
  }, [])

  const submit = async () => {
    key.current ??= uuid()
    const location =
      geo.status === 'found' ? { lat: geo.lat, lon: geo.lon, accuracy_m: geo.accuracy } : null
    try {
      const incident = await create.create(
        { problem_type: problemType, vehicle_id: vehicleId, note: note.trim() || null, location },
        key.current,
      )
      void navigate(`/incidents/${String(incident.id)}`, { state: { fromHelp: true } })
    } catch {
      // Shown below from `create.error`; the driver can tap again with the same key.
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
    >
      <div className="sheet-body">
        <header className="sheet-head">
          <span className="sheet-icon" aria-hidden="true">
            <Icon size={26} strokeWidth={1.75} />
          </span>
          <h2 id={titleId} ref={titleRef} tabIndex={-1}>
            {t(`start.tiles.${label}`)}
          </h2>
          <a className="sos-chip" href="tel:112" aria-label={t('call112Label')}>
            112
          </a>
          <button
            type="button"
            className="icon-btn"
            onClick={onClose}
            aria-label={t('sheet.close')}
          >
            <X size={22} aria-hidden="true" />
          </button>
        </header>

        <p className="sheet-intro">{t('sheet.intro')}</p>

        <label className="note-label" htmlFor={noteId}>
          {t('sheet.noteLabel')}
        </label>
        <textarea
          id={noteId}
          className="field"
          rows={2}
          maxLength={NOTE_MAX}
          placeholder={t('sheet.notePlaceholder')}
          value={note}
          onChange={(e) => {
            setNote(e.target.value)
          }}
        />
        {note.length > 0 && (
          <p className="note-count" aria-hidden="true">
            {note.length}/{NOTE_MAX}
          </p>
        )}

        {vehicles.length > 0 && (
          <fieldset className="vehicle-pick">
            <legend className="note-label">{t('sheet.vehicleLabel')}</legend>
            {[...vehicles, null].map((v) => (
              <label key={v?.id ?? 'none'} className="choice">
                <input
                  type="radio"
                  name="vehicle"
                  checked={vehicleId === (v?.id ?? null)}
                  onChange={() => {
                    setPicked(v?.id ?? null)
                  }}
                />
                <span>{v ? v.name : t('sheet.noVehicle')}</span>
              </label>
            ))}
          </fieldset>
        )}

        {create.isError && <ErrorNotice error={create.error} />}
      </div>

      <div className="sheet-actions">
        <button
          type="button"
          className="btn btn-primary"
          disabled={create.isPending}
          onClick={() => void submit()}
        >
          {create.isPending ? t('sheet.sending') : t('sheet.getHelp')}
        </button>
      </div>
    </dialog>
  )
}
