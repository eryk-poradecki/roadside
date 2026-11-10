import { CircleEllipsis, Fuel, PlugZap } from 'lucide-react'
import type { ProblemKey } from '../lib/problemType'
import { CarBatteryIcon, PotholeIcon, TyreIcon } from './icons'

/** One icon per problem label; "Out of charge" gets a plug instead of the pump. */
export const TILE_ICONS: Record<ProblemKey, typeof Fuel | typeof TyreIcon> = {
  tyre: TyreIcon,
  battery: CarBatteryIcon,
  fuel: Fuel,
  charge: PlugZap,
  pothole: PotholeIcon,
  other: CircleEllipsis,
}
