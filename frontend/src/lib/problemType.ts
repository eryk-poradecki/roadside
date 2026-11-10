import type { FuelType, ProblemType } from '../api/generated/types.gen'

export type { ProblemType }

/** The Start screen's quick picks, in display order. */
export const PROBLEM_TYPES: ProblemType[] = [
  'flat_tyre',
  'flat_battery',
  'out_of_fuel',
  'pothole_damage',
  'other',
]

/** The copy key for a problem type: its label and its safety checklist (ADR 0010). */
export type ProblemKey = 'tyre' | 'battery' | 'fuel' | 'charge' | 'pothole' | 'other'

const KEYS: Record<ProblemType, ProblemKey> = {
  flat_tyre: 'tyre',
  flat_battery: 'battery',
  out_of_fuel: 'fuel',
  pothole_damage: 'pothole',
  other: 'other',
}

/**
 * Out of fuel reads "Out of charge", with its own checklist, for an electric vehicle.
 * The Start tile passes the default vehicle's fuel type; the sheet and the Result screen
 * pass the incident's vehicle (ADR 0003).
 */
export function problemKey(type: ProblemType, fuelType?: FuelType | null): ProblemKey {
  if (type === 'out_of_fuel' && fuelType === 'electric') return 'charge'
  return KEYS[type]
}
