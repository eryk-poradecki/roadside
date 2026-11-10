import { useId } from 'react'
import { useTranslation } from 'react-i18next'
import type { ProblemKey } from '../lib/problemType'

/**
 * The static, non-AI safety checklist (ADR 0010): "Do this first", then the rest, the
 * shared 112 line last. It is bundled copy, so it shows without waiting for the network.
 */
export function SafetyChecklist({ problem }: { problem: ProblemKey }) {
  const { t } = useTranslation()
  const titleId = useId()
  const items = t(`checklist.lists.${problem}.items`, { returnObjects: true })

  return (
    <section className="panel" aria-labelledby={titleId}>
      <div className="panel-head">
        <h2 id={titleId}>{t('checklist.firstLabel')}</h2>
        <span className="badge">{t('checklist.checklistBadge')}</span>
      </div>
      <p className="first-step">
        <span className="check check-first" aria-hidden="true">
          1
        </span>
        <span>{t(`checklist.lists.${problem}.first`)}</span>
      </p>
      <h3 className="then">{t('checklist.checklistTitle')}</h3>
      <ol className="checklist" start={2}>
        {items.map((item, i) => (
          <li key={item}>
            <span className="check" aria-hidden="true">
              {i + 2}
            </span>
            <span>{item}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}
