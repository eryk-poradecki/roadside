import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ArrowLeft, Camera, CameraOff, Car, Check, ChevronDown, CircleCheck, Loader, MapPin, Phone, RotateCw, Send, Sparkles, WifiOff } from 'lucide-react'
import { useLang, useT, type TileId } from './i18n'
import { AI_DELAY_MS, MOCK_AI, MOCK_PLACES, MOCK_RESOLVED, MOCK_VEHICLE, SHOW_DEMO, TURN_DELAY_MS } from './mock'
import { aiContent, resolveSteps, VEHICLES, type AiAnswer, type ClarifyRound, type Confidence, type MockVehicle } from './mockAi'
import { Nearby } from './Nearby'
import { TILE_ICONS } from './tiles'

type Phase = 'loading' | 'error' | 'asking' | 'thinking' | 'answer'
type Turn = { question: string; answer: string }

const MAX_ROUNDS = 2

function useAiFlow(rounds: ClarifyRound[]) {
  const prefilled = MOCK_AI === 'answered-after-question'
  const [phase, setPhase] = useState<Phase>(prefilled ? 'answer' : 'loading')
  const [round, setRound] = useState(0)
  const [history, setHistory] = useState<Turn[]>(() =>
    prefilled ? rounds.slice(0, MAX_ROUNDS).map((r) => ({ question: r.question, answer: r.options[0] })) : [],
  )
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (phase !== 'loading' || MOCK_AI === 'loading') return
    const next: Phase = MOCK_AI === 'error' && attempt === 0 ? 'error' : MOCK_AI === 'asking' ? 'asking' : 'answer'
    const id = window.setTimeout(() => setPhase(next), AI_DELAY_MS)
    return () => window.clearTimeout(id)
  }, [phase, attempt])

  useEffect(() => {
    if (phase !== 'thinking') return
    const id = window.setTimeout(() => setPhase(round < Math.min(rounds.length, MAX_ROUNDS) ? 'asking' : 'answer'), TURN_DELAY_MS)
    return () => window.clearTimeout(id)
  }, [phase, round, rounds.length])

  const answer = (text: string) => {
    setHistory((h) => [...h, { question: rounds[round].question, answer: text }])
    setRound((r) => r + 1)
    setPhase('thinking')
  }
  const retry = () => {
    setAttempt((n) => n + 1)
    setPhase('loading')
  }
  return { phase, round, history, answer, retry }
}

export function Result({ tile, onBack }: { tile: TileId; onBack: () => void }) {
  const t = useT()
  const r = t.result
  const lang = useLang()
  const { rounds, answer } = aiContent(lang, tile, MOCK_AI === 'unsure')
  const ai = useAiFlow(rounds)
  const vehicle = MOCK_VEHICLE === 'none' ? null : VEHICLES[MOCK_VEHICLE]
  const assistance = vehicle?.assistancePhone ?? null
  const [resolved, setResolved] = useState(MOCK_RESOLVED)
  const aiArrived = ai.phase === 'asking' || ai.phase === 'thinking' || ai.phase === 'answer'
  const [checklistOpen, setChecklistOpen] = useState<boolean | null>(null)
  const showChecklist = checklistOpen ?? !aiArrived
  // While a clarifying question is open, its own "Right now" step covers safety,
  // so the whole block folds to one line to keep the question and chips above the dock.
  const asking = ai.phase === 'asking' || ai.phase === 'thinking'
  const [blockOpen, setBlockOpen] = useState(false)
  const blockFolded = asking && !blockOpen
  useEffect(() => {
    if (!asking) setBlockOpen(false)
  }, [asking])
  const aiRef = useRef<HTMLElement>(null)
  const TileIcon = TILE_ICONS[tile]
  const hasLocation = MOCK_PLACES !== 'noloc'

  useEffect(() => {
    if (ai.phase !== 'error') return
    const id = requestAnimationFrame(() => aiRef.current?.scrollIntoView({ block: 'end' }))
    return () => cancelAnimationFrame(id)
  }, [ai.phase])

  const resolve = <ResolveControl resolved={resolved} onChange={setResolved} primary={!assistance} />

  return (
    <main className="screen result">
      <div className="screen-body">
        <div className="topbar">
          <button type="button" className="btn btn-quiet back" onClick={onBack}>
            <ArrowLeft size={20} aria-hidden="true" />
            {r.back}
          </button>
          <p className={resolved ? 'status status-resolved' : 'status'}>
            {resolved ? <CircleCheck size={16} aria-hidden="true" /> : <Check size={16} aria-hidden="true" />}
            {resolved ? r.resolved : r.saved}
          </p>
        </div>

        <header className="result-head">
          <h1>
            <TileIcon size={30} strokeWidth={1.75} aria-hidden="true" />
            {t.tiles[tile]}
          </h1>
          <p className="result-meta">
            {vehicle && (
              <span>
                <Car size={18} aria-hidden="true" />
                {vehicle.name}
              </span>
            )}
            {hasLocation && (
              <span>
                <MapPin size={18} aria-hidden="true" />
                {t.loc.mockPlace}
              </span>
            )}
          </p>
          {SHOW_DEMO && <p className="demo">{t.demo}</p>}
        </header>

        <section className="panel" aria-labelledby="cl-title">
          <div className="panel-head">
            <h2 id="cl-title">{r.firstLabel}</h2>
            <span className="badge">{r.checklistBadge}</span>
          </div>
          {blockFolded ? (
            <button type="button" className="disclosure disclosure-solo" aria-expanded={false} onClick={() => setBlockOpen(true)}>
              <span>{r.safetySummary(t.checklists[tile].length + 1)}</span>
              <span className="disclosure-act">
                {r.show}
                <ChevronDown size={18} aria-hidden="true" />
              </span>
            </button>
          ) : (
          <>
          <p className="first-step">
            <span className="check check-first" aria-hidden="true">
              1
            </span>
            <span>{t.firstStep[tile]}</span>
          </p>

          {aiArrived && (
            <button type="button" className="disclosure" aria-expanded={showChecklist} aria-controls="checklist" onClick={() => setChecklistOpen(!showChecklist)}>
              <span>{r.checklistSummary(t.checklists[tile].length)}</span>
              <span className="disclosure-act">
                {showChecklist ? r.hide : r.show}
                <ChevronDown size={18} aria-hidden="true" className={showChecklist ? 'flip' : undefined} />
              </span>
            </button>
          )}
          {showChecklist && (
            <div id="checklist" className="checklist-wrap">
              {!aiArrived && <h3 className="then">{r.checklistTitle}</h3>}
              <ol className="checklist">
                {t.checklists[tile].map((item, i) => (
                  <li key={item}>
                    <span className="check" aria-hidden="true">
                      {i + 2}
                    </span>
                    <span>{item}</span>
                  </li>
                ))}
              </ol>
              <p className="placeholder-note">{r.placeholderNote}</p>
            </div>
          )}
          </>
          )}
        </section>

        <section className="panel panel-ai" aria-labelledby="ai-title" ref={aiRef}>
          <div className="panel-head">
            <h2 id="ai-title">{r.aiTitle}</h2>
            <span className="badge badge-ai">
              <Sparkles size={14} aria-hidden="true" />
              {r.aiBadge}
            </span>
          </div>

          {ai.history.length > 0 && (
            <ul className="turns" aria-label={r.youAnswered}>
              {ai.history.map((h) => (
                <li key={h.question} className="turn-done">
                  <span>{h.question}</span>
                  <strong>{h.answer}</strong>
                </li>
              ))}
            </ul>
          )}

          <div aria-live="polite" className="ai-body">
            {ai.phase === 'loading' && (
              <div className="ai-loading">
                <p className="ai-line">
                  <Loader size={20} className="spin" aria-hidden="true" />
                  {r.aiLoading}
                </p>
                <p className="muted">{r.aiLoadingSub}</p>
                <div className="skeleton" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </div>
              </div>
            )}
            {ai.phase === 'thinking' && (
              <p className="ai-line">
                <Loader size={20} className="spin" aria-hidden="true" />
                {r.thinking}
              </p>
            )}
            {ai.phase === 'asking' && <Ask round={rounds[ai.round]} onAnswer={ai.answer} />}
            {ai.phase === 'answer' && <Answer answer={answer} vehicle={vehicle} />}
            {ai.phase === 'error' && (
              <div className="ai-error">
                <p className="ai-line">
                  <WifiOff size={20} aria-hidden="true" />
                  <strong>{r.aiErrorTitle}</strong>
                </p>
                <p className="muted">{r.aiErrorBody}</p>
                <button type="button" className="btn btn-quiet" onClick={ai.retry}>
                  <RotateCw size={20} aria-hidden="true" />
                  {r.retry}
                </button>
              </div>
            )}
          </div>
        </section>

        <Nearby tile={tile} />

        {assistance && <div className="resolve-inline">{resolve}</div>}
      </div>

      <div className="dock">
        <div className="dock-main">
          {assistance ? (
            <a className="btn btn-primary" href={`tel:${assistance}`}>
              <Phone size={20} aria-hidden="true" />
              {r.callAssistance(vehicle?.insurer ?? null)}
            </a>
          ) : (
            resolve
          )}
        </div>
        <a className="sos-compact" href="tel:112" aria-label={r.call112}>
          <Phone size={20} strokeWidth={2.25} aria-hidden="true" />
          112
        </a>
      </div>
    </main>
  )
}

function ResolveControl({ resolved, onChange, primary }: { resolved: boolean; onChange: (v: boolean) => void; primary: boolean }) {
  const r = useT().result
  if (resolved)
    return (
      <div className="resolved-row" role="status">
        <CircleCheck size={20} aria-hidden="true" />
        <span>{r.resolvedNote}</span>
        <button type="button" className="link-btn" onClick={() => onChange(false)}>
          {r.reopen}
        </button>
      </div>
    )
  return (
    <button type="button" className={primary ? 'btn btn-primary' : 'btn btn-quiet btn-block'} onClick={() => onChange(true)}>
      <CircleCheck size={20} aria-hidden="true" />
      {r.markResolved}
    </button>
  )
}

function Ask({ round, onAnswer }: { round: ClarifyRound; onAnswer: (a: string) => void }) {
  const r = useT().result
  const [other, setOther] = useState('')
  const qRef = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    qRef.current?.focus()
  }, [round])
  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (other.trim()) onAnswer(other.trim())
  }
  return (
    <div className="ask">
      <p className="ai-now">
        <strong>{r.rightNow}</strong>
        <span>{round.now}</span>
      </p>
      <h3 className="ask-q" ref={qRef} tabIndex={-1} id="ask-q">
        {round.question}
      </h3>
      <div className="ask-options" role="group" aria-labelledby="ask-q">
        {round.options.map((o) => (
          <button key={o} type="button" className="chip chip-lg" onClick={() => onAnswer(o)}>
            {o}
          </button>
        ))}
      </div>
      <form className="ask-other" onSubmit={submit}>
        <label htmlFor="ask-other" className="note-label">
          {r.otherLabel}
        </label>
        <div className="ask-other-row">
          <input id="ask-other" className="field" value={other} maxLength={80} placeholder={r.otherPlaceholder} onChange={(e) => setOther(e.target.value)} enterKeyHint="send" />
          <button type="submit" className="icon-btn icon-btn-lg" disabled={!other.trim()} aria-label={r.send}>
            <Send size={20} aria-hidden="true" />
          </button>
        </div>
      </form>
    </div>
  )
}

function ConfidenceMark({ c }: { c: Confidence }) {
  const r = useT().result
  const level = c === 'likely' ? 3 : c === 'possible' ? 2 : 1
  return (
    <span className={`conf conf-${c}`} aria-label={`${r.confidenceLabel}: ${r.confidence[c]}`}>
      <span className="conf-bars" aria-hidden="true">
        {[1, 2, 3].map((n) => (
          <i key={n} className={n <= level ? 'on' : undefined} />
        ))}
      </span>
      {r.confidence[c]}
    </span>
  )
}

function Answer({ answer: a, vehicle }: { answer: AiAnswer; vehicle: MockVehicle | null }) {
  const r = useT().result
  const lang = useLang()
  const steps = resolveSteps(a.steps, vehicle)
  const vehicleLine = vehicle
    ? [vehicle.name, vehicle.tyreSize, vehicle.spare?.[lang], vehicle.lockKey?.[lang]].filter(Boolean).join(' · ')
    : null
  return (
    <div className="answer">
      <div className="dx">
        <div className="dx-head">
          <span className="dx-label">{r.dxLabel[a.confidence]}</span>
          <ConfidenceMark c={a.confidence} />
        </div>
        <p className="dx-cause">{a.cause}</p>
        {a.alternatives.length > 0 && (
          <div className="dx-alt">
            <span>{r.alsoCould}</span>
            <ul>
              {a.alternatives.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <p className="photo-line">
        {a.photos.seen > 0 ? <Camera size={18} aria-hidden="true" /> : <CameraOff size={18} aria-hidden="true" />}
        <span>
          {a.photos.seen > 0 ? (
            <>
              <strong>{r.photosSeen(a.photos.seen)}.</strong> {a.photos.observed}
              {a.photos.notSeen > 0 && <span className="muted"> {r.photosNotSeen(a.photos.notSeen)}.</span>}
            </>
          ) : (
            r.photosNone
          )}
        </span>
      </p>

      <div className="steps-block">
        <h3>{r.stepsTitle}</h3>
        <ol className="steps">
          {steps.map((s, i) => (
            <li key={s}>
              <span className="step-n" aria-hidden="true">
                {i + 1}
              </span>
              <span>{s}</span>
            </li>
          ))}
        </ol>
      </div>

      {a.escalate.length > 0 && (
        <div className="escalate">
          <h3>{r.escalateTitle}</h3>
          <ul>
            {a.escalate.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="answer-foot">
        <p>{vehicleLine ? `${r.answeredFor} ${vehicleLine}` : r.noVehicle}</p>
        <p>{r.disclaimer}</p>
      </div>
    </div>
  )
}
