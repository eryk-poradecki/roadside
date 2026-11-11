import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useEffect, useRef } from 'react'
import './map.css'

/** The one module that imports Leaflet (ADR 0008). */

export const OSM_COPYRIGHT_URL = 'https://www.openstreetmap.org/copyright'
const DEFAULT_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'

/** `VITE_TILE_URL`, so the tile server can change without a code edit (OSM tile policy). */
const tileUrl = (): string => {
  const value: unknown = import.meta.env.VITE_TILE_URL
  return typeof value === 'string' && value !== '' ? value : DEFAULT_TILE_URL
}

export type MapPin = { id: string; lat: number; lon: number }

type Props = {
  pins: MapPin[]
  /** The driver's location. */
  user: { lat: number; lon: number }
  selected?: string | null
  onSelect?: (id: string) => void
  /** Accessible name of the map image. */
  label: string
  /** Translated "© OpenStreetMap contributors". */
  attribution: string
  /** False on the preview: no panning or zooming under the "Open map" cover. */
  interactive?: boolean
  /** False when the caller renders the attribution itself, above a sheet that covers the corner. */
  showAttribution?: boolean
  /** Pixels at the bottom covered by a sheet, so framing keeps the pins above it. */
  padBottom?: number
}

const escapeHtml = (s: string) => s.replace(/[&<>"']/g, (c) => `&#${String(c.charCodeAt(0))};`)

const pinIcon = (n: number, active: boolean) =>
  L.divIcon({
    className: '',
    html: `<span class="pin${active ? ' pin-active' : ''}">${String(n)}</span>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  })

const youIcon = () =>
  L.divIcon({
    className: '',
    html: '<span class="you-dot"></span>',
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  })

/**
 * Standard OSM tiles, darkened by a CSS filter on the tile pane only, with numbered pins in
 * list order and the driver's dot. The attribution is always fully visible.
 */
export function PlacesMap({
  pins,
  user,
  selected = null,
  onSelect,
  label,
  attribution,
  interactive = true,
  showAttribution = true,
  padBottom = 0,
}: Props) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const layer = useRef<L.LayerGroup | null>(null)
  const select = useRef(onSelect)
  const fit = useRef<() => void>(() => undefined)

  useEffect(() => {
    select.current = onSelect
    fit.current = () => {
      const points: L.LatLngTuple[] = [
        [user.lat, user.lon],
        ...pins.map((p): L.LatLngTuple => [p.lat, p.lon]),
      ]
      map.current?.fitBounds(L.latLngBounds(points), {
        paddingTopLeft: [28, padBottom ? 72 : 24],
        paddingBottomRight: [28, 24 + padBottom],
        maxZoom: 16,
        animate: false,
      })
    }
  })

  useEffect(() => {
    if (!el.current) return
    const m = L.map(el.current, {
      zoomControl: false,
      attributionControl: showAttribution,
      dragging: interactive,
      touchZoom: interactive,
      doubleClickZoom: interactive,
      scrollWheelZoom: false,
      boxZoom: false,
      keyboard: false,
    })
    // Leaflet leaves `attributionControl` undefined when it is turned off (the full map).
    if (showAttribution) m.attributionControl.setPrefix(false)
    L.tileLayer(tileUrl(), {
      maxZoom: 19,
      attribution: `<a href="${OSM_COPYRIGHT_URL}" target="_blank" rel="noopener">${escapeHtml(attribution)}</a>`,
    }).addTo(m)
    L.marker([user.lat, user.lon], { icon: youIcon(), interactive: false, keyboard: false }).addTo(
      m,
    )
    layer.current = L.layerGroup().addTo(m)
    map.current = m
    const resize = new ResizeObserver(() => {
      m.invalidateSize()
      fit.current()
    })
    resize.observe(el.current)
    return () => {
      resize.disconnect()
      m.remove()
      map.current = null
      layer.current = null
    }
  }, [interactive, attribution, showAttribution, user.lat, user.lon])

  // Pins, in list order. Also after the map above is rebuilt with an empty layer.
  useEffect(() => {
    const group = layer.current
    if (!group) return
    group.clearLayers()
    pins.forEach((p, i) => {
      const active = p.id === selected
      const marker = L.marker([p.lat, p.lon], {
        icon: pinIcon(i + 1, active),
        keyboard: false,
        interactive: interactive && onSelect !== undefined,
        zIndexOffset: active ? 1000 : 0,
      })
      marker.on('click', () => select.current?.(p.id))
      marker.addTo(group)
    })
  }, [pins, selected, interactive, onSelect, attribution, showAttribution, user.lat, user.lon])

  // Frame the driver and every pin.
  useEffect(() => {
    fit.current()
  }, [pins, user.lat, user.lon, padBottom, interactive])

  // Keep the chosen place in view.
  useEffect(() => {
    const m = map.current
    const p = pins.find((x) => x.id === selected)
    if (m && p && !m.getBounds().pad(-0.1).contains([p.lat, p.lon])) m.panTo([p.lat, p.lon])
  }, [selected, pins])

  return <div ref={el} className="places-map" role="img" aria-label={label} />
}
