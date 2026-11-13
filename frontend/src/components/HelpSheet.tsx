import { X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import type { DemoScenario } from '../api/generated'
import { useConfig } from '../api/config'
import { useCreateIncident } from '../api/incidents'
import { photoSrc, useAddPhoto, type PhotoSource } from '../api/photos'
import type { VehicleRead } from '../api/vehicles'
import type { GeoState } from '../lib/geolocation'
import { problemKey, type ProblemType } from '../lib/problemType'
import { EmergencyLink } from './AppShell'
import { ErrorNotice } from './ErrorNotice'
import { SituationPick, type Situation } from './SituationPick'
import { AddPhotos, DEFAULT_MAX_PHOTOS, PhotoGrid, VisionNote } from './PhotoPicker'
import { TILE_ICONS } from './tiles'
import './HelpSheet.css'

/** Same cap as the API's `note`. */
export const NOTE_MAX = 280

type Props = {
  scenario?: DemoScenario
  problemType: ProblemType
  vehicles: VehicleRead[]
  geo: GeoState
  /** One per help request, owned by Start so it survives closing and reopening the sheet. */
  idempotencyKey: string
  onCreated: () => void
  onClose: () => void
}

/** A photo picked in the sheet, uploaded once the incident exists. */
type Picked = { key: number; source: PhotoSource; preview: string }

let nextPickKey = 1

/** A local preview of a picked file; none where the browser can't make one (tests). */
const previewOf = (source: PhotoSource, sampleUrl: (id: string) => string) => {
  if ('sampleId' in source) return sampleUrl(source.sampleId)
  return typeof URL.createObjectURL === 'function' ? URL.createObjectURL(source.file) : ''
}

const revoke = (picked: Picked) => {
  if ('file' in picked.source && picked.preview) URL.revokeObjectURL(picked.preview)
}

/**
 * The help sheet: optional note and photos, the vehicle for this request, and "Get help now".
 * The photos upload after the incident is created, while the Result screen already shows
 * the checklist; the first AI turn waits for them (ADR 0002).
 */
export function HelpSheet({
  scenario,
  problemType,
  vehicles,
  geo,
  idempotencyKey,
  onCreated,
  onClose,
}: Props) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const create = useCreateIncident()
  const addPhoto = useAddPhoto()
  const config = useConfig().data
  const maxPhotos = config?.max_photos ?? DEFAULT_MAX_PHOTOS
  const ref = useRef<HTMLDialogElement>(null)
  const titleRef = useRef<HTMLHeadingElement>(null)
  // A request that finishes after the driver closed the sheet must not navigate them away.
  const mounted = useRef(true)
  const [note, setNote] = useState(
    scenario?.locales[i18n.resolvedLanguage ?? i18n.language]?.note ?? '',
  )
  // Never parked unless the driver says so: the full checklist is the safe default.
  const [situation, setSituation] = useState<Situation>(scenario?.situation ?? 'on_road')
  const [photos, setPhotos] = useState<Picked[]>(() =>
    (scenario?.sample_photo_ids ?? []).map((id) => ({
      key: nextPickKey++,
      source: { sampleId: id },
      preview: photoSrc(config?.sample_photos.find((sample) => sample.id === id)?.url ?? ''),
    })),
  )
  // The latest list, for revoking previews on unmount.
  const photosRef = useRef(photos)
  useEffect(() => {
    photosRef.current = photos
  }, [photos])
  // `undefined` until the driver picks: follow the default vehicle, even if it loads late.
  const [picked, setPicked] = useState<number | null | undefined>(undefined)
  const titleId = useId()
  const noteId = useId()

  const defaultId = vehicles.find((v) => v.is_default)?.id ?? null
  const vehicleId = scenario
    ? (vehicles.find(
        (v) => scenario.vehicle_profile !== null && v.demo_profile === scenario.vehicle_profile,
      )?.id ?? null)
    : picked === undefined
      ? defaultId
      : picked
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
      photosRef.current.forEach(revoke)
    }
  }, [])

  const sampleUrl = (id: string) => {
    const sample = config?.sample_photos.find((s) => s.id === id)
    return sample ? photoSrc(sample.url) : ''
  }

  const submit = async () => {
    const location =
      scenario?.location ??
      (geo.status === 'found' ? { lat: geo.lat, lon: geo.lon, accuracy_m: geo.accuracy } : null)
    try {
      const incident = await create.create(
        {
          problem_type: problemType,
          vehicle_id: vehicleId,
          note: note.trim() || null,
          location,
          situation,
        },
        idempotencyKey,
      )
      // Into the mutation cache, so they keep going after the sheet closes and the Result
      // screen can wait for them before the first AI turn.
      for (const photo of photos) addPhoto.mutate({ incidentId: incident.id, source: photo.source })
      photos.forEach(revoke)
      setPhotos([])
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

        {!scenario && <p className="sheet-intro">{t('sheet.intro')}</p>}

        <label className="note-label" htmlFor={noteId}>
          {t('sheet.noteLabel')}
        </label>
        <textarea
          id={noteId}
          className="field"
          rows={2}
          maxLength={NOTE_MAX}
          placeholder={t('sheet.notePlaceholder')}
          readOnly={!!scenario}
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

        <div className="sheet-photos" role="group" aria-label={t('photos.sheetLabel')}>
          <p className="note-label">{t('photos.sheetLabel')}</p>
          <PhotoGrid
            items={photos.map((photo) => ({
              key: photo.key,
              src: photo.preview,
              onRemove: scenario
                ? undefined
                : () => {
                    revoke(photo)
                    setPhotos((list) => list.filter((p) => p.key !== photo.key))
                  },
            }))}
          />
          {!scenario && photos.length < maxPhotos && (
            <AddPhotos
              remaining={maxPhotos - photos.length}
              onPick={(sources) => {
                const added = sources.slice(0, maxPhotos - photos.length).map((source) => ({
                  key: nextPickKey++,
                  source,
                  preview: previewOf(source, sampleUrl),
                }))
                setPhotos([...photos, ...added])
              }}
            />
          )}
          <VisionNote />
        </div>

        <fieldset disabled={!!scenario} className="scenario-fields">
          <SituationPick value={situation} onChange={setSituation} />

          {(vehicles.length > 0 || scenario) && (
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
        </fieldset>
        {create.isError && <ErrorNotice error={create.error} />}
      </div>

      <div className="sheet-actions">
        {scenario && (
          <button type="button" className="btn btn-quiet" onClick={onClose}>
            {t('demo.changeScenario')}
          </button>
        )}
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
