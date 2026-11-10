import type {
  FuelType,
  SpareWheel,
  Transmission,
  VehicleCreate,
  VehicleRead,
} from '../api/vehicles'

/** The vehicle form's state: plain strings, so inputs stay controlled. '' means unknown. */
export interface VehicleDraft {
  name: string
  makeModel: string
  year: string
  fuelType: FuelType | ''
  transmission: Transmission | ''
  registration: string
  tyreSize: string
  spareWheel: SpareWheel | ''
  wheelLocks: 'yes' | 'no' | ''
  lockKeyLocation: string
  assistanceInsurer: string
  assistancePhone: string
  policyNumber: string
  isDefault: boolean
}

export type DraftErrors = Partial<Record<'name' | 'year', 'nameRequired' | 'yearRange'>>

export const MIN_YEAR = 1900
export const MAX_YEAR = 2100

export function emptyDraft(isDefault: boolean): VehicleDraft {
  return {
    name: '',
    makeModel: '',
    year: '',
    fuelType: '',
    transmission: '',
    registration: '',
    tyreSize: '',
    spareWheel: '',
    wheelLocks: '',
    lockKeyLocation: '',
    assistanceInsurer: '',
    assistancePhone: '',
    policyNumber: '',
    isDefault,
  }
}

export function draftFromVehicle(v: VehicleRead): VehicleDraft {
  return {
    name: v.name,
    makeModel: v.make_model ?? '',
    year: v.year === null ? '' : String(v.year),
    fuelType: v.fuel_type ?? '',
    transmission: v.transmission ?? '',
    registration: v.registration ?? '',
    tyreSize: v.tyre_size ?? '',
    spareWheel: v.spare_wheel ?? '',
    wheelLocks: v.wheel_locks === null ? '' : v.wheel_locks ? 'yes' : 'no',
    lockKeyLocation: v.lock_key_location ?? '',
    assistanceInsurer: v.assistance_insurer ?? '',
    assistancePhone: v.assistance_phone ?? '',
    policyNumber: v.policy_number ?? '',
    isDefault: v.is_default,
  }
}

/** Transmission does not apply to an electric vehicle. */
export const showsTransmission = (d: VehicleDraft) => d.fuelType !== 'electric'

/** The lock-key location only makes sense when the car has wheel locks. */
export const showsLockKey = (d: VehicleDraft) => d.wheelLocks === 'yes'

export function validateDraft(d: VehicleDraft): DraftErrors {
  const errors: DraftErrors = {}
  if (d.name.trim() === '') errors.name = 'nameRequired'
  const year = d.year.trim()
  if (year !== '') {
    const n = Number(year)
    if (!/^\d+$/.test(year) || n < MIN_YEAR || n > MAX_YEAR) errors.year = 'yearRange'
  }
  return errors
}

const orNull = (value: string) => value.trim() || null

/** The request body: blank means unknown (null), and hidden fields are sent as null. */
export function toVehicleBody(d: VehicleDraft): VehicleCreate {
  return {
    name: d.name.trim(),
    make_model: orNull(d.makeModel),
    year: d.year.trim() === '' ? null : Number(d.year),
    fuel_type: d.fuelType || null,
    transmission: showsTransmission(d) ? d.transmission || null : null,
    registration: orNull(d.registration),
    tyre_size: orNull(d.tyreSize),
    spare_wheel: d.spareWheel || null,
    wheel_locks: d.wheelLocks === '' ? null : d.wheelLocks === 'yes',
    lock_key_location: showsLockKey(d) ? orNull(d.lockKeyLocation) : null,
    assistance_insurer: orNull(d.assistanceInsurer),
    assistance_phone: orNull(d.assistancePhone),
    policy_number: orNull(d.policyNumber),
    is_default: d.isDefault,
  }
}
