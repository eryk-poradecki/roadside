import { CarFront, Plus } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'
import { ErrorNotice } from '../components/ErrorNotice'
import { useConfig } from '../api/config'
import { useDesktop } from '../lib/useMediaQuery'
import {
  replacementBody,
  useDeleteVehicle,
  useReplaceVehicle,
  useVehicles,
  type VehicleRead,
} from '../api/vehicles'
import './Vehicles.css'

function VehicleCard({
  vehicle,
  demoMode,
  open,
}: {
  vehicle: VehicleRead
  demoMode: boolean
  /** Its form is open beside the list (desktop). */
  open: boolean
}) {
  const { t } = useTranslation()
  const [confirming, setConfirming] = useState(false)
  const replace = useReplaceVehicle()
  const remove = useDeleteVehicle()
  const subtitle = [vehicle.make_model, vehicle.year].filter((part) => part !== null).join(' · ')
  const name = vehicle.name
  const readOnly = demoMode && vehicle.demo_profile != null

  return (
    <li className="vehicle" aria-current={open ? 'true' : undefined}>
      <div className="vehicle-head">
        <div className="vehicle-title">
          <h2>{name}</h2>
          {subtitle && <p className="muted">{subtitle}</p>}
        </div>
        <div className="vehicle-badges">
          {readOnly && <span className="badge">{t('demo.vehicleLabel')}</span>}
          {vehicle.is_default && (
            <span className="badge badge-strong">{t('vehicles.default')}</span>
          )}
        </div>
      </div>

      {confirming && !readOnly ? (
        <div
          className="vehicle-confirm"
          role="group"
          aria-label={t('vehicles.deleteLabel', { name })}
        >
          <p>{t('vehicles.confirmDelete', { name })}</p>
          <div className="vehicle-actions">
            <button
              type="button"
              className="btn btn-danger"
              disabled={remove.isPending}
              onClick={() => {
                remove.mutate({ path: { vehicle_id: vehicle.id } })
              }}
            >
              {t('vehicles.confirmDeleteYes')}
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
      ) : open ? null : (
        // The open card's form beside it edits, sets the default and is the one place that
        // changes it, so a card action can't race the form's draft (#67).
        <div className="vehicle-actions">
          {!readOnly && (
            <Link
              className="btn btn-quiet"
              to={`/vehicles/${String(vehicle.id)}`}
              aria-label={t('vehicles.editLabel', { name })}
            >
              {t('vehicles.edit')}
            </Link>
          )}
          {!vehicle.is_default && (
            <button
              type="button"
              className="btn btn-quiet"
              aria-label={t('vehicles.setDefaultLabel', { name })}
              disabled={replace.isPending}
              onClick={() => {
                replace.mutate({
                  path: { vehicle_id: vehicle.id },
                  body: { ...replacementBody(vehicle), is_default: true },
                })
              }}
            >
              {t('vehicles.setDefault')}
            </button>
          )}
          {!readOnly && (
            <button
              type="button"
              className="btn btn-quiet"
              aria-label={t('vehicles.deleteLabel', { name })}
              onClick={() => {
                setConfirming(true)
              }}
            >
              {t('vehicles.delete')}
            </button>
          )}
        </div>
      )}
      {replace.isError && <ErrorNotice error={replace.error} />}
    </li>
  )
}

/** No vehicles yet: what adding one is for, and the way to add it. */
function EmptyVehicles() {
  const { t } = useTranslation()
  return (
    <div className="vehicles-empty">
      <span className="vehicles-empty-icon" aria-hidden="true">
        <CarFront size={28} strokeWidth={1.75} />
      </span>
      <h2>{t('vehicles.emptyTitle')}</h2>
      <p className="muted">{t('vehicles.empty')}</p>
    </div>
  )
}

/**
 * The vehicle list with "Add a vehicle". `openId` marks the vehicle whose form is open beside
 * it on desktop.
 */
function VehicleList({ openId }: { openId?: number | undefined }) {
  const { t } = useTranslation()
  const desktop = useDesktop()
  const {
    data: config,
    isPending: configPending,
    isError: configIsError,
    error: configError,
  } = useConfig()
  const { data: vehicles, isPending, isError, error } = useVehicles()

  return (
    <div className="vehicles-page">
      <div className="vehicles-head">
        <h1>{t('vehicles.heading')}</h1>
        {vehicles && vehicles.length > 0 && (
          <p className="muted">{t('vehicles.count', { count: vehicles.length })}</p>
        )}
      </div>

      {config?.demo_mode && <p className="notice">{t('demo.vehiclesHint')}</p>}

      {(isPending || configPending) && <p className="muted">{t('common.loading')}</p>}
      {configIsError && <ErrorNotice error={configError} />}
      {isError && (
        <>
          <p className="notice notice-error" role="alert">
            {t('vehicles.loadFailed')}
          </p>
          <ErrorNotice error={error} />
        </>
      )}

      {/* Desktop shows it in the right column instead. */}
      {vehicles?.length === 0 && !desktop && <EmptyVehicles />}
      {vehicles && vehicles.length > 0 && !vehicles.some((v) => v.is_default) && (
        <p className="notice">{t('vehicles.noDefault')}</p>
      )}
      {config && vehicles && vehicles.length > 0 && (
        <ul className="vehicle-list" aria-label={t('vehicles.listLabel')}>
          {vehicles.map((vehicle) => (
            <VehicleCard
              key={vehicle.id}
              vehicle={vehicle}
              demoMode={config.demo_mode}
              open={vehicle.id === openId}
            />
          ))}
        </ul>
      )}

      <Link to="/vehicles/new" className="btn btn-primary">
        <Plus size={22} aria-hidden="true" />
        {t('vehicles.add')}
      </Link>
    </div>
  )
}

/**
 * Desktop (ADR 0012, #67): the list on the left and `detail` (a vehicle's form, or a prompt
 * to pick one) on the right. Mobile: `detail` alone, or the list where there is none. The
 * slots keep their places in the tree, so crossing the breakpoint keeps what was typed.
 */
export function VehiclesSplit({
  openId,
  detail,
}: {
  openId?: number | undefined
  detail: ReactNode | null
}) {
  const desktop = useDesktop()
  return (
    <div className="vehicles-split">
      {(desktop || detail === null) && <VehicleList openId={openId} />}
      {detail !== null && <div className="vehicles-detail">{detail}</div>}
    </div>
  )
}

/** `/vehicles`. */
export function Vehicles() {
  const { t } = useTranslation()
  const desktop = useDesktop()
  const { data: vehicles } = useVehicles()
  // Nothing beside the list until it has loaded: no "pick one" from a list that isn't there.
  const detail =
    vehicles === undefined ? null : vehicles.length === 0 ? (
      <EmptyVehicles />
    ) : (
      <p className="vehicles-pick">{t('vehicles.pick')}</p>
    )
  return <VehiclesSplit detail={desktop ? detail : null} />
}
