import { Phone } from 'lucide-react'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { createPortal } from 'react-dom'
import { Outlet } from 'react-router'
import { useTranslation } from 'react-i18next'
import { LanguageSwitch } from './LanguageSwitch'
import { RoadMark } from './icons'
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

/** The 112 control. It renders on every screen, inside the shell, so no route can omit it. */
export function EmergencyBar({ urgent = false }: { urgent?: boolean }) {
  const { t } = useTranslation()
  return (
    <EmergencyLink className={urgent ? 'sos sos-urgent' : 'sos'}>
      <Phone size={22} strokeWidth={2.25} aria-hidden="true" />
      <span>{t('callEmergency')}</span>
    </EmergencyLink>
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

/** Layout route: masthead, the screen, and the dock (112 plus, on top-level screens, the tabs). */
export function AppShell({ dock }: { dock?: ReactNode }) {
  const { t } = useTranslation()
  const [claimed, claim] = useCounter()
  const [urgent, claimUrgent] = useCounter()
  const [node, setNode] = useState<HTMLElement | null>(null)
  const slot = useMemo(
    () => ({ node, urgent, claim, claimUrgent }),
    [node, urgent, claim, claimUrgent],
  )

  return (
    <DockSlotContext.Provider value={slot}>
      <div className="shell">
        <header className="masthead">
          <p className="wordmark">
            <RoadMark />
            <span>{t('appName')}</span>
          </p>
          <LanguageSwitch />
        </header>
        <main className="shell-body">
          <Outlet />
        </main>
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
      </div>
    </DockSlotContext.Provider>
  )
}
