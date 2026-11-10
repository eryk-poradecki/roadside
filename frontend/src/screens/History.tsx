import { useTranslation } from 'react-i18next'

export function History() {
  const { t } = useTranslation()
  return (
    <>
      <h1>{t('history.heading')}</h1>
      <p className="notice">{t('history.soon')}</p>
    </>
  )
}
