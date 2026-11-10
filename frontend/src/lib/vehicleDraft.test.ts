import { emptyDraft, toVehicleBody, validateDraft } from './vehicleDraft'

describe('validateDraft', () => {
  it('accepts a name alone', () => {
    expect(validateDraft({ ...emptyDraft(false), name: 'Golf' })).toEqual({})
  })

  it('treats a blank name as missing', () => {
    expect(validateDraft({ ...emptyDraft(false), name: '   ' })).toEqual({ name: 'nameRequired' })
  })

  it.each(['1899', '2101', 'abc', '20.5'])('rejects year %s', (year) => {
    expect(validateDraft({ ...emptyDraft(false), name: 'x', year })).toEqual({ year: 'yearRange' })
  })

  it.each(['1900', '2026', '2100'])('accepts year %s', (year) => {
    expect(validateDraft({ ...emptyDraft(false), name: 'x', year })).toEqual({})
  })
})

describe('toVehicleBody', () => {
  it('sends blanks as null and trims text', () => {
    const body = toVehicleBody({ ...emptyDraft(true), name: ' Golf ', makeModel: '  ' })
    expect(body).toMatchObject({ name: 'Golf', make_model: null, year: null, is_default: true })
  })
})
