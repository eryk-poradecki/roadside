import {
  useIsMutating,
  useMutation,
  useMutationState,
  useQueryClient,
  type Mutation,
} from '@tanstack/react-query'
import { downscaleToJpeg } from '../lib/downscale'
import { isApiError } from './client'
import { client } from './generated/client.gen'
import { getIncidentQueryKey } from './generated/@tanstack/react-query.gen'
import { addPhoto, deletePhoto } from './generated/sdk.gen'
import type { AddPhotoData, IncidentRead, PhotoRead } from './generated/types.gen'

export type { PhotoRead, SamplePhoto } from './generated/types.gen'

/** What the driver picked: a file from the device, or a bundled sample in demo mode. */
export type PhotoSource = { file: File } | { sampleId: string }

export type AddPhotoVariables = { incidentId: number; source: PhotoSource }

const addKey = ['addPhoto'] as const

/** The photo URL the API returns is a path; images load it from the API's origin. */
export const photoSrc = (url: string) => `${client.getConfig().baseUrl ?? ''}${url}`

async function upload({ incidentId, source }: AddPhotoVariables): Promise<PhotoRead> {
  const path = { incident_id: incidentId }
  if ('sampleId' in source) {
    const { data } = await addPhoto({
      path,
      body: { sample_id: source.sampleId },
      throwOnError: true,
    })
    return data
  }
  const form = new FormData()
  form.append('file', await downscaleToJpeg(source.file), source.file.name)
  // The generated client types the JSON body only (one endpoint, two bodies, ADR 0002). Send
  // the form as it is, and let the browser set the multipart Content-Type and boundary.
  const { data } = await addPhoto({
    path,
    body: {} as AddPhotoData['body'],
    bodySerializer: () => form,
    headers: { 'Content-Type': null },
    throwOnError: true,
  })
  return data
}

const forIncident = (incidentId: number) => (m: Mutation) =>
  (m.state.variables as AddPhotoVariables | undefined)?.incidentId === incidentId

/**
 * `POST /incidents/{id}/photos`, one photo per request. Uploads live in the mutation cache,
 * not in a component, so they keep going after the help sheet closes and the Result screen
 * can wait for them. Never retried on its own: a failed upload shows "Try again".
 */
export function useAddPhoto() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: addKey,
    mutationFn: upload,
    networkMode: 'always',
    onSuccess: (photo, { incidentId }) => {
      queryClient.setQueryData<IncidentRead>(
        getIncidentQueryKey({ path: { incident_id: incidentId } }),
        (incident) =>
          incident && !incident.photos.some((p) => p.id === photo.id)
            ? { ...incident, photos: [...incident.photos, photo] }
            : incident,
      )
    },
    onError: (error, { incidentId }) => {
      // Another tab filled the last slot, or the incident is gone: show what the server has.
      const reason = isApiError(error) ? error.reason : undefined
      if (reason === 'photo_limit' || reason === 'not_found')
        return queryClient.invalidateQueries({
          queryKey: getIncidentQueryKey({ path: { incident_id: incidentId } }),
        })
    },
  })
}

/**
 * Uploads to this incident still running. The first AI turn waits until there are none: the
 * assistant should see the photos, and a failed upload must never block it (ADR 0002).
 */
export const usePhotosUploading = (incidentId: number) =>
  useIsMutating({ mutationKey: addKey, predicate: forIncident(incidentId) }) > 0

export type UploadState = {
  mutationId: number
  status: 'pending' | 'error'
  error: Error | null
  variables: AddPhotoVariables
}

/** Uploads to this incident that are running or failed, oldest first. */
export function useUploads(incidentId: number): UploadState[] {
  const all = useMutationState({
    filters: { mutationKey: addKey, predicate: forIncident(incidentId) },
    select: (m) => ({
      mutationId: m.mutationId,
      status: m.state.status,
      error: m.state.error,
      variables: m.state.variables as AddPhotoVariables,
    }),
  })
  return all.flatMap((u) =>
    u.status === 'pending' || u.status === 'error' ? [{ ...u, status: u.status }] : [],
  )
}

/** Forget a failed upload, once the driver has dismissed it or tried it again. */
export function useDismissUpload() {
  const queryClient = useQueryClient()
  return (mutationId: number) => {
    const cache = queryClient.getMutationCache()
    const mutation = cache.getAll().find((m) => m.mutationId === mutationId)
    if (mutation) cache.remove(mutation)
  }
}

/** `DELETE /photos/{id}`: removes the row and the file. */
export function useDeletePhoto(incidentId: number) {
  const queryClient = useQueryClient()
  const incidentKey = getIncidentQueryKey({ path: { incident_id: incidentId } })
  const mutation = useMutation({
    mutationFn: async (photoId: number) => {
      await deletePhoto({ path: { photo_id: photoId }, throwOnError: true })
    },
    networkMode: 'always',
    onSuccess: (_, photoId) => {
      queryClient.setQueryData<IncidentRead>(incidentKey, (incident) =>
        incident
          ? { ...incident, photos: incident.photos.filter((p) => p.id !== photoId) }
          : incident,
      )
    },
    onError: (error) => {
      // Already gone (another tab): show what the server has.
      if (isApiError(error) && error.reason === 'not_found')
        return queryClient.invalidateQueries({ queryKey: incidentKey })
    },
  })
  return {
    ...mutation,
    remove: (photoId: number) => mutation.mutateAsync(photoId),
  }
}
