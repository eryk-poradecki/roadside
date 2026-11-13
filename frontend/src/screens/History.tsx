import { ChevronRight, Car, MapPin } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useIncidents, type IncidentStatus, type IncidentSummary } from '../api/incidents'
import { useVehicles, type VehicleRead } from '../api/vehicles'
import { ErrorNotice } from '../components/ErrorNotice'
import { PlacesMap } from '../components/map/LazyPlacesMap'
import type { MapPin as Pin } from '../components/map/PlacesMap'
import { TILE_ICONS } from '../components/tiles'
import { formatCoords } from '../lib/place'
import { problemKey } from '../lib/problemType'
import { useDesktop } from '../lib/useMediaQuery'
import './History.css'

type Filter = IncidentStatus | null
const FILTERS: { value: Filter; key: 'all' | IncidentStatus }[] = [
  { value: null, key: 'all' },
  { value: 'open', key: 'open' },
  { value: 'resolved', key: 'resolved' },
]

/**
 * `/incidents`: past incidents, newest first, with a status filter. On desktop the list sits
 * beside a map of the loaded page's located incidents (no geo-bounds filter, ADR 0005).
 */
export function History() {
  const { t, i18n } = useTranslation()
  const desktop = useDesktop()
  const [status, setStatus] = useState<Filter>(null)
  // The incident picked on the map, or pointed at in the list: highlighted in both.
  const [selected, setSelected] = useState<string | null>(null)
  const incidents = useIncidents(status)
  const vehicles = useVehicles()
  // Offset paging can repeat a row when incidents change between pages: keep the first.
  const items = useMemo(() => {
    const seen = new Set<number>()
    return (incidents.data?.pages ?? [])
      .flatMap((page) => page.items)
      .filter((i) => !seen.has(i.id) && seen.add(i.id))
  }, [incidents.data])
  // Pins in list order, one per spot: incidents at the same coordinates share a pin, named
  // after the first of them and marked with their count. One without a location stays
  // list-only. `pinOf` maps each located incident to its pin.
  const { pins, pinOf } = useMemo(() => {
    const pins: Pin[] = []
    const atSpot = new Map<string, Pin>()
    const pinOf = new Map<string, string>()
    for (const i of items) {
      if (!i.location) continue
      const { lat, lon } = i.location
      const spot = `${lat.toFixed(6)},${lon.toFixed(6)}`
      let pin = atSpot.get(spot)
      if (!pin) {
        pin = { id: String(i.id), lat, lon, count: 0 }
        atSpot.set(spot, pin)
        pins.push(pin)
      }
      pin.count = (pin.count ?? 0) + 1
      pinOf.set(String(i.id), pin.id)
    }
    return { pins, pinOf }
  }, [items])
  const pinNumber = useMemo(() => new Map(pins.map((p, n) => [p.id, n + 1])), [pins])
  // A pointed-at row selects its pin, and with it every incident at that spot.
  const point = (id: string) => {
    setSelected(pinOf.get(id) ?? id)
  }
  const vehicleById = useMemo(
    () => new Map((vehicles.data ?? []).map((v) => [v.id, v])),
    [vehicles.data],
  )
  const formatDate = useMemo(
    () => new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium', timeStyle: 'short' }),
    [i18n.language],
  )
  const total = incidents.data?.pages[0]?.total

  const empty =
    status === 'open'
      ? t('history.emptyOpen')
      : status === 'resolved'
        ? t('history.emptyResolved')
        : t('history.empty')

  const list = (
    <>
      <div className="history-controls">
        <div className="history-head">
          <h1>{t('history.heading')}</h1>
          {total !== undefined && total > 0 && (
            <p className="muted">{t('history.count', { count: total })}</p>
          )}
        </div>

        <div className="segmented" role="group" aria-label={t('history.filterLabel')}>
          {FILTERS.map(({ value, key }) => (
            <button
              key={key}
              type="button"
              aria-pressed={status === value}
              onClick={() => {
                setStatus(value)
              }}
            >
              {t(`history.filters.${key}`)}
            </button>
          ))}
        </div>
      </div>

      {incidents.isPending && <p className="muted">{t('common.loading')}</p>}
      {/* A failed Show more keeps the loaded list; only a failed first load is an alert. */}
      {incidents.isError && !incidents.data && (
        <>
          <p className="notice notice-error" role="alert">
            {t('history.loadFailed')}
          </p>
          <ErrorNotice error={incidents.error} />
        </>
      )}

      {incidents.isSuccess && items.length === 0 && <p className="notice">{empty}</p>}
      {items.length > 0 && (
        <ul className="incident-list" aria-label={t('history.listLabel')}>
          {items.map((incident) => {
            const id = String(incident.id)
            const pinId = pinOf.get(id)
            return (
              <IncidentRow
                key={incident.id}
                incident={incident}
                vehicle={
                  incident.vehicle_id === null
                    ? null
                    : (vehicleById.get(incident.vehicle_id) ?? null)
                }
                formatDate={formatDate}
                {...(desktop && {
                  pin: pinId === undefined ? undefined : pinNumber.get(pinId),
                  selected: selected !== null && (pinId ?? id) === selected,
                  // Of a shared spot, only the first row scrolls into view.
                  lead: pinId === undefined || pinId === id,
                  onPoint: point,
                })}
              />
            )
          })}
        </ul>
      )}

      {incidents.isFetchNextPageError && <ErrorNotice error={incidents.error} />}
      {incidents.hasNextPage && (
        <button
          type="button"
          className="btn btn-quiet"
          disabled={incidents.isFetchingNextPage}
          onClick={() => void incidents.fetchNextPage()}
        >
          {incidents.isFetchingNextPage ? t('common.loading') : t('history.more')}
        </button>
      )}
    </>
  )

  if (!desktop) return list
  return (
    <div className="history-split">
      <div className="history-list">{list}</div>
      <div className="history-map">
        <PlacesMap
          pins={pins}
          selected={selected}
          onSelect={setSelected}
          label={t('history.mapLabel')}
          attribution={t('nearby.attribution')}
          zoomControl
        />
      </div>
    </div>
  )
}

function IncidentRow({
  incident,
  vehicle,
  formatDate,
  pin,
  selected = false,
  lead = true,
  onPoint,
}: {
  incident: IncidentSummary
  vehicle: VehicleRead | null
  formatDate: Intl.DateTimeFormat
  /** Desktop: the number of this incident's pin on the map, when it has a location. */
  pin?: number | undefined
  /** Desktop: highlighted, as its pin is. */
  selected?: boolean
  /** Desktop: the row that scrolls into view when its pin is picked. */
  lead?: boolean
  /** Desktop: pointing at or focusing the row highlights its pin. */
  onPoint?: (id: string) => void
}) {
  const { t } = useTranslation()
  const row = useRef<HTMLAnchorElement>(null)
  // A pin picked on the map brings its row into view.
  useEffect(() => {
    if (selected && lead) row.current?.scrollIntoView({ block: 'nearest' })
  }, [selected, lead])
  const key = problemKey(incident.problem_type, vehicle?.fuel_type)
  const Icon = TILE_ICONS[key]
  const resolved = incident.status === 'resolved'
  const when = formatDate.format(new Date(incident.created_at))
  const place =
    incident.location_label ?? (incident.location ? formatCoords(incident.location) : null)

  return (
    <li>
      <Link
        ref={row}
        className={selected ? 'incident-row incident-row-selected' : 'incident-row'}
        to={`/incidents/${String(incident.id)}`}
        {...(onPoint && {
          onMouseEnter: () => {
            onPoint(String(incident.id))
          },
          onFocus: () => {
            onPoint(String(incident.id))
          },
        })}
      >
        <span className="incident-icon" aria-hidden="true">
          <Icon size={24} strokeWidth={1.75} />
        </span>
        <span className="incident-body">
          <span className="incident-top">
            <h2>{t(`start.tiles.${key}`)}</h2>
            <span className={resolved ? 'badge' : 'badge badge-strong'}>
              {resolved ? t('incident.resolved') : t('incident.open')}
            </span>
          </span>
          {incident.damage_report_status && (
            <span className="badge incident-report">
              {t(`history.reportChip.${incident.damage_report_status}`)}
            </span>
          )}
          <time className="muted" dateTime={incident.created_at}>
            {when}
          </time>
          {(vehicle || place) && (
            <span className="incident-meta">
              {vehicle && (
                <span>
                  <Car size={16} aria-hidden="true" />
                  {vehicle.name}
                </span>
              )}
              {place && (
                <span>
                  {pin === undefined ? (
                    <MapPin size={16} aria-hidden="true" />
                  ) : (
                    <span className="pin-ref" aria-hidden="true">
                      {pin}
                    </span>
                  )}
                  {place}
                </span>
              )}
            </span>
          )}
        </span>
        <ChevronRight className="incident-chevron" size={20} aria-hidden="true" />
      </Link>
    </li>
  )
}
