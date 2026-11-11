import { RotateCw } from 'lucide-react'
import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import { isApiError } from '../api/client'
import { useConfig } from '../api/config'
import type { IncidentRead } from '../api/incidents'
import {
  photoSrc,
  useAddPhoto,
  useDeletePhoto,
  useDismissUpload,
  useUploads,
  type UploadState,
} from '../api/photos'
import { ErrorNotice, useErrorMessage } from './ErrorNotice'
import { AddPhotos, DEFAULT_MAX_PHOTOS, PhotoGrid, VisionNote } from './PhotoPicker'

/**
 * The incident's photos: the stored ones, uploads still running (from the help sheet or from
 * here) and failed ones. Photos can be added and removed one by one at any time; ones added
 * after the AI answer don't change it (ADR 0002).
 */
export function PhotosPanel({ incident }: { incident: IncidentRead }) {
  const { t } = useTranslation()
  const titleId = useId()
  const max = useConfig().data?.max_photos ?? DEFAULT_MAX_PHOTOS
  const add = useAddPhoto()
  const remove = useDeletePhoto(incident.id)
  const uploads = useUploads(incident.id)
  const pending = uploads.filter((u) => u.status === 'pending')
  const failed = uploads.filter((u) => u.status === 'error')
  const photos = incident.photos
  const remaining = max - photos.length - pending.length

  const thumbs = [
    ...photos.map((photo) => ({
      key: photo.id,
      src: photoSrc(photo.url),
      onRemove: () => {
        remove.remove(photo.id).catch(() => {
          // Shown below from `remove.error`.
        })
      },
    })),
    ...pending.map((u) => ({ key: `upload-${String(u.mutationId)}`, src: '', pending: true })),
  ]

  return (
    <section className="panel panel-photos" aria-labelledby={titleId}>
      <div className="panel-head">
        <h2 id={titleId}>{t('photos.title')}</h2>
        <span className="badge">{t('photos.count', { count: photos.length, max })}</span>
      </div>
      <VisionNote />
      {thumbs.length === 0 && <p className="muted">{t('photos.empty')}</p>}
      <PhotoGrid items={thumbs} removing={remove.isPending} />
      {failed.map((upload) => (
        <FailedUpload key={upload.mutationId} upload={upload} onRetry={add.mutate} />
      ))}
      {remove.isError && <ErrorNotice error={remove.error} />}
      {remaining > 0 ? (
        <AddPhotos
          remaining={remaining}
          onPick={(sources) => {
            for (const source of sources) add.mutate({ incidentId: incident.id, source })
          }}
        />
      ) : (
        <p className="muted">{t('photos.full')}</p>
      )}
    </section>
  )
}

function FailedUpload({
  upload,
  onRetry,
}: {
  upload: UploadState
  onRetry: (variables: UploadState['variables']) => void
}) {
  const { t } = useTranslation()
  const message = useErrorMessage()
  const dismiss = useDismissUpload()
  // Only a lost connection or a server failure can go better on a second try.
  const error = upload.error
  const retryable = isApiError(error) && (error.problem.status === 0 || error.problem.status >= 500)
  return (
    <div className="notice notice-error photo-failed" role="alert">
      <p>
        {t('photos.failed')} {message(error)}
      </p>
      <div className="photo-failed-actions">
        {retryable && (
          <button
            type="button"
            className="btn btn-quiet"
            onClick={() => {
              dismiss(upload.mutationId)
              onRetry(upload.variables)
            }}
          >
            <RotateCw size={18} aria-hidden="true" />
            {t('common.retry')}
          </button>
        )}
        <button
          type="button"
          className="btn btn-quiet"
          onClick={() => {
            dismiss(upload.mutationId)
          }}
        >
          {t('photos.dismiss')}
        </button>
      </div>
    </div>
  )
}
