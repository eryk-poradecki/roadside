import { PROBLEM_TYPES, problemKey } from './problemType'

describe('problemKey', () => {
  it('maps every wire value to its copy key', () => {
    expect(PROBLEM_TYPES.map((t) => problemKey(t))).toEqual([
      'tyre',
      'battery',
      'fuel',
      'pothole',
      'other',
    ])
  })

  it('uses the charge variant only for out of fuel on an electric vehicle', () => {
    expect(problemKey('out_of_fuel', 'electric')).toBe('charge')
    expect(problemKey('out_of_fuel', 'plug_in_hybrid')).toBe('fuel')
    expect(problemKey('out_of_fuel', null)).toBe('fuel')
    // Flat battery is always the 12 V battery, never the traction battery.
    expect(problemKey('flat_battery', 'electric')).toBe('battery')
  })
})
