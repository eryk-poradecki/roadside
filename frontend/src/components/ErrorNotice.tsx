import { useTranslation } from 'react-i18next'
import { isApiError } from '../api/client'
import { en } from '../i18n/en'

type ErrorKey = keyof typeof en.errors

const isErrorKey = (reason: string): reason is ErrorKey => reason in en.errors

/** The message for an error, chosen by `reason`. The server's `detail` is never used. */
export function useErrorMessage() {
  const { t } = useTranslation()
  return (error: unknown): string => {
    const reason = isApiError(error) ? error.reason : 'generic'
    return t(`errors.${isErrorKey(reason) ? reason : 'generic'}`)
  }
}

export function ErrorNotice({ error }: { error: unknown }) {
  const message = useErrorMessage()
  return (
    <p className="notice notice-error" role="alert">
      {message(error)}
    </p>
  )
}
