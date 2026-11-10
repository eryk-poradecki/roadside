import type { SVGProps } from 'react'

type IconProps = { size?: number; strokeWidth?: number } & Omit<SVGProps<SVGSVGElement>, 'width' | 'height'>

function Base({ size = 24, strokeWidth = 2, children, ...rest }: IconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...rest}
    >
      {children}
    </svg>
  )
}

/** Wheel with tread blocks and a nail in the tyre: a puncture. */
export function TyreIcon(props: IconProps) {
  return (
    <Base {...props}>
      <circle cx="11.2" cy="12.8" r="8.4" />
      <circle cx="11.2" cy="12.8" r="3.6" />
      <path d="M16.65 15.06L18.04 15.63M13.46 18.25L14.03 19.64M8.94 18.25L8.37 19.64M5.75 15.06L4.36 15.63M5.75 10.54L4.36 9.97M8.94 7.35L8.37 5.96M13.46 7.35L14.03 5.96M16.65 10.54L18.04 9.97" />
      <path d="M17.4 6.6L21.6 2.4M20.2 1.2l3 3" />
    </Base>
  )
}

/** 12 V car battery: box, two terminals, + and −. */
export function CarBatteryIcon(props: IconProps) {
  return (
    <Base {...props}>
      <rect x="2.5" y="7" width="19" height="13" rx="2" />
      <path d="M6 7V4.5h3V7M15 7V4.5h3V7" />
      <path d="M6 13.5h3M7.5 12v3M15 13.5h3" />
    </Base>
  )
}

/** Road in perspective with a broken, cracked hole in the lane: a pothole. */
export function PotholeIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M3 20 8 4M21 20 16 4" />
      <path d="M12 4v2M12 8.2v1.4" />
      <path d="m8 16.2 1.6-2.5 2.2.6 1.8-1 2.3 1 .9 2-1.6 1.8-2.4-.3-1.4.6-2.4-.5z" />
      <path d="m9.6 13.7-.9-1.2M14.8 18l1 1.3M13.6 13.3l.6-1.3" />
    </Base>
  )
}

/** Wordmark glyph: a road centre line receding into the distance. */
export function RoadMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M6.8 22 17.2 22 16 17H8Z" />
      <path d="M9.2 14.8H14.8L14.2 11H9.8Z" />
      <path d="M10.5 8.8H13.5L13.1 6.2H10.9Z" />
      <path d="M11.4 4.5H12.6L12.45 3H11.55Z" />
    </svg>
  )
}
