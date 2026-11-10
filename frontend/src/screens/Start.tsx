import { useTranslation } from 'react-i18next'
import { TILE_ICONS, TILE_ORDER } from '../components/tiles'
import './Start.css'

/** Placeholder for the help flow: the tiles are the prototype's, wired up in a later ticket. */
export function Start() {
  const { t } = useTranslation()
  return (
    <>
      <div className="intro">
        <h1>{t('start.heading')}</h1>
        <p className="lede">{t('start.subheading')}</p>
      </div>
      <ul className="tiles" aria-label={t('start.tilesLabel')}>
        {TILE_ORDER.map((id) => {
          const Icon = TILE_ICONS[id]
          return (
            <li key={id} className={id === 'other' ? 'tile-wide' : undefined}>
              <button type="button" className="tile" disabled>
                <Icon size={28} strokeWidth={1.75} aria-hidden="true" />
                <span>{t(`start.tiles.${id}`)}</span>
              </button>
            </li>
          )
        })}
      </ul>
      <p className="notice">{t('start.soon')}</p>
    </>
  )
}
