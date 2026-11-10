import { Camera, Loader, RotateCw, Sparkles, WifiOff } from 'lucide-react'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  autoStartClaimed,
  claimAutoStart,
  findAdvice,
  useTakeAiTurn,
  useTurnInFlight,
  type AdviceRead,
  type Confidence,
  type Locale,
  type TurnInputsRead,
} from '../api/aiTurns'
import type { FuelType } from '../api/generated/types.gen'
import type { IncidentRead } from '../api/incidents'
import { isProblemType, problemKey } from '../lib/problemType'
import { useErrorMessage } from './ErrorNotice'
import './AiPanel.css'

/**
 * The AI answer on the Result screen, labelled as AI. Right after "Get help now"
 * (`autoStart`) it asks for the advice at once; a failed turn shows why and "Try again",
 * while the safety checklist above stays as it is.
 */
export function AiPanel({ incident, autoStart }: { incident: IncidentRead; autoStart: boolean }) {
  const { t, i18n } = useTranslation()
  const turn = useTakeAiTurn(incident.id)
  const inFlight = useTurnInFlight(incident.id)
  const message = useErrorMessage()
  const adviceTurn = findAdvice(incident)
  // About to ask on its own: show the waiting state from the first paint, not "not answered".
  const starting = autoStart && !adviceTurn && turn.isIdle && !autoStartClaimed(incident.id)
  // The answer is in the UI language only, never the note's (ADR 0004).
  const locale: Locale = i18n.resolvedLanguage === 'pl' ? 'pl' : 'en'

  const ask = () => {
    turn.take(locale).catch(() => {
      // Shown below from `turn.error`.
    })
  }

  // At most once per incident and session: not again after a remount, a reload or
  // StrictMode's second effect run, and never while a turn is in flight or answered.
  useEffect(() => {
    if (!autoStart || adviceTurn || inFlight || !claimAutoStart(incident.id)) return
    ask()
  })

  return (
    <section className="panel panel-ai" aria-labelledby="ai-title" aria-busy={inFlight}>
      <div className="panel-head">
        <h2 id="ai-title">{t('ai.title')}</h2>
        <span className="badge badge-ai">
          <Sparkles size={14} aria-hidden="true" />
          {t('ai.badge')}
        </span>
      </div>

      <div className="ai-body" aria-live="polite">
        {adviceTurn?.advice ? (
          <Advice advice={adviceTurn.advice} inputs={adviceTurn.inputs} />
        ) : inFlight || starting ? (
          <div className="ai-loading">
            <p className="ai-line">
              <Loader size={20} className="spin" aria-hidden="true" />
              {t('ai.loading')}
            </p>
            <p className="muted">{t('ai.loadingSub')}</p>
            <div className="skeleton" aria-hidden="true">
              <i />
              <i />
              <i />
            </div>
          </div>
        ) : turn.isError ? (
          <div className="ai-error" role="alert">
            <p className="ai-line">
              <WifiOff size={20} aria-hidden="true" />
              <strong>{t('ai.errorTitle')}</strong>
            </p>
            <p className="muted">
              {message(turn.error)} {t('ai.errorBody')}
            </p>
            <button type="button" className="btn btn-quiet" onClick={ask}>
              <RotateCw size={20} aria-hidden="true" />
              {t('ai.retry')}
            </button>
          </div>
        ) : (
          // Opened later with no advice (it failed, or the driver left mid-turn): finish it.
          <div className="ai-idle">
            <p className="muted">{t('ai.notAnswered')}</p>
            <button type="button" className="btn btn-quiet" onClick={ask}>
              <Sparkles size={20} aria-hidden="true" />
              {t('ai.ask')}
            </button>
          </div>
        )}
      </div>
    </section>
  )
}

function ConfidenceMark({ confidence }: { confidence: Confidence }) {
  const { t } = useTranslation()
  const level = { likely: 3, possible: 2, unsure: 1 }[confidence]
  return (
    <span className={`conf conf-${confidence}`}>
      <span className="conf-bars" aria-hidden="true">
        {[1, 2, 3].map((n) => (
          <i key={n} className={n <= level ? 'on' : undefined} />
        ))}
      </span>
      <span className="sr-only">{t('ai.confidenceLabel')}: </span>
      {t(`ai.confidence.${confidence}`)}
    </span>
  )
}

/**
 * What the advice was based on, read from the inputs snapshot stored with it, so it stays
 * true after the incident or the vehicle is edited (ADR 0004).
 */
function AnsweredFor({ inputs }: { inputs: TurnInputsRead }) {
  const { t } = useTranslation()
  // A value this client doesn't know yet is left out rather than shown as a raw key.
  if (!isProblemType(inputs.problem_type)) return null
  const key = problemKey(inputs.problem_type, inputs.vehicle?.fuel_type as FuelType | null)
  const problem = t(`start.tiles.${key}`)
  return (
    <p>
      {inputs.vehicle
        ? t('ai.answeredFor', { vehicle: inputs.vehicle.name, problem })
        : t('ai.answeredForNoVehicle', { problem })}
    </p>
  )
}

function Advice({ advice, inputs }: { advice: AdviceRead; inputs: TurnInputsRead | null }) {
  const { t } = useTranslation()
  return (
    <div className="answer">
      <div className="dx">
        <div className="dx-head">
          <span className="dx-label">{t(`ai.dxLabel.${advice.confidence}`)}</span>
          <ConfidenceMark confidence={advice.confidence} />
        </div>
        <p className="dx-cause">{advice.cause}</p>
        {advice.alternatives.length > 0 && (
          <div className="dx-alt">
            <span>{t('ai.alsoCould')}</span>
            <ul>
              {advice.alternatives.map((alt) => (
                <li key={alt}>{alt}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {advice.photo_observation && (
        <p className="photo-line">
          <Camera size={18} aria-hidden="true" />
          <span>
            <strong>{t('ai.photoSeen')}:</strong> {advice.photo_observation}
          </span>
        </p>
      )}

      <div className="steps-block">
        <h3>{t('ai.stepsTitle')}</h3>
        <ol className="steps">
          {advice.steps.map((step, i) => (
            <li key={`${String(i)}-${step}`}>
              <span className="step-n" aria-hidden="true">
                {i + 1}
              </span>
              <span>{step}</span>
            </li>
          ))}
        </ol>
      </div>

      <div className="escalate">
        <h3>{t('ai.escalateTitle')}</h3>
        <ul>
          {advice.escalate_if.map((condition) => (
            <li key={condition}>{condition}</li>
          ))}
        </ul>
      </div>

      <div className="answer-foot">
        {inputs && <AnsweredFor inputs={inputs} />}
        <p>{t('ai.disclaimer')}</p>
      </div>
    </div>
  )
}
