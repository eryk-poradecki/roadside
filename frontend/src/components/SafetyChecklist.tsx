import { ChevronDown } from 'lucide-react'
import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { ProblemKey } from '../lib/problemType'

/**
 * The static, non-AI safety checklist (ADR 0010): "Do this first", then the rest, the
 * shared 112 line last. It is bundled copy, so it shows without waiting for the network.
 * Once the AI has answered (`answered`), the items after the first step fold under a
 * visible "N more safety steps" toggle; the first step never hides while the incident is
 * open. Once the incident is resolved, the whole list, first step included, folds into
 * one "Safety steps" disclosure; reopening restores the open layout.
 */
export function SafetyChecklist({
  problem,
  resolved = false,
  answered = false,
}: {
  problem: ProblemKey
  resolved?: boolean
  answered?: boolean
}) {
  const { t } = useTranslation()
  const titleId = useId()

  if (resolved) {
    return (
      <details className="panel fold">
        <summary>
          <span>{t('checklist.resolvedSummary')}</span>
          <ChevronDown className="fold-icon" size={20} aria-hidden="true" />
        </summary>
        <div className="fold-body">
          <Steps problem={problem} titleId={titleId} folds={false} />
        </div>
      </details>
    )
  }
  return (
    <section className="panel" aria-labelledby={titleId}>
      <Steps problem={problem} titleId={titleId} folds={answered} />
    </section>
  )
}

function Steps({
  problem,
  titleId,
  folds,
}: {
  problem: ProblemKey
  titleId: string
  /** The rest sits under a toggle, closed until the driver opens it. */
  folds: boolean
}) {
  const { t } = useTranslation()
  const listId = useId()
  const [open, setOpen] = useState(false)
  const items = t(`checklist.lists.${problem}.items`, { returnObjects: true })
  const shown = !folds || open
  return (
    <>
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
      {folds ? (
        <button
          type="button"
          className="disclosure"
          aria-expanded={open}
          aria-controls={listId}
          onClick={() => {
            setOpen(!open)
          }}
        >
          <span>{t('checklist.checklistSummary', { count: items.length })}</span>
          <span className="disclosure-act">
            {open ? t('checklist.hide') : t('checklist.show')}
            <ChevronDown size={18} aria-hidden="true" className={open ? 'flip' : undefined} />
          </span>
        </button>
      ) : (
        <h3 className="then">{t('checklist.checklistTitle')}</h3>
      )}
      {/* Kept mounted so the toggle's aria-controls always resolves. */}
      <ol id={listId} className="checklist" start={2} hidden={!shown}>
        {items.map((item, i) => (
          <li key={item}>
            <span className="check" aria-hidden="true">
              {i + 2}
            </span>
            <span>{item}</span>
          </li>
        ))}
      </ol>
    </>
  )
}
