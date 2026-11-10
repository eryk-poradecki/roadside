import { CircleEllipsis, Fuel } from 'lucide-react'
import type { TileId } from './i18n'
import { CarBatteryIcon, PotholeIcon, TyreIcon } from './icons'

export const TILE_ORDER: TileId[] = ['tyre', 'battery', 'fuel', 'pothole', 'other']

export const TILE_ICONS = {
  tyre: TyreIcon,
  battery: CarBatteryIcon,
  fuel: Fuel,
  pothole: PotholeIcon,
  other: CircleEllipsis,
}
