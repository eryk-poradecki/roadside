import { ArrowLeft, Car, Check, CircleCheck, MapPin, Phone, Sparkles, Store } from 'lucide-react'
import { Link, useLocation, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useIncident, type IncidentRead } from '../api/incidents'
import { useVehicles, type VehicleRead } from '../api/vehicles'
import { DockAction } from '../components/AppShell'
import { ErrorNotice } from '../components/ErrorNotice'
import { SafetyChecklist } from '../components/SafetyChecklist'
import { TILE_ICONS } from '../components/tiles'
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
      <Result incident={incident.data} vehicle={vehicle} noVehicles={noVehicles} back={back} />
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
  back,
}: {
  incident: IncidentRead
  vehicle: VehicleRead | null
  noVehicles: boolean
  back: React.ReactNode
}) {
  const { t } = useTranslation()
  const key = problemKey(incident.problem_type, vehicle?.fuel_type)
  const Icon = TILE_ICONS[key]
  const resolved = incident.status === 'resolved'
  const loc = incident.location

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
            {incident.location_label ??
              (loc ? `${loc.lat.toFixed(5)}, ${loc.lon.toFixed(5)}` : t('incident.noLocation'))}
          </span>
        </p>
      </header>

      <SafetyChecklist problem={key} />

      {noVehicles && (
        <p className="notice invite">
          <span>{t('incident.addVehicle')}</span>
          <Link to="/vehicles/new" className="link-btn">
            {t('incident.addVehicleLink')}
          </Link>
        </p>
      )}

      <section className="panel panel-ai" aria-labelledby="ai-title">
        <div className="panel-head">
          <h2 id="ai-title">{t('incident.aiTitle')}</h2>
          <span className="badge badge-ai">
            <Sparkles size={14} aria-hidden="true" />
            {t('incident.aiBadge')}
          </span>
        </div>
        <p className="muted">{t('incident.aiSoon')}</p>
      </section>

      <section className="panel" aria-labelledby="nearby-title">
        <div className="panel-head">
          <h2 id="nearby-title">{t('incident.nearbyTitle')}</h2>
          <span className="badge">
            <Store size={14} aria-hidden="true" />
            {t('incident.nearbyBadge')}
          </span>
        </div>
        <p className="muted">{t('incident.nearbySoon')}</p>
      </section>

      {vehicle?.assistance_phone && <CallAssistance vehicle={vehicle} />}
    </div>
  )
}

/** Rendered only from what the driver entered, so the number can never be invented. */
function CallAssistance({ vehicle }: { vehicle: VehicleRead }) {
  const { t } = useTranslation()
  const phone = (vehicle.assistance_phone ?? '').replace(/[^\d+]/g, '')
  if (!/\d/.test(phone)) return null
  return (
    <DockAction>
      <a className="btn btn-primary btn-call" href={`tel:${phone}`}>
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
