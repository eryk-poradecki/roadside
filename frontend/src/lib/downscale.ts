/** The client's long edge and JPEG quality: small uploads on a weak roadside signal (ADR 0002). */
export const UPLOAD_MAX_EDGE = 1600
const JPEG_QUALITY = 0.8

/** The size of a `width` × `height` image scaled down to fit `max` on its long edge. */
export function fitWithin(width: number, height: number, max: number): [number, number] {
  const scale = Math.min(1, max / Math.max(width, height))
  return [Math.max(1, Math.round(width * scale)), Math.max(1, Math.round(height * scale))]
}

/**
 * The photo re-encoded as a JPEG of at most `max` px on the long edge, with the EXIF
 * orientation applied. When the browser can't decode or encode it, the original file goes up
 * as it is: the server is the real gate and answers 413 or 415 if it must.
 */
export async function downscaleToJpeg(file: Blob, max: number = UPLOAD_MAX_EDGE): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
    try {
      const [width, height] = fitWithin(bitmap.width, bitmap.height, max)
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      if (!ctx) return file
      ctx.drawImage(bitmap, 0, 0, width, height)
      const blob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY)
      })
      return blob ?? file
    } finally {
      bitmap.close()
    }
  } catch {
    return file
  }
}
