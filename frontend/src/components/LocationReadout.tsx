import { Loader, Locate, MapPin } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { GeoState } from '../lib/geolocation'
import './LocationReadout.css'

const EMPTY = '––.–––––'
/** Beyond this, a fix (often Wi-Fi or IP based on a laptop) is shown as approximate. */
const APPROXIMATE_M = 1000

/**
 * Dashboard-style readout of the detected location: the numbers are the instrument.
 * `onRetry` is left out where the browser has no geolocation, so no button does nothing.
 */
export function LocationReadout({ geo, onRetry }: { geo: GeoState; onRetry?: () => void }) {
  const { t } = useTranslation()
  const found = geo.status === 'found' ? geo : null
  // A rough fix keeps two decimals (about 1 km) so the numbers don't claim metre precision.
  const approximate = found !== null && found.accuracy > APPROXIMATE_M
  const digits = approximate ? 2 : 5
  const label = {
    detecting: t('location.detecting'),
    found: approximate ? t('location.approximate') : t('location.found'),
    denied: t('location.denied'),
    unavailable: t('location.unavailable'),
  }[geo.status]
  const Icon = geo.status === 'detecting' ? Loader : found ? Locate : MapPin

  return (
    <section className={`readout readout-${geo.status}`} aria-label={t('location.label')}>
      <div className="readout-head">
        <p className="readout-label" role="status">
          <Icon
            size={20}
            aria-hidden="true"
            className={geo.status === 'detecting' ? 'spin' : found ? 'fix' : undefined}
          />
          <span>{label}</span>
        </p>
        {onRetry && (geo.status === 'denied' || geo.status === 'unavailable') && (
          <button type="button" className="link-btn readout-action" onClick={onRetry}>
            {t('location.retry')}
          </button>
        )}
      </div>
      <div className="coords" aria-hidden={!found}>
        <p className="coord">
          <span>{found ? Math.abs(found.lat).toFixed(digits) : EMPTY}</span>
          <small>° {t(found && found.lat < 0 ? 'location.south' : 'location.north')}</small>
        </p>
        <p className="coord">
          <span>{found ? Math.abs(found.lon).toFixed(digits) : EMPTY}</span>
          <small>° {t(found && found.lon < 0 ? 'location.west' : 'location.east')}</small>
        </p>
      </div>
      {found ? (
        <p className="readout-foot">
          {approximate
            ? t('location.approximateWithin', { km: Math.round(found.accuracy / 1000) })
            : t('location.accuracy', { meters: Math.round(found.accuracy) })}
        </p>
      ) : (
        geo.status !== 'detecting' && <p className="readout-foot">{t('location.noFix')}</p>
      )}
    </section>
  )
}
