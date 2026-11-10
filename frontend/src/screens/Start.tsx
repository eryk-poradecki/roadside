import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useVehicles } from '../api/vehicles'
import { HelpSheet } from '../components/HelpSheet'
import { LocationReadout } from '../components/LocationReadout'
import { TILE_ICONS } from '../components/tiles'
import { useGeolocation } from '../lib/geolocation'
import { PROBLEM_TYPES, problemKey, type ProblemType } from '../lib/problemType'
import { uuid } from '../lib/uuid'
import './Start.css'

/** Problem-type tiles, the detected location, and the help sheet behind each tile. */
export function Start() {
  const { t } = useTranslation()
  const vehicles = useVehicles().data ?? []
  const geo = useGeolocation()
  const [picked, setPicked] = useState<ProblemType | null>(null)
  const [opened, setOpened] = useState(0)
  // The idempotency key of the help request in progress. Reopening the same tile after a
  // failed or lost attempt keeps it, so the retry can't create a second incident. Another
  // problem type is a new help request, and a success ends this one.
  const [request, setRequest] = useState<{ type: ProblemType; key: string } | null>(null)
  // The tile label follows the default vehicle; the sheet follows the one picked there.
  const defaultFuel = vehicles.find((v) => v.is_default)?.fuel_type

  return (
    <>
      <LocationReadout geo={geo.state} onRetry={geo.supported ? geo.retry : undefined} />
      <div className="intro">
        <h1>{t('start.heading')}</h1>
        <p className="lede">{t('start.subheading')}</p>
      </div>
      <ul className="tiles" aria-label={t('start.tilesLabel')}>
        {PROBLEM_TYPES.map((type) => {
          const key = problemKey(type, defaultFuel)
          const Icon = TILE_ICONS[key]
          return (
            <li key={type} className={type === 'other' ? 'tile-wide' : undefined}>
              <button
                type="button"
                className="tile"
                onClick={() => {
                  if (request?.type !== type) setRequest({ type, key: uuid() })
                  setPicked(type)
                  setOpened((n) => n + 1)
                }}
              >
                <Icon size={28} strokeWidth={1.75} aria-hidden="true" />
                <span>{t(`start.tiles.${key}`)}</span>
              </button>
            </li>
          )
        })}
      </ul>
      {picked && request && (
        <HelpSheet
          key={opened}
          problemType={picked}
          vehicles={vehicles}
          geo={geo.state}
          idempotencyKey={request.key}
          onCreated={() => {
            setRequest(null)
          }}
          onClose={() => {
            setPicked(null)
          }}
        />
      )}
    </>
  )
}
