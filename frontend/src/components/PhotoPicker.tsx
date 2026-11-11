import { Camera, Loader, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useConfig } from '../api/config'
import { photoSrc, type PhotoSource, type SamplePhoto } from '../api/photos'
import { en } from '../i18n/en'
import './Photos.css'

/** The API's cap, until `GET /config` has loaded. */
export const DEFAULT_MAX_PHOTOS = 5

type SampleId = keyof typeof en.photos.samples
const isSampleId = (id: string): id is SampleId => id in en.photos.samples

/** The sample's title in the UI language; the server's English title for one we don't know. */
export function useSampleTitle() {
  const { t } = useTranslation()
  return (sample: SamplePhoto) =>
    isSampleId(sample.id) ? t(`photos.samples.${sample.id}`) : sample.title
}

/**
 * "Add photos": the device's files, or in demo mode (uploads refused, ADR 0002) the bundled
 * sample photos. At most `remaining` files are taken from one pick.
 */
export function AddPhotos({
  remaining,
  onPick,
}: {
  remaining: number
  onPick: (sources: PhotoSource[]) => void
}) {
  const { t } = useTranslation()
  const config = useConfig().data
  const title = useSampleTitle()
  if (!config) return null

  if (config.demo_mode) {
    return (
      <div className="samples">
        <p className="muted">{t('photos.samplesIntro')}</p>
        <ul className="sample-list" aria-label={t('photos.samplesLabel')}>
          {config.sample_photos.map((sample) => (
            <li key={sample.id}>
              <button
                type="button"
                className="sample"
                title={t('photos.sampleCredit', { credit: sample.credit })}
                onClick={() => {
                  onPick([{ sampleId: sample.id }])
                }}
              >
                <img src={photoSrc(sample.url)} alt="" loading="lazy" />
                <span>{title(sample)}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    )
  }

  return (
    <label className="btn btn-quiet photo-add">
      <Camera size={20} aria-hidden="true" />
      {t('photos.add')}
      <input
        type="file"
        className="sr-only"
        accept="image/jpeg,image/png,image/webp,image/*"
        multiple
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []).slice(0, remaining)
          // Let the same file be picked again later.
          e.target.value = ''
          if (files.length > 0) onPick(files.map((file) => ({ file })))
        }}
      />
    </label>
  )
}

export type Thumb = {
  key: string | number
  /** Empty while the browser can't show a preview yet. */
  src: string
  pending?: boolean
  onRemove?: () => void
}

/** Photos as a grid of tiles, in order, each removable on its own. */
export function PhotoGrid({ items, removing = false }: { items: Thumb[]; removing?: boolean }) {
  const { t } = useTranslation()
  if (items.length === 0) return null
  return (
    <ul className="photo-grid">
      {items.map((item, i) => {
        const n = i + 1
        return (
          <li key={item.key} className={item.pending ? 'photo photo-pending' : 'photo'}>
            {item.src ? (
              <img src={item.src} alt={t('photos.photo', { n })} loading="lazy" />
            ) : (
              <span className="photo-blank" role="img" aria-label={t('photos.photo', { n })} />
            )}
            {item.pending && (
              <span className="photo-status">
                <Loader size={18} className="spin" aria-hidden="true" />
                {t('photos.uploading')}
              </span>
            )}
            {item.onRemove && (
              <button
                type="button"
                className="photo-remove"
                aria-label={t('photos.remove', { n })}
                disabled={removing}
                onClick={item.onRemove}
              >
                <X size={18} aria-hidden="true" />
              </button>
            )}
          </li>
        )
      })}
    </ul>
  )
}

/** Shown wherever photos are picked while the provider can see them (ADR 0002). */
export function VisionNote() {
  const { t } = useTranslation()
  const vision = useConfig().data?.vision_enabled === true
  return vision ? <p className="muted photo-note">{t('photos.visionNote')}</p> : null
}
