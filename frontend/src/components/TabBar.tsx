import { Car, History, LifeBuoy } from 'lucide-react'
import { NavLink } from 'react-router'
import { useTranslation } from 'react-i18next'

const TABS = [
  { to: '/', key: 'help', Icon: LifeBuoy, end: true },
  { to: '/incidents', key: 'history', Icon: History, end: false },
  { to: '/vehicles', key: 'vehicles', Icon: Car, end: false },
] as const

/** Bottom tab bar. Rendered on top-level screens only. */
export function TabBar() {
  const { t } = useTranslation()
  return (
    <nav className="tabbar" aria-label={t('nav.label')}>
      {TABS.map(({ to, key, Icon, end }) => (
        <NavLink key={to} to={to} end={end} className="tab">
          <Icon size={22} aria-hidden="true" />
          <span>{t(`nav.${key}`)}</span>
        </NavLink>
      ))}
    </nav>
  )
}
