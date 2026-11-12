import { Smartphone } from 'lucide-react'
import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useVehicles } from '../api/vehicles'
import { EmergencyBar } from '../components/AppShell'
import { HelpSheet } from '../components/HelpSheet'
import { LocationReadout } from '../components/LocationReadout'
import { QrCode } from '../components/QrCode'
import { TILE_ICONS } from '../components/tiles'
import { useGeolocation } from '../lib/geolocation'
import { phoneReachable } from '../lib/phoneReachable'
import { PROBLEM_TYPES, problemKey, type ProblemType } from '../lib/problemType'
import { useDesktop } from '../lib/useMediaQuery'
import { uuid } from '../lib/uuid'
import './Start.css'

type HelpRequest = { type: ProblemType; key: string }
type FlowState = {
  request: HelpRequest | null
  setRequest: (request: HelpRequest | null) => void
}

/**
 * `/`. Mobile: the help flow. Desktop (ADR 0012): a QR code to open the app on a phone,
 * beside the same flow in a narrow column to try it here. Where a phone couldn't open this
 * address (localhost, a private IP) a short "how it works" takes the QR code's place.
 */
export function Start() {
  const { t } = useTranslation()
  const desktop = useDesktop()
  const headingId = useId()
  // The idempotency key of the help request in progress. Reopening the same tile after a
  // failed or lost attempt keeps it, so the retry can't create a second incident. Another
  // problem type is a new help request, and a success ends this one. Held here, not in the
  // flow, so it survives the flow moving into the desktop column when the window is resized.
  const [request, setRequest] = useState<HelpRequest | null>(null)
  const flow = { request, setRequest }
  if (!desktop) return <HelpFlow {...flow} />

  const origin = window.location.origin
  const qr = phoneReachable(window.location.hostname)
  return (
    <div className="start-desk">
      {qr ? (
        <section className="start-side">
          <h1>{t('start.desktop.qrHeading')}</h1>
          <p className="lede">{t('start.desktop.qrBody')}</p>
          <QrCode value={origin} label={t('start.desktop.qrLabel', { url: origin })} />
          <p className="start-origin">{window.location.host}</p>
        </section>
      ) : (
        <HowItWorks />
      )}
      <section className="start-try" aria-labelledby={headingId}>
        <h2 id={headingId}>{qr ? t('start.desktop.tryHere') : t('start.desktop.tryHereSolo')}</h2>
        <TrialColumn {...flow} />
      </section>
    </div>
  )
}

/**
 * Where a phone couldn't open this address (localhost, a private IP): what the flow does at
 * the roadside, in the QR code's place, so the trial column has its context.
 */
function HowItWorks() {
  const { t } = useTranslation()
  const headingId = useId()
  const steps = t('start.desktop.howSteps', { returnObjects: true })
  return (
    <section className="start-side" aria-labelledby={headingId}>
      <h1 id={headingId}>{t('start.desktop.howHeading')}</h1>
      <ol className="how-steps">
        {steps.map((step, n) => (
          <li key={step.title}>
            <span className="how-n" aria-hidden="true">
              {n + 1}
            </span>
            <span className="how-text">
              <strong>{step.title}</strong>
              <span>{step.body}</span>
            </span>
          </li>
        ))}
      </ol>
      <p className="how-hint">
        <Smartphone size={18} aria-hidden="true" />
        {t('start.desktop.howHint')}
      </p>
    </section>
  )
}

/**
 * The mobile flow at phone width, with its own 112: desktop has no global one (ADR 0012).
 * It leads the column (DESIGN.md allows 112 above the tiles), so no window height hides it.
 */
function TrialColumn(flow: FlowState) {
  return (
    <div className="trial">
      <EmergencyBar />
      <HelpFlow {...flow} sub />
    </div>
  )
}

/**
 * Problem-type tiles, the detected location, and the help sheet behind each tile. `sub` when
 * it sits under a desktop page heading, so its own heading steps down a level.
 */
function HelpFlow({ request, setRequest, sub = false }: FlowState & { sub?: boolean }) {
  const { t } = useTranslation()
  const Heading = sub ? 'h2' : 'h1'
  const vehicles = useVehicles().data ?? []
  const geo = useGeolocation()
  const [picked, setPicked] = useState<ProblemType | null>(null)
  const [opened, setOpened] = useState(0)
  // The tile label follows the default vehicle; the sheet follows the one picked there.
  const defaultFuel = vehicles.find((v) => v.is_default)?.fuel_type

  return (
    <>
      <LocationReadout geo={geo.state} onRetry={geo.supported ? geo.retry : undefined} />
      <div className="intro">
        <Heading className="intro-heading">{t('start.heading')}</Heading>
        <p className="lede">{t('start.subheading')}</p>
      </div>
      <ul className="tiles" aria-label={t('start.tilesLabel')}>
        {PROBLEM_TYPES.map((type) => {
          const key = problemKey(type, defaultFuel)
          const Icon = TILE_ICONS[key]
          return (
            <li key={type} className={type === 'other' ? 'tile-wide' : undefined}>
              <button
                type="button"
                className="tile"
                onClick={() => {
                  if (request?.type !== type) setRequest({ type, key: uuid() })
                  setPicked(type)
                  setOpened((n) => n + 1)
                }}
              >
                <Icon size={28} strokeWidth={1.75} aria-hidden="true" />
                <span>{t(`start.tiles.${key}`)}</span>
              </button>
            </li>
          )
        })}
      </ul>
      {picked && request && (
        <HelpSheet
          key={opened}
          problemType={picked}
          vehicles={vehicles}
          geo={geo.state}
          idempotencyKey={request.key}
          onCreated={() => {
            setRequest(null)
          }}
          onClose={() => {
            setPicked(null)
          }}
        />
      )}
    </>
  )
}
