import { X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { useCreateIncident } from '../api/incidents'
import type { VehicleRead } from '../api/vehicles'
import type { GeoState } from '../lib/geolocation'
import { problemKey, type ProblemType } from '../lib/problemType'
import { EmergencyLink } from './AppShell'
import { ErrorNotice } from './ErrorNotice'
import { TILE_ICONS } from './tiles'
import './HelpSheet.css'

/** Same cap as the API's `note`. */
export const NOTE_MAX = 280

type Props = {
  problemType: ProblemType
  vehicles: VehicleRead[]
  geo: GeoState
  /** One per help request, owned by Start so it survives closing and reopening the sheet. */
  idempotencyKey: string
  onCreated: () => void
  onClose: () => void
}

/** The help sheet: optional note, the vehicle for this request, and "Get help now". */
export function HelpSheet({
  problemType,
  vehicles,
  geo,
  idempotencyKey,
  onCreated,
  onClose,
}: Props) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const create = useCreateIncident()
  const ref = useRef<HTMLDialogElement>(null)
  const titleRef = useRef<HTMLHeadingElement>(null)
  // A request that finishes after the driver closed the sheet must not navigate them away.
  const mounted = useRef(true)
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
    mounted.current = true
    const dialog = ref.current
    if (dialog && !dialog.open) dialog.showModal()
    titleRef.current?.focus()
    return () => {
      mounted.current = false
    }
  }, [])

  const submit = async () => {
    const location =
      geo.status === 'found' ? { lat: geo.lat, lon: geo.lon, accuracy_m: geo.accuracy } : null
    try {
      const incident = await create.create(
        { problem_type: problemType, vehicle_id: vehicleId, note: note.trim() || null, location },
        idempotencyKey,
      )
      onCreated()
      if (mounted.current)
        void navigate(`/incidents/${String(incident.id)}`, { state: { fromHelp: true } })
    } catch {
      // Shown below from `create.error`. A re-tap reuses the key, so it can't duplicate.
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
          <EmergencyLink className="sos-chip">112</EmergencyLink>
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
