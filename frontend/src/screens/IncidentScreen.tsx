import {
  ArrowLeft,
  TriangleAlert,
  Car,
  Check,
  CircleCheck,
  MapPin,
  Pencil,
  Phone,
  RotateCcw,
  SquareParking,
  Trash2,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'
import {
  useDeleteIncident,
  useIncident,
  useUpdateIncident,
  type IncidentRead,
} from '../api/incidents'
import { useVehicles, type VehicleRead } from '../api/vehicles'
import { findAdvice } from '../api/aiTurns'
import { AiPanel } from '../components/AiPanel'
import { DockAction, EmergencyFirst, useDockUrgent } from '../components/AppShell'
import { DamageReportCard, PotholeHint } from '../components/DamageReportCard'
import { ErrorNotice } from '../components/ErrorNotice'
import { NearbyPanel } from '../components/NearbyPanel'
import { PhotosPanel } from '../components/PhotosPanel'
import { SafetyChecklist } from '../components/SafetyChecklist'
import { TILE_ICONS } from '../components/tiles'
import { formatCoords } from '../lib/place'
import { problemKey } from '../lib/problemType'
import './IncidentScreen.css'

/**
 * `/incidents/:id`: the Result screen right after "Get help now", and Incident detail later.
 * The checklist is bundled copy, so it renders as soon as the incident is known.
 */
export function IncidentScreen() {
  const { t } = useTranslation()
  const id = Number(useParams().id)
  const incident = useIncident(id)
  const vehicles = useVehicles()
  const state: unknown = useLocation().state
  const fromHelp = typeof state === 'object' && state !== null && 'fromHelp' in state

  const back = (
    <Link to={fromHelp ? '/' : '/incidents'} className="back">
      <ArrowLeft size={20} aria-hidden="true" />
      {t('common.back')}
    </Link>
  )

  if (!incident.data) {
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

  // The label and the checklist variant follow the incident's vehicle (ADR 0003, 0010).
  const vehicleId = incident.data.vehicle_id
  if (vehicleId !== null && vehicles.isPending) {
    return (
      <>
        {back}
        <p className="muted">{t('common.loading')}</p>
      </>
    )
  }
  const vehicle = vehicles.data?.find((v) => v.id === vehicleId) ?? null
  const noVehicles = vehicles.data?.length === 0

  return (
    <>
      <Result
        incident={incident.data}
        vehicle={vehicle}
        noVehicles={noVehicles}
        fromHelp={fromHelp}
        back={back}
      />
      {/* Without the vehicle the checklist falls back to the fuel list and the insurer
          button is missing, so say so instead of failing silently. */}
      {vehicleId !== null && vehicles.isError && <ErrorNotice error={vehicles.error} />}
    </>
  )
}

function Result({
  incident,
  vehicle,
  noVehicles,
  fromHelp,
  back,
}: {
  incident: IncidentRead
  vehicle: VehicleRead | null
  noVehicles: boolean
  /** Arrived straight from "Get help now": ask the assistant at once. */
  fromHelp: boolean
  back: React.ReactNode
}) {
  const { t } = useTranslation()
  const key = problemKey(incident.problem_type, vehicle?.fuel_type)
  const Icon = TILE_ICONS[key]
  const resolved = incident.status === 'resolved'
  const loc = incident.location
  const adviceTurn = findAdvice(incident)
  // A resolved record keeps its answer but no longer calls for 112 first.
  const urgent = adviceTurn?.urgent === true && !resolved

  return (
    <div className="result">
      <div className="topbar">
        {back}
        <p className={resolved ? 'status status-resolved' : 'status'}>
          {resolved ? (
            <CircleCheck size={16} aria-hidden="true" />
          ) : (
            <Check size={16} aria-hidden="true" />
          )}
          {resolved ? t('incident.resolved') : t('incident.saved')}
        </p>
      </div>

      <header className="result-head">
        <h1>
          <Icon size={30} strokeWidth={1.75} aria-hidden="true" />
          {t(`start.tiles.${key}`)}
        </h1>
        <p className="result-meta">
          {vehicle && (
            <span>
              <Car size={18} aria-hidden="true" />
              {vehicle.name}
            </span>
          )}
          <span>
            <MapPin size={18} aria-hidden="true" />
            {incident.location_label ?? (loc ? formatCoords(loc) : t('incident.noLocation'))}
          </span>
          {incident.situation === 'parked' && (
            <span>
              <SquareParking size={18} aria-hidden="true" />
              {t('situation.parkedShort')}
            </span>
          )}
        </p>
      </header>

      {urgent && (
        <div className="notice notice-error urgent-banner" role="alert">
          <TriangleAlert size={22} aria-hidden="true" />
          <p>
            <strong>{t('ai.urgentTitle')}</strong>
            <span>{t('ai.urgentBody')}</span>
          </p>
          <EmergencyFirst />
        </div>
      )}

      {/* One column on mobile; on desktop the advice beside the record (ADR 0008). */}
      <div className="result-columns">
        <div className="result-col">
          <SafetyChecklist
            problem={key}
            situation={incident.situation}
            resolved={resolved}
            answered={adviceTurn !== undefined}
          />

          <AiPanel incident={incident} autoStart={fromHelp} noVehicles={noVehicles} />
        </div>

        <div className="result-col">
          <NearbyPanel incident={incident} fuelType={vehicle?.fuel_type} />

          <PhotosPanel incident={incident} />

          {incident.problem_type === 'flat_tyre' && <PotholeHint incident={incident} />}
          <DamageReportCard incident={incident} />

          <Upkeep incident={incident} />
        </div>
      </div>

      {vehicle?.assistance_phone && <CallAssistance vehicle={vehicle} />}
    </div>
  )
}

/** Mark resolved / Reopen, edit and delete: the driver's upkeep of the record (ADR 0001). */
function Upkeep({ incident }: { incident: IncidentRead }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const update = useUpdateIncident(incident.id)
  const remove = useDeleteIncident(incident.id)
  const [confirming, setConfirming] = useState(false)
  const resolved = incident.status === 'resolved'

  const toggleStatus = async () => {
    try {
      await update.update({ status: resolved ? 'open' : 'resolved' })
    } catch {
      // Shown below from `update.error`.
    }
  }
  const confirmDelete = async () => {
    try {
      await remove.remove(() => {
        void navigate('/incidents', { replace: true })
      })
    } catch {
      // Shown below from `remove.error`.
    }
  }

  return (
    <section className="upkeep" aria-label={t('incident.manageLabel')}>
      <button
        type="button"
        className="btn btn-quiet upkeep-status"
        disabled={update.isPending}
        onClick={() => void toggleStatus()}
      >
        {resolved ? (
          <RotateCcw size={20} aria-hidden="true" />
        ) : (
          <CircleCheck size={20} aria-hidden="true" />
        )}
        {resolved ? t('incident.reopen') : t('incident.markResolved')}
      </button>
      {update.isError && <ErrorNotice error={update.error} />}

      {confirming ? (
        <div className="upkeep-confirm" role="group" aria-label={t('incident.delete')}>
          <p>{t('incident.confirmDelete')}</p>
          <div className="upkeep-row">
            <button
              type="button"
              className="btn btn-danger"
              disabled={remove.isPending}
              onClick={() => void confirmDelete()}
            >
              {t('incident.confirmDeleteYes')}
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
          {remove.isError && <ErrorNotice error={remove.error} />}
        </div>
      ) : (
        <div className="upkeep-row">
          <Link className="btn btn-quiet" to={`/incidents/${String(incident.id)}/edit`}>
            <Pencil size={18} aria-hidden="true" />
            {t('incident.edit')}
          </Link>
          <button
            type="button"
            className="btn btn-quiet"
            onClick={() => {
              setConfirming(true)
            }}
          >
            <Trash2 size={18} aria-hidden="true" />
            {t('incident.delete')}
          </button>
        </div>
      )}
    </section>
  )
}

/** Rendered only from what the driver entered, so the number can never be invented. */
function CallAssistance({ vehicle }: { vehicle: VehicleRead }) {
  const { t } = useTranslation()
  // Beside an urgent 112 it steps down so the two never compete.
  const urgent = useDockUrgent()
  const phone = (vehicle.assistance_phone ?? '').replace(/[^\d+]/g, '')
  if (!/\d/.test(phone)) return null
  return (
    <DockAction>
      <a
        className={urgent ? 'btn btn-quiet btn-call' : 'btn btn-primary btn-call'}
        href={`tel:${phone}`}
      >
        <Phone size={20} aria-hidden="true" />
        <span className="btn-call-text">
          <span>
            {vehicle.assistance_insurer
              ? t('incident.callInsurer', { insurer: vehicle.assistance_insurer })
              : t('incident.callAssistance')}
          </span>
          {vehicle.policy_number && (
            <small>{t('incident.policy', { number: vehicle.policy_number })}</small>
          )}
        </span>
      </a>
    </DockAction>
  )
}
