import { ChevronDown } from 'lucide-react'

/** A panel that folds into its summary line (`.fold` in base.css). `open` is where it starts. */
export function Fold({
  summary,
  open,
  children,
}: {
  summary: string
  open: boolean
  children: React.ReactNode
}) {
  return (
    <details className="panel fold" open={open}>
      <summary>
        <span>{summary}</span>
        <ChevronDown className="fold-icon" size={20} aria-hidden="true" />
      </summary>
      <div className="fold-body">{children}</div>
    </details>
  )
}
