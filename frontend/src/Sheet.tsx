import { useEffect, useId, useRef, useState } from 'react'
import { ImagePlus, X } from 'lucide-react'
import { useT, type TileId } from './i18n'
import { TILE_ICONS } from './tiles'

type Props = {
  tile: TileId | null
  photo: File | null
  note: string
  onPhoto: (f: File | null) => void
  onNote: (s: string) => void
  onClose: () => void
  onSubmit: () => void
}

const NOTE_MAX = 160

export function Sheet({ tile, photo, note, onPhoto, onNote, onClose, onSubmit }: Props) {
  const t = useT()
  const ref = useRef<HTMLDialogElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const titleRef = useRef<HTMLHeadingElement>(null)
  const dragRef = useRef<{ y: number } | null>(null)
  const [dy, setDy] = useState(0)
  const [url, setUrl] = useState<string | null>(null)
  const titleId = useId()
  const noteId = useId()
  const open = tile !== null
  const shownTile = useRef<TileId>('other')
  if (tile) shownTile.current = tile
  const Icon = TILE_ICONS[shownTile.current]

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) {
      setDy(0)
      d.showModal()
      titleRef.current?.focus()
    } else if (!open && d.open) {
      d.close()
    }
  }, [open])

  useEffect(() => {
    if (!photo) {
      setUrl(null)
      return
    }
    const u = URL.createObjectURL(photo)
    setUrl(u)
    return () => URL.revokeObjectURL(u)
  }, [photo])

  const onPointerDown = (e: React.PointerEvent) => {
    dragRef.current = { y: e.clientY }
    e.currentTarget.setPointerCapture(e.pointerId)
  }
  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragRef.current) return
    setDy(Math.max(0, e.clientY - dragRef.current.y))
  }
  const onPointerUp = () => {
    if (!dragRef.current) return
    dragRef.current = null
    if (dy > 90) onClose()
    else setDy(0)
  }

  return (
    <dialog
      ref={ref}
      className="sheet"
      aria-labelledby={titleId}
      style={dy ? { transform: `translateY(${dy}px)`, transition: 'none' } : undefined}
      onCancel={(e) => {
        e.preventDefault()
        onClose()
      }}
      onClick={(e) => {
        if (e.target === ref.current) onClose()
      }}
    >
      <div
        className="sheet-grab"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        title={t.sheet.dragHint}
      >
        <span className="sheet-handle" aria-hidden="true" />
      </div>

      <div className="sheet-body">
        <header className="sheet-head">
          <span className="sheet-icon" aria-hidden="true">
            <Icon size={26} strokeWidth={1.75} />
          </span>
          <h2 id={titleId} ref={titleRef} tabIndex={-1}>{t.tiles[shownTile.current]}</h2>
          <a className="sos-chip" href="tel:112" aria-label={t.call112Label}>
            112
          </a>
          <button type="button" className="icon-btn" onClick={onClose} aria-label={t.sheet.close}>
            <X size={22} aria-hidden="true" />
          </button>
        </header>

        <p className="sheet-intro">{t.sheet.intro}</p>

        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => {
            onPhoto(e.target.files?.[0] ?? null)
            e.target.value = ''
          }}
        />

        {url ? (
          <div className="photo-row">
            <img className="photo-thumb" src={url} alt={t.sheet.photoAlt} />
            <button type="button" className="btn btn-quiet" onClick={() => onPhoto(null)}>
              <X size={18} aria-hidden="true" />
              {t.sheet.removePhoto}
            </button>
          </div>
        ) : (
          <button type="button" className="photo-add" onClick={() => fileRef.current?.click()}>
            <ImagePlus size={24} strokeWidth={1.75} aria-hidden="true" />
            <span className="photo-add-text">
              <strong>{t.sheet.addPhoto}</strong>
              <small>{t.sheet.photoHint}</small>
            </span>
          </button>
        )}

        <label className="note-label" htmlFor={noteId}>
          {t.sheet.noteLabel}
        </label>
        <textarea
          id={noteId}
          className="field"
          rows={2}
          maxLength={NOTE_MAX}
          placeholder={t.sheet.notePlaceholder}
          value={note}
          onChange={(e) => onNote(e.target.value)}
        />
        {note.length > 0 && (
          <p className="note-count" aria-hidden="true">
            {note.length}/{NOTE_MAX}
          </p>
        )}

      </div>

      <div className="sheet-actions">
        <button type="button" className="btn btn-primary" onClick={onSubmit}>
          {t.sheet.getHelp}
        </button>
        <p className="sheet-foot">{t.sheet.vehicleNote}</p>
</div>
    </dialog>
  )
}
