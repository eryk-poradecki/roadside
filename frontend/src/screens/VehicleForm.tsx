import { ArrowLeft } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'
import { ErrorNotice } from '../components/ErrorNotice'
import {
  useCreateVehicle,
  useReplaceVehicle,
  useVehicle,
  useVehicles,
  type VehicleRead,
} from '../api/vehicles'
import {
  draftFromVehicle,
  emptyDraft,
  showsLockKey,
  showsTransmission,
  toVehicleBody,
  validateDraft,
  type DraftErrors,
  type VehicleDraft,
} from '../lib/vehicleDraft'
import { en } from '../i18n/en'
import './Vehicles.css'

const FUEL_TYPES = Object.keys(
  en.vehicleForm.fuelTypes,
) as (keyof typeof en.vehicleForm.fuelTypes)[]
const TRANSMISSIONS = Object.keys(
  en.vehicleForm.transmissions,
) as (keyof typeof en.vehicleForm.transmissions)[]
const SPARE_WHEELS = Object.keys(
  en.vehicleForm.spareWheels,
) as (keyof typeof en.vehicleForm.spareWheels)[]

function Field({
  id,
  label,
  error,
  children,
}: {
  id: string
  label: string
  error?: string | undefined
  children: ReactNode
}) {
  return (
    <div className="vform-field">
      <label htmlFor={id}>{label}</label>
      {children}
      {error && (
        <p className="vform-error" id={`${id}-error`}>
          {error}
        </p>
      )}
    </div>
  )
}

function VehicleEditor({ vehicle, initial }: { vehicle?: VehicleRead; initial: VehicleDraft }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const create = useCreateVehicle()
  const replace = useReplaceVehicle()
  const [draft, setDraft] = useState(initial)
  const [errors, setErrors] = useState<DraftErrors>({})
  const mutation = vehicle ? replace : create

  const set = <K extends keyof VehicleDraft>(key: K, value: VehicleDraft[K]) => {
    setDraft((d) => ({ ...d, [key]: value }))
  }
  const text = (
    key:
      | 'name'
      | 'makeModel'
      | 'registration'
      | 'tyreSize'
      | 'lockKeyLocation'
      | 'assistanceInsurer'
      | 'assistancePhone'
      | 'policyNumber',
  ) => ({
    value: draft[key],
    onChange: (e: { target: { value: string } }) => {
      set(key, e.target.value)
    },
  })

  const onSubmit = (event: React.SyntheticEvent) => {
    event.preventDefault()
    const found = validateDraft(draft)
    setErrors(found)
    if (Object.keys(found).length > 0) return
    const body = toVehicleBody(draft)
    const done = { onSuccess: () => void navigate('/vehicles') }
    if (vehicle) replace.mutate({ path: { vehicle_id: vehicle.id }, body }, done)
    else create.mutate({ body }, done)
  }

  const f = 'vehicleForm.fields'
  const nameError = errors.name && t(`vehicleForm.validation.${errors.name}`)
  const yearError = errors.year && t(`vehicleForm.validation.${errors.year}`)

  return (
    <form className="vform" onSubmit={onSubmit} noValidate>
      <p className="muted">{t('vehicleForm.requiredHint')}</p>

      <fieldset>
        <legend>{t('vehicleForm.groups.basics')}</legend>
        <Field id="vf-name" label={`${t(`${f}.name`)} *`} error={nameError}>
          <input
            id="vf-name"
            className="field"
            required
            aria-invalid={!!nameError}
            aria-describedby={nameError ? 'vf-name-error' : undefined}
            placeholder={t(`${f}.namePlaceholder`)}
            autoComplete="off"
            {...text('name')}
          />
        </Field>
        <Field id="vf-make" label={t(`${f}.makeModel`)}>
          <input id="vf-make" className="field" autoComplete="off" {...text('makeModel')} />
        </Field>
        <Field id="vf-year" label={t(`${f}.year`)} error={yearError}>
          <input
            id="vf-year"
            className="field"
            inputMode="numeric"
            autoComplete="off"
            aria-invalid={!!yearError}
            aria-describedby={yearError ? 'vf-year-error' : undefined}
            value={draft.year}
            onChange={(e) => {
              set('year', e.target.value)
            }}
          />
        </Field>
        <Field id="vf-fuel" label={t(`${f}.fuelType`)}>
          <select
            id="vf-fuel"
            className="field"
            value={draft.fuelType}
            onChange={(e) => {
              set('fuelType', e.target.value as VehicleDraft['fuelType'])
            }}
          >
            <option value="">{t('vehicleForm.unknown')}</option>
            {FUEL_TYPES.map((v) => (
              <option key={v} value={v}>
                {t(`vehicleForm.fuelTypes.${v}`)}
              </option>
            ))}
          </select>
        </Field>
        {showsTransmission(draft) && (
          <Field id="vf-transmission" label={t(`${f}.transmission`)}>
            <select
              id="vf-transmission"
              className="field"
              value={draft.transmission}
              onChange={(e) => {
                set('transmission', e.target.value as VehicleDraft['transmission'])
              }}
            >
              <option value="">{t('vehicleForm.unknown')}</option>
              {TRANSMISSIONS.map((v) => (
                <option key={v} value={v}>
                  {t(`vehicleForm.transmissions.${v}`)}
                </option>
              ))}
            </select>
          </Field>
        )}
        <Field id="vf-registration" label={t(`${f}.registration`)}>
          <input
            id="vf-registration"
            className="field"
            autoComplete="off"
            {...text('registration')}
          />
        </Field>
      </fieldset>

      <fieldset>
        <legend>{t('vehicleForm.groups.tyres')}</legend>
        <Field id="vf-tyre" label={t(`${f}.tyreSize`)}>
          <input
            id="vf-tyre"
            className="field"
            autoComplete="off"
            placeholder={t(`${f}.tyreSizePlaceholder`)}
            {...text('tyreSize')}
          />
        </Field>
        <Field id="vf-spare" label={t(`${f}.spareWheel`)}>
          <select
            id="vf-spare"
            className="field"
            value={draft.spareWheel}
            onChange={(e) => {
              set('spareWheel', e.target.value as VehicleDraft['spareWheel'])
            }}
          >
            <option value="">{t('vehicleForm.unknown')}</option>
            {SPARE_WHEELS.map((v) => (
              <option key={v} value={v}>
                {t(`vehicleForm.spareWheels.${v}`)}
              </option>
            ))}
          </select>
        </Field>
        <Field id="vf-locks" label={t(`${f}.wheelLocks`)}>
          <select
            id="vf-locks"
            className="field"
            value={draft.wheelLocks}
            onChange={(e) => {
              set('wheelLocks', e.target.value as VehicleDraft['wheelLocks'])
            }}
          >
            <option value="">{t('vehicleForm.unknown')}</option>
            <option value="yes">{t('vehicleForm.yes')}</option>
            <option value="no">{t('vehicleForm.no')}</option>
          </select>
        </Field>
        {showsLockKey(draft) && (
          <Field id="vf-lockkey" label={t(`${f}.lockKeyLocation`)}>
            <input
              id="vf-lockkey"
              className="field"
              autoComplete="off"
              placeholder={t(`${f}.lockKeyPlaceholder`)}
              {...text('lockKeyLocation')}
            />
          </Field>
        )}
      </fieldset>

      <fieldset>
        <legend>{t('vehicleForm.groups.assistance')}</legend>
        <Field id="vf-insurer" label={t(`${f}.insurer`)}>
          <input
            id="vf-insurer"
            className="field"
            autoComplete="off"
            {...text('assistanceInsurer')}
          />
        </Field>
        <Field id="vf-phone" label={t(`${f}.phone`)}>
          <input
            id="vf-phone"
            className="field"
            type="tel"
            autoComplete="off"
            {...text('assistancePhone')}
          />
        </Field>
        <Field id="vf-policy" label={t(`${f}.policyNumber`)}>
          <input id="vf-policy" className="field" autoComplete="off" {...text('policyNumber')} />
        </Field>
      </fieldset>

      <div className="vform-check">
        <input
          id="vf-default"
          type="checkbox"
          checked={draft.isDefault}
          onChange={(e) => {
            set('isDefault', e.target.checked)
          }}
        />
        <label htmlFor="vf-default">{t(`${f}.isDefault`)}</label>
      </div>

      {mutation.isError && <ErrorNotice error={mutation.error} />}
      <button type="submit" className="btn btn-primary" disabled={mutation.isPending}>
        {mutation.isPending ? t('vehicleForm.saving') : t('vehicleForm.save')}
      </button>
    </form>
  )
}

function Frame({ heading, children }: { heading: string; children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <>
      <Link to="/vehicles" className="back">
        <ArrowLeft size={20} aria-hidden="true" />
        {t('common.back')}
      </Link>
      <h1>{heading}</h1>
      {children}
    </>
  )
}

function NewVehicle() {
  const { t } = useTranslation()
  const { data: vehicles, isPending, isError, error } = useVehicles()
  return (
    <Frame heading={t('vehicleForm.newHeading')}>
      {isPending && <p className="muted">{t('common.loading')}</p>}
      {isError && <ErrorNotice error={error} />}
      {/* The first vehicle becomes the default (ADR 0005), so the box starts ticked. */}
      {vehicles && <VehicleEditor initial={emptyDraft(!vehicles.some((v) => v.is_default))} />}
    </Frame>
  )
}

function EditVehicle({ id }: { id: number }) {
  const { t } = useTranslation()
  const { data: vehicle, isPending, isError, error } = useVehicle(id)
  return (
    <Frame heading={t('vehicleForm.editHeading')}>
      {isPending && <p className="muted">{t('common.loading')}</p>}
      {isError && <ErrorNotice error={error} />}
      {vehicle && (
        <VehicleEditor key={vehicle.id} vehicle={vehicle} initial={draftFromVehicle(vehicle)} />
      )}
    </Frame>
  )
}

export function VehicleForm() {
  const { id } = useParams()
  return id === undefined ? <NewVehicle /> : <EditVehicle id={Number(id)} />
}
