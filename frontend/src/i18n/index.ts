import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'
import { en } from './en'
import { pl } from './pl'

export const LANGUAGES = ['en', 'pl'] as const
export type Language = (typeof LANGUAGES)[number]

export const resources = { en: { translation: en }, pl: { translation: pl } } as const

const syncDocumentLang = (lng: string) => {
  document.documentElement.lang = lng
}

/** Detection order: `?lang=`, then local storage (`lang`), then the browser, then English. */
export async function initI18n(): Promise<typeof i18n> {
  i18n.on('languageChanged', syncDocumentLang)
  await i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      resources,
      supportedLngs: LANGUAGES,
      nonExplicitSupportedLngs: true,
      fallbackLng: 'en',
      interpolation: { escapeValue: false },
      detection: {
        order: ['querystring', 'localStorage', 'navigator'],
        lookupQuerystring: 'lang',
        lookupLocalStorage: 'lang',
        caches: ['localStorage'],
      },
    })
  syncDocumentLang(i18n.resolvedLanguage ?? 'en')
  return i18n
}

export { i18n }
