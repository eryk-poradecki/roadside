import { downscaleToJpeg, fitWithin } from './downscale'

describe('fitWithin', () => {
  it.each([
    [
      [4000, 3000],
      [1600, 1200],
    ],
    [
      [3000, 4000],
      [1200, 1600],
    ],
    [
      [1600, 900],
      [1600, 900],
    ],
    [
      [800, 600],
      [800, 600],
    ],
    [
      [5000, 10],
      [1600, 3],
    ],
    [
      [10, 5000],
      [3, 1600],
    ],
  ])('%j → %j', ([w, h], expected) => {
    expect(fitWithin(w ?? 0, h ?? 0, 1600)).toEqual(expected)
  })
})

describe('downscaleToJpeg', () => {
  it('sends the original file when the browser cannot decode it', async () => {
    // jsdom has no createImageBitmap: the server, the real gate, decides (ADR 0002).
    const file = new File(['not really an image'], 'a.heic', { type: 'image/heic' })
    await expect(downscaleToJpeg(file)).resolves.toBe(file)
  })
})
