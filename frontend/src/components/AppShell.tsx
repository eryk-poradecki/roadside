import { Phone, WifiOff } from 'lucide-react'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { createPortal } from 'react-dom'
import { Outlet } from 'react-router'
import { useTranslation } from 'react-i18next'
import { useOffline } from '../api/offline'
import { useDesktop } from '../lib/useMediaQuery'
import { LanguageSwitch } from './LanguageSwitch'
import { RoadMark } from './icons'
import { SideNav } from './TabBar'
import './AppShell.css'

/** The one way to render a 112 link, so the number and its label can't drift apart. */
export function EmergencyLink({ className, children }: { className: string; children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <a className={className} href="tel:112" aria-label={t('call112Label')}>
      {children}
    </a>
  )
}

/**
 * The 112 control. On mobile it renders on every screen, inside the shell, so no route can
 * omit it. Desktop has no global 112 (ADR 0012).
 */
export function EmergencyBar({ urgent = false }: { urgent?: boolean }) {
  const { t } = useTranslation()
  return (
    <EmergencyLink className={urgent ? 'sos sos-urgent' : 'sos'}>
      <Phone size={22} strokeWidth={2.25} aria-hidden="true" />
      <span>{t('callEmergency')}</span>
    </EmergencyLink>
  )
}

/**
 * Shown while the app is cut off (ADR 0008), so a failed load reads as "no signal" rather
 * than a broken app. The live region stays mounted so the change is announced.
 */
export function OfflineBanner() {
  const { t } = useTranslation()
  const offline = useOffline()
  const labelId = useId()
  return (
    <div className="offline" role="status" aria-labelledby={offline ? labelId : undefined}>
      {offline && (
        <>
          <WifiOff size={20} aria-hidden="true" />
          <p>
            <strong id={labelId}>{t('offline.label')}</strong> <span>{t('offline.body')}</span>
          </p>
        </>
      )}
    </div>
  )
}

type DockSlot = {
  node: HTMLElement | null
  urgent: boolean
  claim: () => () => void
  claimUrgent: () => () => void
}
const DockSlotContext = createContext<DockSlot | null>(null)

/**
 * A screen's primary action in the dock, in one row beside a compact 112 (the Result
 * screen's "Call <insurer>"). The shell keeps rendering 112 either way.
 */
export function DockAction({ children }: { children: ReactNode }) {
  const slot = useContext(DockSlotContext)
  const claim = slot?.claim
  useEffect(() => claim?.(), [claim])
  return slot?.node ? createPortal(children, slot.node) : null
}

/**
 * While mounted, 112 takes the dock's primary slot with its full label and the screen's
 * own action moves beside it (an `urgent` AI answer, ADR 0004).
 */
export function EmergencyFirst() {
  const claimUrgent = useContext(DockSlotContext)?.claimUrgent
  useEffect(() => claimUrgent?.(), [claimUrgent])
  return null
}

function useCounter() {
  const [count, setCount] = useState(0)
  const claim = useCallback(() => {
    setCount((n) => n + 1)
    return () => {
      setCount((n) => n - 1)
    }
  }, [])
  return [count > 0, claim] as const
}

/** True while 112 leads the dock, so a `DockAction` can render as the secondary action. */
export const useDockUrgent = () => useContext(DockSlotContext)?.urgent ?? false

function Wordmark() {
  const { t } = useTranslation()
  return (
    <p className="wordmark">
      <RoadMark />
      <span>{t('appName')}</span>
    </p>
  )
}

/**
 * Layout route. Mobile: masthead, the screen, and the dock (112 plus, on top-level screens,
 * the tabs). Desktop (ADR 0012): a sidebar on every route beside the screen, with no dock and
 * no global 112; `dock` is ignored there. Both layouts keep `<main>` at the same place in the
 * tree, so crossing the breakpoint doesn't remount the screen and lose what was typed.
 */
export function AppShell({ dock }: { dock?: ReactNode }) {
  const desktop = useDesktop()
  const [claimed, claim] = useCounter()
  const [urgent, claimUrgent] = useCounter()
  const [node, setNode] = useState<HTMLElement | null>(null)
  const slot = useMemo(
    () => ({ node, urgent, claim, claimUrgent }),
    [node, urgent, claim, claimUrgent],
  )

  return (
    <DockSlotContext.Provider value={slot}>
      <div className={desktop ? 'desk' : 'shell'}>
        {desktop ? (
          <aside className="desk-side">
            <Wordmark />
            <SideNav />
            <LanguageSwitch />
          </aside>
        ) : (
          <header className="masthead">
            <Wordmark />
            <LanguageSwitch />
          </header>
        )}
        <div className={desktop ? 'desk-main' : 'shell-main'}>
          <OfflineBanner />
          <main className="shell-body">
            <Outlet />
          </main>
          {!desktop && (
            <div className="shell-dock">
              {claimed ? (
                // Fixed child positions keep the slot node mounted when `urgent` flips.
                <div className={urgent ? 'dock dock-urgent' : 'dock'}>
                  {urgent && <EmergencyBar urgent />}
                  <div className="dock-main" ref={setNode} />
                  {!urgent && (
                    <EmergencyLink className="sos-compact">
                      <Phone size={20} strokeWidth={2.25} aria-hidden="true" />
                      112
                    </EmergencyLink>
                  )}
                </div>
              ) : (
                <EmergencyBar urgent={urgent} />
              )}
              {dock}
            </div>
          )}
        </div>
      </div>
    </DockSlotContext.Provider>
  )
}
