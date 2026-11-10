import { Phone } from 'lucide-react'
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

/** Layout route: masthead, the screen, and the dock (112 plus, on top-level screens, the tabs). */
export function AppShell({ dock }: { dock?: React.ReactNode }) {
  const { t } = useTranslation()
  return (
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
        <EmergencyBar />
        {dock}
      </div>
    </div>
  )
}
