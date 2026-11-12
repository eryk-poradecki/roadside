import {
  ArrowRight,
  Camera,
  CameraOff,
  Info,
  Loader,
  RotateCw,
  Send,
  Sparkles,
  WifiOff,
} from 'lucide-react'
import { useEffect, useId, useRef, useState, type SyntheticEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import {
  autoStartClaimed,
  claimAutoStart,
  findAdvice,
  openQuestion,
  questionsWithReplies,
  useTakeAiTurn,
  useTurnInFlight,
  type AdviceRead,
  type Confidence,
  type Locale,
  type QuestionRead,
  type QuestionWithReply,
  type ReplyCreate,
  type TurnInputsRead,
} from '../api/aiTurns'
import type { FuelType } from '../api/generated/types.gen'
import { isApiError } from '../api/client'
import type { IncidentRead } from '../api/incidents'
import { usePhotosUploading } from '../api/photos'
import { photosSeen } from '../lib/photosSeen'
import { isProblemType, problemKey } from '../lib/problemType'
import { useErrorMessage } from './ErrorNotice'
import { NOTE_MAX } from './HelpSheet'
import './AiPanel.css'

/** The longest the first AI turn waits for photos still uploading. */
export const UPLOAD_WAIT_MS = 20_000

/**
 * The AI answer on the Result screen, labelled as AI. Right after "Get help now"
 * (`autoStart`) it asks at once; the assistant may first ask up to two clarifying questions,
 * each replied to with a tap, a short text or "Just give me the steps". A failed turn shows
 * why and "Try again", while the safety checklist above stays as it is. In demo mode a case
 * with no recorded answer is labelled as such, with no "Try again": it would only miss again.
 */
export function AiPanel({
  incident,
  autoStart,
  noVehicles = false,
}: {
  incident: IncidentRead
  autoStart: boolean
  /** The driver has no vehicle saved: the answer's footer invites adding one. */
  noVehicles?: boolean
}) {
  const { t, i18n } = useTranslation()
  const turn = useTakeAiTurn(incident.id)
  const inFlight = useTurnInFlight(incident.id)
  // Photos picked in the help sheet are still uploading: the first turn waits for every one
  // to succeed or fail, so a failed upload never blocks it (ADR 0002).
  const uploadsPending = usePhotosUploading(incident.id)
  // A stalled upload on a weak signal must not hold the advice back for long.
  const [waitedOut, setWaitedOut] = useState(false)
  useEffect(() => {
    if (!uploadsPending) return
    const timer = setTimeout(() => {
      setWaitedOut(true)
    }, UPLOAD_WAIT_MS)
    return () => {
      clearTimeout(timer)
    }
  }, [uploadsPending])
  const uploading = uploadsPending && !waitedOut
  const message = useErrorMessage()
  const adviceTurn = findAdvice(incident)
  const question = openQuestion(incident)
  const replied = questionsWithReplies(incident)
  const started = incident.ai_turns.length > 0
  // About to ask on its own: show the waiting state from the first paint, not "not answered".
  const starting = autoStart && !started && turn.isIdle && !autoStartClaimed(incident)
  // The answer is in the UI language only, never the note's (ADR 0004).
  const locale: Locale = i18n.resolvedLanguage === 'pl' ? 'pl' : 'en'

  const ask = (reply?: ReplyCreate) => {
    turn.take(locale, reply).catch(() => {
      // Shown below from `turn.error`.
    })
  }

  // At most once per incident and session: not again after a remount, a reload or
  // StrictMode's second effect run, and never once the AI answer has begun.
  useEffect(() => {
    if (!autoStart || started || inFlight || uploading || !claimAutoStart(incident)) return
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

      {replied.length > 0 && <Replies items={replied} />}

      <div className="ai-body" aria-live="polite">
        {adviceTurn?.advice ? (
          <Advice advice={adviceTurn.advice} inputs={adviceTurn.inputs} noVehicles={noVehicles} />
        ) : inFlight || starting ? (
          <div className="ai-loading">
            <p className="ai-line">
              <Loader size={20} className="spin" aria-hidden="true" />
              {started ? t('ai.thinking') : t('ai.loading')}
            </p>
            <p className="muted">{t('ai.loadingSub')}</p>
            <div className="skeleton" aria-hidden="true">
              <i />
              <i />
              <i />
            </div>
          </div>
        ) : question?.question ? (
          <Ask
            key={question.id}
            question={question.question}
            // Only a failed reply to this question belongs here, e.g. no signal on the way.
            error={turn.isError && turn.variables.body.reply ? message(turn.error) : null}
            onReply={ask}
          />
        ) : turn.isError && isApiError(turn.error) && turn.error.reason === 'no_recording' ? (
          <div className="ai-error" role="alert">
            <p className="ai-line">
              <Info size={20} aria-hidden="true" />
              <strong>{t('ai.noRecordingTitle')}</strong>
            </p>
            <p className="muted">{t('ai.noRecordingBody')}</p>
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
            <button
              type="button"
              className="btn btn-quiet"
              onClick={() => {
                ask()
              }}
            >
              <RotateCw size={20} aria-hidden="true" />
              {t('ai.retry')}
            </button>
          </div>
        ) : (
          // Opened later with no advice (it failed, or the driver left mid-turn): finish it.
          <div className="ai-idle">
            <p className="muted">{t('ai.notAnswered')}</p>
            <button
              type="button"
              className="btn btn-quiet"
              onClick={() => {
                ask()
              }}
            >
              <Sparkles size={20} aria-hidden="true" />
              {t('ai.ask')}
            </button>
          </div>
        )}
      </div>
    </section>
  )
}

/** The questions already asked, each with the driver's reply, above what came next. */
function Replies({ items }: { items: QuestionWithReply[] }) {
  const { t } = useTranslation()
  return (
    <ul className="turns" aria-label={t('ai.yourReplies')}>
      {items.map(({ id, question, reply }) => (
        <li key={id} className="turn-done">
          <span>{question}</span>
          <strong>{reply.option ?? reply.text ?? t('ai.skipped')}</strong>
        </li>
      ))}
    </ul>
  )
}

/**
 * A clarifying question: its "Right now" safety step first, then the question with two to
 * four options to tap, a short answer of the driver's own, or "Just give me the steps".
 */
function Ask({
  question,
  error,
  onReply,
}: {
  question: QuestionRead
  error: string | null
  onReply: (reply: ReplyCreate) => void
}) {
  const { t } = useTranslation()
  const id = useId()
  const [other, setOther] = useState('')
  const heading = useRef<HTMLHeadingElement>(null)
  // A new question moves focus to itself, for screen readers, without scrolling the
  // safety steps above out of view.
  useEffect(() => {
    heading.current?.focus({ preventScroll: true })
  }, [])

  const submit = (e: SyntheticEvent) => {
    e.preventDefault()
    const text = other.trim()
    if (text) onReply({ text })
  }

  return (
    <div className="ask">
      <p className="ai-now">
        <strong>{t('ai.rightNow')}</strong>
        <span>{question.now}</span>
      </p>
      <h3 className="ask-q" ref={heading} tabIndex={-1} id={`${id}-q`}>
        {question.question}
      </h3>
      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}
      <div className="ask-options" role="group" aria-labelledby={`${id}-q`}>
        {question.options.map((option) => (
          <button
            key={option}
            type="button"
            className="chip chip-lg"
            onClick={() => {
              onReply({ option })
            }}
          >
            {option}
          </button>
        ))}
      </div>
      <form className="ask-other" onSubmit={submit}>
        <label htmlFor={`${id}-other`} className="note-label">
          {t('ai.otherLabel')}
        </label>
        <div className="ask-other-row">
          <input
            id={`${id}-other`}
            className="field"
            value={other}
            maxLength={NOTE_MAX}
            placeholder={t('ai.otherPlaceholder')}
            enterKeyHint="send"
            onChange={(e) => {
              setOther(e.target.value)
            }}
          />
          <button
            type="submit"
            className="icon-btn icon-btn-lg"
            disabled={!other.trim()}
            aria-label={t('ai.send')}
          >
            <Send size={20} aria-hidden="true" />
          </button>
        </div>
      </form>
      <button
        type="button"
        className="btn btn-quiet ask-skip"
        onClick={() => {
          onReply({ skip: true })
        }}
      >
        {t('ai.skip')}
        <ArrowRight size={20} aria-hidden="true" />
      </button>
    </div>
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
  const tile = t(`start.tiles.${key}`)
  // The checklist follows the incident as edited; this keeps what the advice was told.
  const problem = inputs.situation === 'parked' ? t('ai.problemParked', { problem: tile }) : tile
  return (
    <p>
      {inputs.vehicle
        ? t('ai.answeredFor', { vehicle: inputs.vehicle.name, problem })
        : t('ai.answeredForNoVehicle', { problem })}
    </p>
  )
}

/** Says when the advice was given without some or all of the photos (ADR 0002). */
function PhotosNotSeen({ inputs }: { inputs: TurnInputsRead }) {
  const { t } = useTranslation()
  const seen = photosSeen(inputs)
  if (!seen) return null
  return (
    <p className="photo-line photo-line-unseen">
      <CameraOff size={18} aria-hidden="true" />
      <span>
        {seen.kind === 'none'
          ? t('ai.photosNotSeen', { count: seen.total })
          : t('ai.photosPartlySeen', { seen: seen.seen, total: seen.total })}
      </span>
    </p>
  )
}

function Advice({
  advice,
  inputs,
  noVehicles,
}: {
  advice: AdviceRead
  inputs: TurnInputsRead | null
  noVehicles: boolean
}) {
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
      {inputs && <PhotosNotSeen inputs={inputs} />}

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
        {noVehicles && (
          <p className="answer-invite">
            {t('incident.addVehicle')}{' '}
            <Link to="/vehicles/new">{t('incident.addVehicleLink')}</Link>
          </p>
        )}
      </div>
    </div>
  )
}
