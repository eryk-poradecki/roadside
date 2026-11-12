import { useMemo } from 'react'
import { encode } from 'uqr'

/** The quiet zone scanners need around the code, in modules. */
const QUIET = 4

/**
 * A QR code for `value`, drawn in the browser as one SVG path: dark modules on a light plate
 * with its quiet zone, the contrast a phone camera expects (ADR 0012).
 */
export function QrCode({ value, label }: { value: string; label: string }) {
  const { size, path } = useMemo(() => {
    const qr = encode(value, { ecc: 'M', border: QUIET })
    const d = qr.data.flatMap((row, y) =>
      row.flatMap((dark, x) => (dark ? [`M${String(x)} ${String(y)}h1v1h-1z`] : [])),
    )
    return { size: qr.size, path: d.join('') }
  }, [value])

  return (
    <svg
      className="qr"
      role="img"
      aria-label={label}
      viewBox={`0 0 ${String(size)} ${String(size)}`}
      shapeRendering="crispEdges"
    >
      <rect className="qr-plate" width={size} height={size} />
      <path className="qr-modules" d={path} />
    </svg>
  )
}
