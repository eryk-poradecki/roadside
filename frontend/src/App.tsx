import { useEffect, useRef, useState } from 'react'
import { dictionaries, LangContext, type Lang, type TileId } from './i18n'
import { EmergencyBar, LocationBar, useLocation } from './LocationBar'
import { Sheet } from './Sheet'
import { Result } from './Result'
import { TILE_ICONS, TILE_ORDER } from './tiles'
import { MOCK_RESULT, MOCK_SHEET } from './mock'
import { RoadMark } from './icons'

const LANG_NAMES: Record<Lang, string> = { en: 'English', pl: 'Polski' }

function initialLang(): Lang {
  const forced = new URLSearchParams(window.location.search).get('lang')
  if (forced === 'pl' || forced === 'en') return forced
  try {
    const saved = localStorage.getItem('lang')
    if (saved === 'pl' || saved === 'en') return saved
  } catch {
    /* storage unavailable */
  }
  return navigator.language?.toLowerCase().startsWith('pl') ? 'pl' : 'en'
}

export function App() {
  const [lang, setLang] = useState<Lang>(initialLang)
  const t = dictionaries[lang]
  const loc = useLocation()
  const [tile, setTile] = useState<TileId | null>(MOCK_SHEET)
  const [photo, setPhoto] = useState<File | null>(null)
  const [note, setNote] = useState('')
  const lastTile = useRef<TileId | null>(MOCK_SHEET ?? MOCK_RESULT)
  const [submitted, setSubmitted] = useState<TileId | null>(MOCK_RESULT)

  useEffect(() => {
    document.documentElement.lang = lang
    try {
      localStorage.setItem('lang', lang)
    } catch {
      /* ignore */
    }
  }, [lang])

  const submit = () => {
    if (!tile) return
    setSubmitted(tile)
    setTile(null)
  }

  // Going back keeps the photo and note; picking a different problem starts clean.
  const back = () => setSubmitted(null)

  const openTile = (id: TileId) => {
    if (submitted === null && lastTile.current && lastTile.current !== id) {
      setPhoto(null)
      setNote('')
    }
    lastTile.current = id
    setTile(id)
  }

  return (
    <LangContext.Provider value={{ lang, t }}>
      {submitted ? (
        <Result tile={submitted} onBack={back} />
      ) : (
        <main className="screen">
          <div className="screen-body">
          <header className="masthead">
            <p className="wordmark">
              <RoadMark />
              <span>Roadside</span>
            </p>
            <div className="lang" role="group" aria-label={t.language}>
              {(['en', 'pl'] as const).map((l) => (
                <button key={l} type="button" lang={l} aria-label={LANG_NAMES[l]} aria-pressed={lang === l} onClick={() => setLang(l)}>
                  {l.toUpperCase()}
                </button>
              ))}
            </div>
          </header>

          <LocationBar state={loc.state} manual={loc.manual} setManual={loc.setManual} retry={loc.retry} />

          <div className="intro">
            <h1>{t.heading}</h1>
            <p className="lede">{t.subheading}</p>
          </div>

          <ul className="tiles" aria-label={t.tilesLabel}>
            {TILE_ORDER.map((id) => {
              const Icon = TILE_ICONS[id]
              return (
                <li key={id} className={id === 'other' ? 'tile-wide' : undefined}>
                  <button type="button" className="tile" onClick={() => openTile(id)}>
                    <Icon size={28} strokeWidth={1.75} aria-hidden="true" />
                    <span>{t.tiles[id]}</span>
                  </button>
                </li>
              )
            })}
          </ul>
          </div>

          <EmergencyBar />

          <Sheet
            tile={tile}
            photo={photo}
            note={note}
            onPhoto={setPhoto}
            onNote={setNote}
            onClose={() => setTile(null)}
            onSubmit={submit}
          />
        </main>
      )}
    </LangContext.Provider>
  )
}
