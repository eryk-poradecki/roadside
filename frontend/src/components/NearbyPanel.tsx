import {
  Fuel,
  Loader,
  Map as MapIcon,
  MapPinOff,
  Navigation,
  Phone,
  PlugZap,
  RotateCw,
  Search,
  Store,
  Wrench,
  X,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { findAdvice } from '../api/aiTurns'
import { isApiError } from '../api/client'
import type { FuelType } from '../api/generated/types.gen'
import type { IncidentRead } from '../api/incidents'
import {
  claimNearbyAutoStart,
  FIRST_RADIUS_KM,
  nearbyAutoStartClaimed,
  useFindNearby,
  useNearbyInFlight,
  WIDE_RADIUS_KM,
  type NearbyCategory,
  type PlaceRead,
} from '../api/nearby'
import {
  ALL_CATEGORIES,
  filterPlaces,
  isAll,
  preselectedCategories,
  simpleHours,
  toggleCategory,
} from '../lib/nearby'
import { useErrorMessage } from './ErrorNotice'
import { TyreIcon } from './icons'
import { OSM_COPYRIGHT_URL, PlacesMap, type MapPin } from './map/PlacesMap'
import './NearbyPanel.css'

const CATEGORY_ICON = { tyres: TyreIcon, fuel: Fuel, charging: PlugZap, repair: Wrench }
const PREVIEW_ROWS = 3
const OSM_FIX_URL = 'https://www.openstreetmap.org/fixthemap'

const placeId = (p: PlaceRead) => `${p.osm_type}/${String(p.osm_id)}`

/**
 * Real places from OpenStreetMap, looked up by the server and labelled as map data. The
 * model never supplies one: this panel reads only `incident.nearby`, never an AI turn
 * (whose `extra_categories` only preselect chips). With a location and no places yet, an
 * open incident looks them up at once, in parallel with the AI turn.
 */
export function NearbyPanel({
  incident,
  fuelType,
}: {
  incident: IncidentRead
  fuelType: FuelType | null | undefined
}) {
  const { t } = useTranslation()
  const lookup = useFindNearby(incident.id)
  const inFlight = useNearbyInFlight(incident.id)
  const message = useErrorMessage()
  const snapshot = incident.nearby
  const location = incident.location
  const open = incident.status === 'open'
  // Not looked up yet, about to be: the searching state from the first paint.
  const starting =
    location !== null &&
    snapshot === null &&
    open &&
    lookup.isIdle &&
    !nearbyAutoStartClaimed(incident)
  // "Try again" repeats the radius that failed.
  const lastRadius = lookup.variables?.body.radius_km ?? FIRST_RADIUS_KM

  const find = (radiusKm: number) => {
    lookup.find(radiusKm).catch(() => {
      // Shown below from `lookup.error`.
    })
  }

  // Once per incident, location and session: not again after a remount or a reload.
  useEffect(() => {
    if (!location || snapshot || !open || inFlight || !claimNearbyAutoStart(incident)) return
    find(FIRST_RADIUS_KM)
  })

  const extra = findAdvice(incident)?.advice?.extra_categories
  const preselected = useMemo(
    () => preselectedCategories(incident.problem_type, fuelType, extra ?? []),
    [incident.problem_type, fuelType, extra],
  )
  // Until the driver taps a chip, the selection follows the problem type and the advice.
  const [chosen, setChosen] = useState<NearbyCategory[] | null>(null)
  const selected = chosen ?? preselected
  const [mapOpen, setMapOpen] = useState(false)
  const [focus, setFocus] = useState<string | null>(null)
  // The map unmounts without a close event when its places go (e.g. the location changed):
  // don't let it pop up again by itself with the next places.
  if (mapOpen && (!snapshot || !location)) setMapOpen(false)

  const failed = lookup.isError && !inFlight
  // Demo mode with no recorded places: trying again can't help.
  const notRecorded = isApiError(lookup.error) && lookup.error.reason === 'nearby_not_recorded'
  const searching = inFlight || starting

  return (
    <section className="panel nearby" aria-labelledby="nearby-title" aria-busy={searching}>
      <div className="panel-head">
        <h2 id="nearby-title">{t('nearby.title')}</h2>
        <span className="badge">
          <Store size={14} aria-hidden="true" />
          {t('nearby.badge')}
        </span>
      </div>

      <div className="nearby-state" aria-live="polite">
        {!location ? (
          <>
            <p className="ai-line">
              <MapPinOff size={20} aria-hidden="true" />
              {t('nearby.noLocation')}
            </p>
            <Link className="btn btn-quiet" to={`/incidents/${String(incident.id)}/edit`}>
              {t('nearby.setLocation')}
            </Link>
          </>
        ) : searching ? (
          <>
            <p className="ai-line">
              <Loader size={20} className="spin" aria-hidden="true" />
              {t('nearby.searching')}
            </p>
            <p className="muted">{t('nearby.searchingSub')}</p>
            {!snapshot && (
              <div className="skeleton skeleton-rows" aria-hidden="true">
                <i />
                <i />
                <i />
              </div>
            )}
          </>
        ) : failed ? (
          <div className="nearby-error" role="alert">
            <p className="ai-line">
              <MapPinOff size={20} aria-hidden="true" />
              <strong>{t('nearby.unavailable')}</strong>
            </p>
            <p className="muted">
              {message(lookup.error)} {!notRecorded && t('nearby.unavailableSub')}
              {snapshot && ` ${t('nearby.earlier')}`}
            </p>
            {!notRecorded && (
              <button
                type="button"
                className="btn btn-quiet"
                onClick={() => {
                  find(lastRadius)
                }}
              >
                <RotateCw size={18} aria-hidden="true" />
                {t('nearby.retry')}
              </button>
            )}
          </div>
        ) : !snapshot ? (
          // Resolved, or opened later after a lookup that never finished.
          <button
            type="button"
            className="btn btn-quiet"
            onClick={() => {
              find(FIRST_RADIUS_KM)
            }}
          >
            <Search size={18} aria-hidden="true" />
            {t('nearby.find')}
          </button>
        ) : snapshot.status === 'none' ? (
          <>
            <p className="ai-line">
              <MapPinOff size={20} aria-hidden="true" />
              {t('nearby.none', { radius: snapshot.radius_km })}
            </p>
            {snapshot.radius_km < WIDE_RADIUS_KM && (
              <WidenButton
                onClick={() => {
                  find(WIDE_RADIUS_KM)
                }}
              />
            )}
          </>
        ) : null}
      </div>

      {location && snapshot?.status === 'found' && (
        <Found
          places={snapshot.places}
          radiusKm={snapshot.radius_km}
          user={location}
          selected={selected}
          onSelect={setChosen}
          busy={inFlight}
          onWiden={() => {
            find(WIDE_RADIUS_KM)
          }}
          onOpenMap={(id) => {
            setFocus(id)
            setMapOpen(true)
          }}
        />
      )}

      {mapOpen && location && snapshot && (
        <FullMap
          places={snapshot.places}
          user={location}
          selected={selected}
          onSelect={setChosen}
          focus={focus}
          onFocus={setFocus}
          onClose={() => {
            setMapOpen(false)
          }}
        />
      )}
    </section>
  )
}

function WidenButton({ onClick, disabled }: { onClick: () => void; disabled?: boolean }) {
  const { t } = useTranslation()
  return (
    <button type="button" className="btn btn-quiet" disabled={disabled} onClick={onClick}>
      <Search size={18} aria-hidden="true" />
      {t('nearby.widen')}
    </button>
  )
}

function Found({
  places,
  radiusKm,
  user,
  selected,
  onSelect,
  busy,
  onWiden,
  onOpenMap,
}: {
  places: PlaceRead[]
  radiusKm: number
  user: { lat: number; lon: number }
  selected: NearbyCategory[]
  onSelect: (c: NearbyCategory[]) => void
  busy: boolean
  onWiden: () => void
  onOpenMap: (focus: string | null) => void
}) {
  const { t } = useTranslation()
  const shown = useShown(places, selected)
  const pins = usePins(shown)

  return (
    <>
      <Chips places={places} selected={selected} onSelect={onSelect} />
      <p className="muted nearby-within">{t('nearby.within', { radius: radiusKm })}</p>
      {shown.length === 0 ? (
        <div className="nearby-state">
          <p className="ai-line">
            <MapPinOff size={20} aria-hidden="true" />
            {t('nearby.noneChosen', { radius: radiusKm })}
          </p>
          {radiusKm < WIDE_RADIUS_KM && <WidenButton onClick={onWiden} disabled={busy} />}
        </div>
      ) : (
        <>
          <div className="map-preview">
            <PlacesMap
              pins={pins}
              user={user}
              label={t('nearby.mapLabel')}
              attribution={t('nearby.attribution')}
              interactive={false}
            />
            <button
              type="button"
              className="map-preview-cover"
              onClick={() => {
                onOpenMap(null)
              }}
            >
              <span className="map-preview-open">
                <MapIcon size={18} aria-hidden="true" />
                {t('nearby.openMap')}
              </span>
            </button>
          </div>
          <PlaceList
            places={shown.slice(0, PREVIEW_ROWS)}
            focus={null}
            onFocus={(id) => {
              onOpenMap(id)
            }}
          />
          {shown.length > PREVIEW_ROWS && (
            <button
              type="button"
              className="btn btn-quiet btn-block"
              onClick={() => {
                onOpenMap(null)
              }}
            >
              <MapIcon size={18} aria-hidden="true" />
              {t('nearby.showAll')}
            </button>
          )}
        </>
      )}
    </>
  )
}

/** Stable between renders, so the map keeps the driver's pan and zoom. */
const useShown = (places: PlaceRead[], selected: NearbyCategory[]) =>
  useMemo(() => filterPlaces(places, selected), [places, selected])

const usePins = (places: PlaceRead[]): MapPin[] =>
  useMemo(() => places.map((p) => ({ id: placeId(p), lat: p.lat, lon: p.lon })), [places])

/** "All" plus one chip per category that has places or is selected. Filtering is local. */
function Chips({
  places,
  selected,
  onSelect,
}: {
  places: PlaceRead[]
  selected: NearbyCategory[]
  onSelect: (c: NearbyCategory[]) => void
}) {
  const { t } = useTranslation()
  const counts = new Map<NearbyCategory, number>()
  for (const p of places) counts.set(p.category, (counts.get(p.category) ?? 0) + 1)
  const all = isAll(selected)
  const chips = ALL_CATEGORIES.filter((c) => counts.has(c) || (!all && selected.includes(c)))
  return (
    <div className="chips" role="group" aria-label={t('nearby.chipsLabel')}>
      <button
        type="button"
        className="chip"
        aria-pressed={all}
        onClick={() => {
          onSelect(ALL_CATEGORIES)
        }}
      >
        {t('nearby.all')}
        <span className="chip-count">{places.length}</span>
      </button>
      {chips.map((c) => (
        <button
          key={c}
          type="button"
          className="chip"
          aria-pressed={!all && selected.includes(c)}
          onClick={() => {
            onSelect(toggleCategory(selected, c))
          }}
        >
          {t(`nearby.chips.${c}`)}
          <span className="chip-count">{counts.get(c) ?? 0}</span>
        </button>
      ))}
    </div>
  )
}

function useDistance() {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage ?? 'en'
  return (metres: number) =>
    metres < 1000
      ? t('nearby.metres', { distance: new Intl.NumberFormat(lang).format(metres) })
      : t('nearby.kilometres', {
          distance: new Intl.NumberFormat(lang, {
            minimumFractionDigits: 1,
            maximumFractionDigits: 1,
          }).format(metres / 1000),
        })
}

function PlaceList({
  places,
  focus,
  onFocus,
}: {
  places: PlaceRead[]
  focus: string | null
  onFocus: (id: string) => void
}) {
  const { t } = useTranslation()
  const distance = useDistance()
  const rows = useRef<Record<string, HTMLLIElement | null>>({})

  useEffect(() => {
    if (focus) rows.current[focus]?.scrollIntoView({ block: 'nearest' })
  }, [focus])

  return (
    <ol className="places" aria-label={t('nearby.listLabel')}>
      {places.map((p, i) => {
        const id = placeId(p)
        const Icon = CATEGORY_ICON[p.category]
        const kind = t(`nearby.category.${p.category}`)
        const name = p.name ?? kind
        const hours = simpleHours(p.opening_hours)
        const phone = (p.phone ?? '').replace(/[^\d+]/g, '')
        return (
          <li
            key={id}
            ref={(node) => {
              rows.current[id] = node
            }}
            className={id === focus ? 'place place-active' : 'place'}
          >
            <button
              type="button"
              className="place-main"
              aria-pressed={id === focus}
              onClick={() => {
                onFocus(id)
              }}
            >
              <span className="pin pin-static" aria-hidden="true">
                {i + 1}
              </span>
              <span className="place-text">
                <strong>{name}</strong>
                <span className="place-meta">
                  <Icon size={15} aria-hidden="true" />
                  <span className="place-dist">{distance(p.distance_m)}</span>
                  {p.name && <span>· {kind}</span>}
                  {hours && (
                    <span>
                      ·{' '}
                      {hours.kind === 'always'
                        ? t('nearby.hoursAlways')
                        : t('nearby.hoursDaily', { open: hours.open, close: hours.close })}
                    </span>
                  )}
                </span>
              </span>
            </button>
            <div className="place-actions">
              <a
                className="icon-btn"
                href={`https://www.google.com/maps/dir/?api=1&destination=${String(p.lat)},${String(p.lon)}`}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={t('nearby.directions', { name })}
              >
                <Navigation size={20} aria-hidden="true" />
              </a>
              {/\d/.test(phone) && (
                <a
                  className="icon-btn"
                  href={`tel:${phone}`}
                  aria-label={t('nearby.call', { name })}
                >
                  <Phone size={20} aria-hidden="true" />
                </a>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

/** The map fills the screen; the list sits in a sheet over its lower part. */
function FullMap({
  places,
  user,
  selected,
  onSelect,
  focus,
  onFocus,
  onClose,
}: {
  places: PlaceRead[]
  user: { lat: number; lon: number }
  selected: NearbyCategory[]
  onSelect: (c: NearbyCategory[]) => void
  focus: string | null
  onFocus: (id: string | null) => void
  onClose: () => void
}) {
  const { t } = useTranslation()
  const ref = useRef<HTMLDialogElement>(null)
  const shown = useShown(places, selected)
  const pins = usePins(shown)
  const sheetHeight = typeof window === 'undefined' ? 0 : window.innerHeight * 0.46

  useEffect(() => {
    ref.current?.showModal()
  }, [])

  return (
    <dialog ref={ref} className="fullmap" onClose={onClose} aria-label={t('nearby.mapLabel')}>
      <div className="fullmap-map">
        <PlacesMap
          pins={pins}
          user={user}
          selected={focus}
          onSelect={onFocus}
          label={t('nearby.mapLabel')}
          attribution={t('nearby.attribution')}
          padBottom={sheetHeight}
          showAttribution={false}
        />
      </div>
      <button
        type="button"
        className="icon-btn fullmap-close"
        onClick={() => ref.current?.close()}
        aria-label={t('nearby.closeMap')}
      >
        <X size={22} aria-hidden="true" />
      </button>
      <div className="fullmap-sheet">
        {/* On the sheet's top edge, so the sheet can never cover it (ADR 0008). */}
        <p className="fullmap-attr">
          <a href={OSM_COPYRIGHT_URL} target="_blank" rel="noopener">
            {t('nearby.attribution')}
          </a>
          <span aria-hidden="true"> · </span>
          <a href={OSM_FIX_URL} target="_blank" rel="noopener">
            {t('nearby.reportIssue')}
          </a>
        </p>
        <span className="sheet-handle" aria-hidden="true" />
        <Chips
          places={places}
          selected={selected}
          onSelect={(c) => {
            onFocus(null)
            onSelect(c)
          }}
        />
        <div className="fullmap-list">
          <PlaceList places={shown} focus={focus} onFocus={onFocus} />
        </div>
      </div>
    </dialog>
  )
}
