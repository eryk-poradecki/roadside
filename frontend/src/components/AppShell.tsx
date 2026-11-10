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

/** The 112 control. It renders on every screen, inside the shell, so no route can omit it. */
export function EmergencyBar() {
  const { t } = useTranslation()
  return (
    <a className="sos" href="tel:112" aria-label={t('call112Label')}>
      <Phone size={22} strokeWidth={2.25} aria-hidden="true" />
      <span>{t('callEmergency')}</span>
    </a>
  )
}

type DockSlot = { node: HTMLElement | null; claim: () => () => void }
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

/** Layout route: masthead, the screen, and the dock (112 plus, on top-level screens, the tabs). */
export function AppShell({ dock }: { dock?: ReactNode }) {
  const { t } = useTranslation()
  const [claims, setClaims] = useState(0)
  const [node, setNode] = useState<HTMLElement | null>(null)
  const claim = useCallback(() => {
    setClaims((n) => n + 1)
    return () => {
      setClaims((n) => n - 1)
    }
  }, [])
  const slot = useMemo(() => ({ node, claim }), [node, claim])

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
          {claims > 0 ? (
            <div className="dock">
              <div className="dock-main" ref={setNode} />
              <a className="sos-compact" href="tel:112" aria-label={t('call112Label')}>
                <Phone size={20} strokeWidth={2.25} aria-hidden="true" />
                112
              </a>
            </div>
          ) : (
            <EmergencyBar />
          )}
          {dock}
        </div>
      </div>
    </DockSlotContext.Provider>
  )
}
