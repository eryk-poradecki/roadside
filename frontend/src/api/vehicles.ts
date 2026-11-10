import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createVehicleMutation,
  deleteVehicleMutation,
  getVehicleOptions,
  listVehiclesOptions,
  listVehiclesQueryKey,
  replaceVehicleMutation,
} from './generated/@tanstack/react-query.gen'
import type { VehicleCreate, VehicleRead } from './generated/types.gen'

export type {
  FuelType,
  SpareWheel,
  Transmission,
  VehicleCreate,
  VehicleRead,
} from './generated/types.gen'

export const useVehicles = () => useQuery(listVehiclesOptions())

export const useVehicle = (id: number) => useQuery(getVehicleOptions({ path: { vehicle_id: id } }))

/** Every vehicle write changes the list, and the default flag can move between vehicles. */
function useInvalidateVehicles() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: listVehiclesQueryKey() })
}

export function useCreateVehicle() {
  const invalidate = useInvalidateVehicles()
  return useMutation({ ...createVehicleMutation(), onSuccess: invalidate })
}

export function useReplaceVehicle() {
  const invalidate = useInvalidateVehicles()
  return useMutation({ ...replaceVehicleMutation(), onSuccess: invalidate })
}

export function useDeleteVehicle() {
  const invalidate = useInvalidateVehicles()
  return useMutation({ ...deleteVehicleMutation(), onSuccess: invalidate })
}

/** The writable part of a vehicle, for a full PUT. */
export function replacementBody(vehicle: VehicleRead): VehicleCreate {
  const body: Partial<VehicleRead> = { ...vehicle }
  delete body.id
  delete body.created_at
  delete body.updated_at
  return body as VehicleCreate
}
