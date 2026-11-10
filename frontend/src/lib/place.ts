/** Coordinates as the driver sees them when there is no place name: five decimals (~1 m). */
export function formatCoords(loc: { lat: number; lon: number }): string {
  return `${loc.lat.toFixed(5)}, ${loc.lon.toFixed(5)}`
}
