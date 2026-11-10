import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { Place } from './mockAi'

type Props = {
  places: Place[]
  user: { lat: number; lon: number }
  selected: string | null
  onSelect: (id: string) => void
  label: string
  attribution: string
  /** extra bottom padding (px) when a sheet covers the lower part of the map */
  padBottom?: number
  interactive?: boolean
  /** false when the caller renders the OSM attribution itself (full map: the sheet covers the corner) */
  showAttribution?: boolean
}

const pinIcon = (n: number, active: boolean) =>
  L.divIcon({
    className: '',
    html: `<span class="pin${active ? ' pin-active' : ''}">${n}</span>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  })

const youIcon = L.divIcon({ className: '', html: '<span class="you-dot"></span>', iconSize: [22, 22], iconAnchor: [11, 11] })

/** Muted dark OSM map with numbered pins that match the list order. */
export function MiniMap({ places, user, selected, onSelect, label, attribution, padBottom = 0, interactive = true, showAttribution = true }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const layer = useRef<L.LayerGroup | null>(null)
  const select = useRef(onSelect)
  select.current = onSelect
  const fit = useRef<() => void>(() => {})
  fit.current = () => {
    const pts: L.LatLngTuple[] = [[user.lat, user.lon], ...places.map((p): L.LatLngTuple => [p.lat, p.lon])]
    map.current?.fitBounds(L.latLngBounds(pts), { paddingTopLeft: [28, padBottom ? 72 : 24], paddingBottomRight: [28, 24 + padBottom], maxZoom: 16, animate: false })
  }

  useEffect(() => {
    if (!el.current) return
    const m = L.map(el.current, {
      zoomControl: false,
      attributionControl: showAttribution,
      dragging: interactive,
      touchZoom: interactive,
      scrollWheelZoom: false,
      doubleClickZoom: interactive,
      keyboard: false,
    })
    m.attributionControl?.setPrefix(false)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution }).addTo(m)
    L.marker([user.lat, user.lon], { icon: youIcon, interactive: false, keyboard: false }).addTo(m)
    layer.current = L.layerGroup().addTo(m)
    map.current = m
    const ro = new ResizeObserver(() => {
      m.invalidateSize()
      fit.current()
    })
    ro.observe(el.current)
    return () => {
      ro.disconnect()
      m.remove()
      map.current = null
    }
  }, [interactive, attribution, showAttribution, user.lat, user.lon])

  // pins + framing
  useEffect(() => {
    const m = map.current
    const g = layer.current
    if (!m || !g) return
    g.clearLayers()
    places.forEach((p, i) => {
      L.marker([p.lat, p.lon], { icon: pinIcon(i + 1, p.id === selected), keyboard: false, zIndexOffset: p.id === selected ? 1000 : 0 })
        .on('click', () => select.current(p.id))
        .addTo(g)
    })
  }, [places, selected])

  // frame the driver and every pin
  useEffect(() => {
    fit.current()
  }, [places, user.lat, user.lon, padBottom, interactive])

  // keep the chosen place in view
  useEffect(() => {
    const p = places.find((x) => x.id === selected)
    if (p && map.current && !map.current.getBounds().pad(-0.1).contains([p.lat, p.lon])) map.current.panTo([p.lat, p.lon])
  }, [selected, places])

  return <div ref={el} className="minimap" role="img" aria-label={label} />
}
