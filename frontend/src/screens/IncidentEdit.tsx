import { ArrowLeft, Crosshair, MapPin, X } from 'lucide-react'
import { useId, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'
import {
  useIncident,
  useUpdateIncident,
  type IncidentPatch,
  type IncidentRead,
  type LocationIn,
} from '../api/incidents'
import { useVehicles, type VehicleRead } from '../api/vehicles'
import { ErrorNotice } from '../components/ErrorNotice'
import { NOTE_MAX } from '../components/HelpSheet'
import { SituationPick, type Situation } from '../components/SituationPick'
import { locateOnce, type GeoState } from '../lib/geolocation'
import { formatCoords } from '../lib/place'
import { PROBLEM_TYPES, problemKey, type ProblemType } from '../lib/problemType'
import '../components/HelpSheet.css'
import './IncidentScreen.css'
import './Vehicles.css'

/** `/incidents/:id/edit`: correct the note, problem type, location and vehicle. */
export function IncidentEdit() {
  const { t } = useTranslation()
  const id = Number(useParams().id)
  const incident = useIncident(id)
  const vehicles = useVehicles()

  const back = (
    <Link to={`/incidents/${String(id)}`} className="back">
      <ArrowLeft size={20} aria-hidden="true" />
      {t('common.back')}
    </Link>
  )

  if (!incident.data || !vehicles.data) {
    const error = incident.error ?? vehicles.error
    return (
      <>
        {back}
        {!incident.isEnabled ? (
          <p className="notice notice-error" role="alert">
            {t('errors.not_found')}
          </p>
        ) : error ? (
          <ErrorNotice error={error} />
        ) : (
          <p className="muted">{t('common.loading')}</p>
        )}
      </>
    )
  }

  return (
    <>
      {back}
      <h1>{t('incidentForm.heading')}</h1>
      <EditForm key={incident.data.id} incident={incident.data} vehicles={vehicles.data} />
    </>
  )
}

type Place = LocationIn | null

const toPlace = (loc: IncidentRead['location']): Place =>
  loc ? { lat: loc.lat, lon: loc.lon, accuracy_m: loc.accuracy_m } : null

const samePlace = (a: Place, b: Place) =>
  a === b ||
  (a !== null &&
    b !== null &&
    a.lat === b.lat &&
    a.lon === b.lon &&
    (a.accuracy_m ?? null) === (b.accuracy_m ?? null))

/** Only the fields the driver changed, so PATCH never rewrites what they left alone. */
function changes(
  incident: IncidentRead,
  draft: {
    problemType: ProblemType
    situation: Situation
    note: string
    vehicleId: number | null
    place: Place
  },
): IncidentPatch {
  const patch: IncidentPatch = {}
  if (draft.problemType !== incident.problem_type) patch.problem_type = draft.problemType
  if (draft.situation !== incident.situation) patch.situation = draft.situation
  const note = draft.note.trim() || null
  if (note !== incident.note) patch.note = note
  if (draft.vehicleId !== incident.vehicle_id) patch.vehicle_id = draft.vehicleId
  if (!samePlace(draft.place, toPlace(incident.location))) patch.location = draft.place
  return patch
}

function EditForm({ incident, vehicles }: { incident: IncidentRead; vehicles: VehicleRead[] }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const update = useUpdateIncident(incident.id)
  const location = useLocation()
  // Diff against what the form started from, so a background refetch can't make an
  // untouched field look edited and PATCH it back.
  const [base] = useState(incident)
  const [problemType, setProblemType] = useState(incident.problem_type)
  const [situation, setSituation] = useState(incident.situation)
  const [note, setNote] = useState(incident.note ?? '')
  const [vehicleId, setVehicleId] = useState(incident.vehicle_id)
  const [place, setPlace] = useState<Place>(toPlace(incident.location))
  const [geo, setGeo] = useState<GeoState | null>(null)
  const noteId = useId()

  const vehicle = vehicles.find((v) => v.id === vehicleId) ?? null
  // The label stays only while the point is the one it was computed for.
  const placeText = samePlace(place, toPlace(base.location))
    ? (base.location_label ?? (place ? formatCoords(place) : null))
    : place && formatCoords(place)

  const locate = async () => {
    setGeo({ status: 'detecting' })
    const next = await locateOnce()
    setGeo(next)
    if (next.status === 'found')
      setPlace({ lat: next.lat, lon: next.lon, accuracy_m: next.accuracy })
  }

  // Back to the detail entry we came from (keeping its state); a deep link has none.
  const leave = () => {
    if (location.key === 'default')
      void navigate(`/incidents/${String(incident.id)}`, { replace: true })
    else void navigate(-1)
  }

  const onSubmit = async (e: React.SyntheticEvent) => {
    e.preventDefault()
    const patch = changes(base, { problemType, situation, note, vehicleId, place })
    if (Object.keys(patch).length === 0) {
      leave()
      return
    }
    try {
      await update.update(patch)
      leave()
    } catch {
      // Shown below from `update.error`.
    }
  }

  return (
    <form className="vform" onSubmit={(e) => void onSubmit(e)} noValidate>
      <fieldset className="vehicle-pick">
        <legend className="note-label">{t('incidentForm.problemType')}</legend>
        {PROBLEM_TYPES.map((type) => (
          <label key={type} className="choice">
            <input
              type="radio"
              name="problem_type"
              checked={problemType === type}
              onChange={() => {
                setProblemType(type)
              }}
            />
            <span>{t(`start.tiles.${problemKey(type, vehicle?.fuel_type)}`)}</span>
          </label>
        ))}
      </fieldset>

      <SituationPick value={situation} onChange={setSituation} />

      <div className="vform-field">
        <label htmlFor={noteId}>{t('incidentForm.note')}</label>
        <textarea
          id={noteId}
          className="field"
          rows={3}
          maxLength={NOTE_MAX}
          value={note}
          onChange={(e) => {
            setNote(e.target.value)
          }}
        />
      </div>

      {(vehicles.length > 0 || vehicleId !== null) && (
        <fieldset className="vehicle-pick">
          <legend className="note-label">{t('incidentForm.vehicle')}</legend>
          {[...vehicles, null].map((v) => (
            <label key={v?.id ?? 'none'} className="choice">
              <input
                type="radio"
                name="vehicle"
                checked={vehicleId === (v?.id ?? null)}
                onChange={() => {
                  setVehicleId(v?.id ?? null)
                }}
              />
              <span>{v ? v.name : t('incidentForm.noVehicle')}</span>
            </label>
          ))}
        </fieldset>
      )}

      <fieldset className="vehicle-pick">
        <legend className="note-label">{t('incidentForm.location')}</legend>
        <p className="edit-place">
          <MapPin size={18} aria-hidden="true" />
          <span>{placeText ?? t('incident.noLocation')}</span>
        </p>
        {geo?.status === 'denied' && <p className="notice">{t('location.denied')}</p>}
        {geo?.status === 'unavailable' && <p className="notice">{t('location.unavailable')}</p>}
        <div className="upkeep-row">
          <button
            type="button"
            className="btn btn-quiet"
            disabled={geo?.status === 'detecting'}
            onClick={() => void locate()}
          >
            <Crosshair size={18} aria-hidden="true" />
            {geo?.status === 'detecting'
              ? t('incidentForm.detecting')
              : t('incidentForm.useCurrent')}
          </button>
          {place && (
            <button
              type="button"
              className="btn btn-quiet"
              onClick={() => {
                setPlace(null)
                setGeo(null)
              }}
            >
              <X size={18} aria-hidden="true" />
              {t('incidentForm.removeLocation')}
            </button>
          )}
        </div>
      </fieldset>

      {update.isError && <ErrorNotice error={update.error} />}
      <button type="submit" className="btn btn-primary" disabled={update.isPending}>
        {update.isPending ? t('incidentForm.saving') : t('incidentForm.save')}
      </button>
    </form>
  )
}
