import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'

export function IncidentScreen() {
  const { t } = useTranslation()
  return (
    <>
      <Link to="/incidents" className="back">
        <ArrowLeft size={20} aria-hidden="true" />
        {t('common.back')}
      </Link>
      <h1>{t('incident.heading')}</h1>
      <p className="notice">{t('incident.soon')}</p>
    </>
  )
}
