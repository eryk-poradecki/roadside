import type { FuelType, NearbyCategory, PlaceRead, ProblemType } from '../api/generated/types.gen'

export type { NearbyCategory }

/** The chips, in display order. */
export const ALL_CATEGORIES: NearbyCategory[] = ['tyres', 'fuel', 'charging', 'repair']

export type SimpleHours = { kind: 'always' } | { kind: 'daily'; open: string; close: string }

/**
 * The prototype's rule for raw OSM `opening_hours`: only `24/7` and the same hours every day
 * are shown. Anything else would need a full parser to read right, so it is not shown at all.
 */
export function simpleHours(raw: string | null): SimpleHours | null {
  const value = raw?.trim() ?? ''
  if (value === '24/7') return { kind: 'always' }
  const daily = /^Mo-Su (\d{2}:\d{2})-(\d{2}:\d{2})$/.exec(value)
  if (daily?.[1] && daily[2]) return { kind: 'daily', open: daily[1], close: daily[2] }
  return null
}

const BY_PROBLEM: Record<ProblemType, NearbyCategory[]> = {
  flat_tyre: ['tyres'],
  pothole_damage: ['tyres'],
  out_of_fuel: ['fuel'],
  flat_battery: ['repair'],
  other: ALL_CATEGORIES,
}

/**
 * The chips selected before the driver touches them (ADR 0004): the problem type's category
 * (charging for an electric vehicle out of charge), plus the advice's `extra_categories`,
 * which can only add chips.
 */
export function preselectedCategories(
  problem: ProblemType,
  fuelType: FuelType | null | undefined,
  extra: NearbyCategory[],
): NearbyCategory[] {
  const base =
    problem === 'out_of_fuel' && fuelType === 'electric'
      ? (['charging'] as NearbyCategory[])
      : BY_PROBLEM[problem]
  const chosen = new Set([...base, ...extra])
  return ALL_CATEGORIES.filter((c) => chosen.has(c))
}

export const isAll = (selected: NearbyCategory[]) =>
  ALL_CATEGORIES.every((c) => selected.includes(c))

/** Tapping a chip: from "all" it narrows to that chip; otherwise it adds or removes it. */
export function toggleCategory(
  selected: NearbyCategory[],
  category: NearbyCategory,
): NearbyCategory[] {
  if (isAll(selected)) return [category]
  const next = selected.includes(category)
    ? selected.filter((c) => c !== category)
    : [...selected, category]
  return next.length === 0 ? ALL_CATEGORIES : ALL_CATEGORIES.filter((c) => next.includes(c))
}

/** The places of the selected categories, still nearest first. */
export const filterPlaces = (places: PlaceRead[], selected: NearbyCategory[]) =>
  places.filter((p) => selected.includes(p.category))
