import { uuid } from './uuid'

const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

describe('uuid', () => {
  it('returns a fresh v4 UUID each time', () => {
    const a = uuid()
    expect(a).toMatch(V4)
    expect(uuid()).not.toBe(a)
  })

  it('falls back to getRandomValues outside a secure context', () => {
    const original = crypto.randomUUID.bind(crypto)
    Object.defineProperty(crypto, 'randomUUID', { value: undefined, configurable: true })
    try {
      expect(uuid()).toMatch(V4)
    } finally {
      Object.defineProperty(crypto, 'randomUUID', { value: original, configurable: true })
    }
  })
})
