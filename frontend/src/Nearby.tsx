import { useEffect, useMemo, useRef, useState } from 'react'
import { Fuel, Loader, Map as MapIcon, MapPinOff, Navigation, Phone, RotateCw, Wrench, X } from 'lucide-react'
import { useLang, useT, type TileId } from './i18n'
import { MiniMap } from './MiniMap'
import { MOCK_MAP_OPEN, MOCK_PLACES, PLACES_DELAY_MS } from './mock'
import { DEFAULT_FILTER, PLACES, simpleHours, USER_POS, type Place, type PlaceCat } from './mockAi'
import { TyreIcon } from './icons'

type Phase = 'searching' | 'found' | 'none' | 'unavailable' | 'noloc'
type Filter = 'all' | PlaceCat

const CAT_ICON = { tyres: TyreIcon, fuel: Fuel, repair: Wrench }
const CATS: PlaceCat[] = ['tyres', 'fuel', 'repair']

function usePlaces() {
  const initial: Phase = MOCK_PLACES ?? 'searching'
  const [phase, setPhase] = useState<Phase>(initial)
  const [run, setRun] = useState(0)
  useEffect(() => {
    if (phase !== 'searching' || MOCK_PLACES === 'searching') return
    const id = window.setTimeout(() => setPhase('found'), PLACES_DELAY_MS)
    return () => window.clearTimeout(id)
  }, [phase, run])
  const research = () => {
    setPhase('searching')
    setRun((n) => n + 1)
  }
  return { phase, research }
}

const PREVIEW_ROWS = 3

export function Nearby({ tile }: { tile: TileId }) {
  const t = useT().nearby
  const { phase, research } = usePlaces()
  const [filter, setFilter] = useState<Filter>(DEFAULT_FILTER[tile])
  const [selected, setSelected] = useState<string | null>(null)
  const [mapOpen, setMapOpen] = useState(MOCK_MAP_OPEN && MOCK_PLACES === 'found')

  const places = useMemo(() => (filter === 'all' ? PLACES : PLACES.filter((p) => p.cat === filter)), [filter])
  const counts = useMemo(() => Object.fromEntries(CATS.map((c) => [c, PLACES.filter((p) => p.cat === c).length])), [])

  return (
    <section className="panel panel-osm" aria-labelledby="nb-title">
      <div className="panel-head">
        <h2 id="nb-title">{t.title}</h2>
        <span className="badge">
          <MapIcon size={14} aria-hidden="true" />
          {t.badge}
        </span>
      </div>

      <div aria-live="polite">
        {phase === 'searching' && (
          <div className="nb-state">
            <p className="ai-line">
              <Loader size={20} className="spin" aria-hidden="true" />
              {t.searching}
            </p>
            <p className="muted">{t.searchingSub}</p>
            <div className="skeleton skeleton-rows" aria-hidden="true">
              <i />
              <i />
              <i />
            </div>
          </div>
        )}
        {phase === 'none' && (
          <div className="nb-state">
            <p className="ai-line">
              <MapPinOff size={20} aria-hidden="true" />
              {t.none}
            </p>
            <button type="button" className="btn btn-quiet" onClick={research}>
              {t.widen}
            </button>
          </div>
        )}
        {phase === 'unavailable' && (
          <div className="nb-state">
            <p className="ai-line">
              <MapPinOff size={20} aria-hidden="true" />
              <strong>{t.unavailable}</strong>
            </p>
            <p className="muted">{t.unavailableSub}</p>
            <button type="button" className="btn btn-quiet" onClick={research}>
              <RotateCw size={18} aria-hidden="true" />
              {t.retry}
            </button>
          </div>
        )}
        {phase === 'noloc' && (
          <div className="nb-state">
            <p className="ai-line">
              <MapPinOff size={20} aria-hidden="true" />
              {t.noloc}
            </p>
            <button type="button" className="btn btn-quiet">
              {t.setLoc}
            </button>
          </div>
        )}
      </div>

      {phase === 'found' && (
        <>
          <Chips filter={filter} counts={counts} onFilter={(f) => { setFilter(f); setSelected(null) }} />

          <div className="minimap-frame">
            <MiniMap places={places} user={USER_POS} selected={null} onSelect={() => setMapOpen(true)} label={t.mapLabel} attribution={t.attribution} interactive={false} />
            <button type="button" className="minimap-cover" onClick={() => setMapOpen(true)} aria-label={t.openMap}>
              <span className="minimap-open" aria-hidden="true">
                <MapIcon size={18} />
                {t.openMap}
              </span>
            </button>
          </div>

          <PlaceList places={places.slice(0, PREVIEW_ROWS)} selected={null} onSelect={(id) => { setSelected(id); setMapOpen(true) }} />
          <button type="button" className="btn btn-quiet btn-block" onClick={() => { setFilter('all'); setSelected(null); setMapOpen(true) }}>
            <MapIcon size={18} aria-hidden="true" />
            {t.showAll(PLACES.length)}
          </button>
          <p className="placeholder-note">{t.sample}</p>
        </>
      )}

      {mapOpen && (
        <FullMap
          places={places}
          filter={filter}
          counts={counts}
          onFilter={(f) => { setFilter(f); setSelected(null) }}
          selected={selected}
          onSelect={setSelected}
          onClose={() => setMapOpen(false)}
        />
      )}
    </section>
  )
}

function Chips({ filter, counts, onFilter }: { filter: Filter; counts: Record<string, number>; onFilter: (f: Filter) => void }) {
  const t = useT().nearby
  return (
    <div className="chips" role="group" aria-label={t.title}>
      {(['all', ...CATS] as Filter[]).map((f) => (
        <button key={f} type="button" className="chip" aria-pressed={filter === f} onClick={() => onFilter(f)}>
          {f === 'all' ? t.all : t.chips[f]}
          {f !== 'all' && <span className="chip-count">{counts[f]}</span>}
        </button>
      ))}
    </div>
  )
}

function PlaceList({ places, selected, onSelect }: { places: Place[]; selected: string | null; onSelect: (id: string) => void }) {
  const t = useT().nearby
  const lang = useLang()
  const km = new Intl.NumberFormat(lang, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
  const rowRefs = useRef<Record<string, HTMLLIElement | null>>({})

  useEffect(() => {
    if (selected) rowRefs.current[selected]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [selected])

  return (
    <ol className="places">
      {places.map((p, i) => {
        const Icon = CAT_ICON[p.cat]
        const name = p.name ?? t.cat[p.cat]
        return (
          <li key={p.id} ref={(n) => { rowRefs.current[p.id] = n }} className={p.id === selected ? 'place place-active' : 'place'}>
            <button type="button" className="place-main" onClick={() => onSelect(p.id)} aria-pressed={p.id === selected}>
              <span className="pin pin-static" aria-hidden="true">{i + 1}</span>
              <span className="place-text">
                <strong>{name}</strong>
                <span className="place-meta">
                  <Icon size={15} aria-hidden="true" />
                  <span className="place-dist">{km.format(p.distanceKm)} km</span>
                  {[p.name ? t.cat[p.cat] : null, simpleHours(p.openingHours, lang)].filter(Boolean).map((x) => (
                    <span key={x}>· {x}</span>
                  ))}
                </span>
              </span>
            </button>
            <div className="place-actions">
              <a className="icon-btn" href={`geo:${p.lat},${p.lon}?q=${p.lat},${p.lon}`} aria-label={`${t.navigate} ${name}`}>
                <Navigation size={20} aria-hidden="true" />
              </a>
              {p.phone && (
                <a className="icon-btn" href={`tel:${p.phone}`} aria-label={`${t.call} ${name}`}>
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

type FullMapProps = {
  places: Place[]
  filter: Filter
  counts: Record<string, number>
  onFilter: (f: Filter) => void
  selected: string | null
  onSelect: (id: string) => void
  onClose: () => void
}

/** Alternative layout: the map fills the screen, places sit in a sheet over its lower half. */
function FullMap({ places, filter, counts, onFilter, selected, onSelect, onClose }: FullMapProps) {
  const t = useT().nearby
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    ref.current?.showModal()
  }, [])
  return (
    <dialog ref={ref} className="fullmap" onClose={onClose} aria-label={t.mapLabel}>
      <div className="fullmap-map">
        <MiniMap places={places} user={USER_POS} selected={selected} onSelect={onSelect} label={t.mapLabel} attribution={t.attribution} padBottom={window.innerHeight * 0.46} showAttribution={false} />
      </div>
      <button type="button" className="icon-btn fullmap-close" onClick={() => ref.current?.close()} aria-label={t.closeMap}>
        <X size={22} aria-hidden="true" />
      </button>
      <div className="fullmap-sheet">
        <a className="fullmap-attr" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
          {t.attribution}
        </a>
        <span className="sheet-handle" aria-hidden="true" />
        <Chips filter={filter} counts={counts} onFilter={onFilter} />
        <div className="fullmap-list">
          <PlaceList places={places} selected={selected} onSelect={onSelect} />
          <p className="placeholder-note">{t.sample}</p>
        </div>
      </div>
    </dialog>
  )
}
