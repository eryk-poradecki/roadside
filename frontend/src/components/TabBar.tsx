import { Car, History, LifeBuoy } from 'lucide-react'
import { NavLink } from 'react-router'
import { useTranslation } from 'react-i18next'

/** The three sections. A flow screen's route sits under its section, so its link stays current. */
const SECTIONS = [
  { to: '/', key: 'help', Icon: LifeBuoy, end: true },
  { to: '/incidents', key: 'history', Icon: History, end: false },
  { to: '/vehicles', key: 'vehicles', Icon: Car, end: false },
] as const

function MainNav({
  className,
  item,
  iconSize,
}: {
  className: string
  item: string
  iconSize: number
}) {
  const { t } = useTranslation()
  return (
    <nav className={className} aria-label={t('nav.label')}>
      {SECTIONS.map(({ to, key, Icon, end }) => (
        <NavLink key={to} to={to} end={end} className={item}>
          <Icon size={iconSize} aria-hidden="true" />
          <span>{t(`nav.${key}`)}</span>
        </NavLink>
      ))}
    </nav>
  )
}

/** Bottom tab bar (mobile). Rendered on top-level screens only. */
export function TabBar() {
  return <MainNav className="tabbar" item="tab" iconSize={22} />
}

/** The desktop sidebar's navigation, on every route (ADR 0012). */
export function SideNav() {
  return <MainNav className="sidenav" item="sidenav-item" iconSize={20} />
}
