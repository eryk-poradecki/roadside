import { Plus } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'
import { ErrorNotice } from '../components/ErrorNotice'
import { useConfig } from '../api/config'
import {
  replacementBody,
  useDeleteVehicle,
  useReplaceVehicle,
  useVehicles,
  type VehicleRead,
} from '../api/vehicles'
import './Vehicles.css'

function VehicleCard({ vehicle, demoMode }: { vehicle: VehicleRead; demoMode: boolean }) {
  const { t } = useTranslation()
  const [confirming, setConfirming] = useState(false)
  const replace = useReplaceVehicle()
  const remove = useDeleteVehicle()
  const subtitle = [vehicle.make_model, vehicle.year].filter((part) => part !== null).join(' · ')
  const name = vehicle.name
  const readOnly = demoMode && vehicle.demo_profile != null

  return (
    <li className="vehicle">
      <div className="vehicle-head">
        <div className="vehicle-title">
          <h2>{name}</h2>
          {subtitle && <p className="muted">{subtitle}</p>}
        </div>
        <div className="vehicle-badges">
          {readOnly && <span className="badge">{t('demo.vehicleLabel')}</span>}
          {vehicle.is_default && (
            <span className="badge badge-accent">{t('vehicles.default')}</span>
          )}
        </div>
      </div>

      {confirming ? (
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
      ) : (
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

export function Vehicles() {
  const { t } = useTranslation()
  const { data: config } = useConfig()
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

      {isPending && <p className="muted">{t('common.loading')}</p>}
      {isError && (
        <>
          <p className="notice notice-error" role="alert">
            {t('vehicles.loadFailed')}
          </p>
          <ErrorNotice error={error} />
        </>
      )}

      {vehicles?.length === 0 && <p className="notice">{t('vehicles.empty')}</p>}
      {vehicles && vehicles.length > 0 && !vehicles.some((v) => v.is_default) && (
        <p className="notice">{t('vehicles.noDefault')}</p>
      )}
      {vehicles && vehicles.length > 0 && (
        <ul className="vehicle-list" aria-label={t('vehicles.listLabel')}>
          {vehicles.map((vehicle) => (
            <VehicleCard key={vehicle.id} vehicle={vehicle} demoMode={config?.demo_mode === true} />
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
