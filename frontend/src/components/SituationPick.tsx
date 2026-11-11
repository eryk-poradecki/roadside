import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import type { Situation } from '../api/generated/types.gen'

export type { Situation }

/** On the road first: it is the default, and the app never assumes parked (#93). */
const SITUATIONS: Situation[] = ['on_road', 'parked']

/**
 * Where the car is, asked rather than inferred: a reverse geocode can't tell a parking lot
 * from a street. Parked picks the short safety checklist without the roadside steps.
 */
export function SituationPick({
  value,
  onChange,
}: {
  value: Situation
  onChange: (situation: Situation) => void
}) {
  const { t } = useTranslation()
  const name = useId()
  return (
    <fieldset className="vehicle-pick">
      <legend className="note-label">{t('situation.label')}</legend>
      {SITUATIONS.map((situation) => (
        <label key={situation} className="choice">
          <input
            type="radio"
            name={name}
            checked={value === situation}
            onChange={() => {
              onChange(situation)
            }}
          />
          <span>{t(`situation.${situation}`)}</span>
        </label>
      ))}
    </fieldset>
  )
}
