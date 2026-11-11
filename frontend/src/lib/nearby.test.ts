import type { PlaceRead } from '../api/generated/types.gen'
import {
  ALL_CATEGORIES,
  filterPlaces,
  isAll,
  preselectedCategories,
  simpleHours,
  toggleCategory,
} from './nearby'

describe('simpleHours', () => {
  it('shows 24/7', () => {
    expect(simpleHours('24/7')).toEqual({ kind: 'always' })
    expect(simpleHours(' 24/7 ')).toEqual({ kind: 'always' })
  })

  it('shows the same hours every day', () => {
    expect(simpleHours('Mo-Su 06:00-22:00')).toEqual({
      kind: 'daily',
      open: '06:00',
      close: '22:00',
    })
  })

  it('hides anything else, which it could get wrong', () => {
    for (const raw of [
      null,
      '',
      'Mo-Fr 08:00-18:00; Sa 09:00-14:00',
      'Mo-Su 06:00-22:00; PH off',
      'Mo-Su 06:00-14:00,15:00-22:00',
      'Mo-Sa 06:00-22:00',
      'sunrise-sunset',
      '24/7 "on call"',
    ])
      expect(simpleHours(raw)).toBeNull()
  })
})

describe('preselectedCategories', () => {
  it('follows the problem type', () => {
    expect(preselectedCategories('flat_tyre', null, [])).toEqual(['tyres'])
    expect(preselectedCategories('pothole_damage', null, [])).toEqual(['tyres'])
    expect(preselectedCategories('out_of_fuel', 'diesel', [])).toEqual(['fuel'])
    expect(preselectedCategories('flat_battery', 'electric', [])).toEqual(['repair'])
    expect(preselectedCategories('other', null, [])).toEqual(ALL_CATEGORIES)
  })

  it('preselects charging for an electric vehicle out of charge', () => {
    expect(preselectedCategories('out_of_fuel', 'electric', [])).toEqual(['charging'])
    expect(preselectedCategories('out_of_fuel', 'plug_in_hybrid', [])).toEqual(['fuel'])
  })

  it('lets the advice only add chips, in chip order', () => {
    expect(preselectedCategories('flat_tyre', null, ['repair', 'tyres'])).toEqual([
      'tyres',
      'repair',
    ])
    expect(preselectedCategories('other', null, ['fuel'])).toEqual(ALL_CATEGORIES)
  })
})

describe('toggleCategory', () => {
  it('narrows "all" to the tapped chip', () => {
    expect(toggleCategory(ALL_CATEGORIES, 'fuel')).toEqual(['fuel'])
  })

  it('adds and removes chips, back to all when none is left', () => {
    expect(toggleCategory(['tyres'], 'repair')).toEqual(['tyres', 'repair'])
    expect(toggleCategory(['tyres', 'repair'], 'tyres')).toEqual(['repair'])
    expect(toggleCategory(['repair'], 'repair')).toEqual(ALL_CATEGORIES)
  })

  it('isAll is true only with every chip', () => {
    expect(isAll(ALL_CATEGORIES)).toBe(true)
    expect(isAll(['tyres', 'fuel', 'charging'])).toBe(false)
  })
})

describe('filterPlaces', () => {
  const place = (osm_id: number, category: PlaceRead['category']): PlaceRead => ({
    osm_type: 'node',
    osm_id,
    category,
    name: null,
    lat: 52,
    lon: 21,
    distance_m: osm_id * 100,
    phone: null,
    opening_hours: null,
  })

  it('keeps the distance order of the chosen categories', () => {
    const places = [place(1, 'fuel'), place(2, 'tyres'), place(3, 'fuel')]
    expect(filterPlaces(places, ['fuel']).map((p) => p.osm_id)).toEqual([1, 3])
    expect(filterPlaces(places, ALL_CATEGORIES)).toEqual(places)
  })
})
