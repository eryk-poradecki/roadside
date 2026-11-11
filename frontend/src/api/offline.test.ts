import { isOffline, requestAnswered, requestFailed, requestSent } from './offline'

describe('offline flag', () => {
  afterEach(() => {
    requestAnswered(requestSent())
  })

  it('is set by a request that got no response', () => {
    requestFailed(requestSent())
    expect(isOffline()).toBe(true)
  })

  it('is cleared by a later answer', () => {
    requestFailed(requestSent())
    requestAnswered(requestSent())
    expect(isOffline()).toBe(false)
  })

  it('ignores a failure of a request sent before a newer one was answered', () => {
    const older = requestSent()
    const newer = requestSent()
    requestAnswered(newer)
    requestFailed(older)
    expect(isOffline()).toBe(false)
  })

  it('is cleared when the browser comes back online', () => {
    requestFailed(requestSent())
    window.dispatchEvent(new Event('online'))
    expect(isOffline()).toBe(false)
  })
})
