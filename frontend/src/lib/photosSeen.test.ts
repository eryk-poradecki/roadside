import { photosSeen } from './photosSeen'

describe('photosSeen', () => {
  it('says nothing when every photo was seen, or there were none', () => {
    expect(photosSeen({ photo_ids_seen: [], photos_not_sent: 0 })).toBeNull()
    expect(photosSeen({ photo_ids_seen: [4, 5], photos_not_sent: 0 })).toBeNull()
  })

  it('says no photo was seen when the provider could not see them', () => {
    expect(photosSeen({ photo_ids_seen: [], photos_not_sent: 2 })).toEqual({
      kind: 'none',
      seen: 0,
      total: 2,
    })
  })

  it('says how many were seen when the cap left some out', () => {
    expect(photosSeen({ photo_ids_seen: [1, 2, 3], photos_not_sent: 2 })).toEqual({
      kind: 'some',
      seen: 3,
      total: 5,
    })
  })
})
