import { ChevronRight, Car, MapPin } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useIncidents, type IncidentStatus, type IncidentSummary } from '../api/incidents'
import { useVehicles, type VehicleRead } from '../api/vehicles'
import { ErrorNotice } from '../components/ErrorNotice'
import { TILE_ICONS } from '../components/tiles'
import { formatCoords } from '../lib/place'
import { problemKey } from '../lib/problemType'
import './History.css'

type Filter = IncidentStatus | null
const FILTERS: { value: Filter; key: 'all' | IncidentStatus }[] = [
  { value: null, key: 'all' },
  { value: 'open', key: 'open' },
  { value: 'resolved', key: 'resolved' },
]

/** `/incidents`: past incidents, newest first, with a status filter (mobile layout). */
export function History() {
  const { t, i18n } = useTranslation()
  const [status, setStatus] = useState<Filter>(null)
  const incidents = useIncidents(status)
  const vehicles = useVehicles()
  // Offset paging can repeat a row when incidents change between pages: keep the first.
  const items = useMemo(() => {
    const seen = new Set<number>()
    return (incidents.data?.pages ?? [])
      .flatMap((page) => page.items)
      .filter((i) => !seen.has(i.id) && seen.add(i.id))
  }, [incidents.data])
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

  return (
    <>
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
          {items.map((incident) => (
            <IncidentRow
              key={incident.id}
              incident={incident}
              vehicle={
                incident.vehicle_id === null ? null : (vehicleById.get(incident.vehicle_id) ?? null)
              }
              formatDate={formatDate}
            />
          ))}
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
}

function IncidentRow({
  incident,
  vehicle,
  formatDate,
}: {
  incident: IncidentSummary
  vehicle: VehicleRead | null
  formatDate: Intl.DateTimeFormat
}) {
  const { t } = useTranslation()
  const key = problemKey(incident.problem_type, vehicle?.fuel_type)
  const Icon = TILE_ICONS[key]
  const resolved = incident.status === 'resolved'
  const when = formatDate.format(new Date(incident.created_at))
  const place =
    incident.location_label ?? (incident.location ? formatCoords(incident.location) : null)

  return (
    <li>
      <Link className="incident-row" to={`/incidents/${String(incident.id)}`}>
        <span className="incident-icon" aria-hidden="true">
          <Icon size={24} strokeWidth={1.75} />
        </span>
        <span className="incident-body">
          <span className="incident-top">
            <h2>{t(`start.tiles.${key}`)}</h2>
            <span className={resolved ? 'badge' : 'badge badge-accent'}>
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
                  <MapPin size={16} aria-hidden="true" />
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
