import type { ReactNode } from 'react'
import type { Color, Counts } from '../api'

export const COLOR_LABEL: Record<Color, string> = { green: 'Verde', yellow: 'Amarillo', red: 'Rojo' }
export const COLOR_BG: Record<Color, string> = { green: 'bg-go', yellow: 'bg-warn', red: 'bg-stop' }
export const COLOR_SOFT: Record<Color, string> = {
  green: 'border-go/30 bg-go/5',
  yellow: 'border-warn/40 bg-warn/5',
  red: 'border-stop/40 bg-stop/5',
}

export function Dot({ color, className = '' }: { color: Color; className?: string }) {
  return <span className={`inline-block size-3 shrink-0 rounded-full ${COLOR_BG[color]} ${className}`} aria-label={COLOR_LABEL[color]} />
}

export function CountsBar({ counts, className = '' }: { counts: Counts; className?: string }) {
  const total = counts.green + counts.yellow + counts.red || 1
  return (
    <div className={`flex h-2 w-full overflow-hidden rounded-full bg-stone-200 dark:bg-stone-800 ${className}`}>
      {(['red', 'yellow', 'green'] as Color[]).map((c) => (
        <div key={c} className={COLOR_BG[c]} style={{ width: `${(100 * counts[c]) / total}%` }} title={`${COLOR_LABEL[c]}: ${counts[c]}`} />
      ))}
    </div>
  )
}

export function scoreColor(score: number): Color {
  return score >= 75 ? 'green' : score >= 50 ? 'yellow' : 'red'
}

export function Score({ score, size = 'md' }: { score: number; size?: 'sm' | 'md' }) {
  const c = scoreColor(score)
  const dims = size === 'sm' ? 'size-10 text-sm' : 'size-16 text-xl'
  const ring = { green: 'ring-go', yellow: 'ring-warn', red: 'ring-stop' }[c]
  return (
    <div className={`flex ${dims} shrink-0 items-center justify-center rounded-full font-bold ring-4 ${ring}`} title="Puntuación 0–100 (más alto = mejor para ti)">
      {score}
    </div>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-stone-200 bg-white p-4 shadow-sm dark:border-stone-800 dark:bg-stone-900 ${className}`}>{children}</div>
}

export function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm transition ${
        active
          ? 'border-stone-900 bg-stone-900 text-white dark:border-stone-100 dark:bg-stone-100 dark:text-stone-900'
          : 'border-stone-300 hover:border-stone-500 dark:border-stone-700'
      }`}
    >
      {children}
    </button>
  )
}

export function fmtDate(iso: string | null | undefined, withTime = false): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('es', withTime ? { dateStyle: 'medium', timeStyle: 'short' } : { dateStyle: 'medium' })
}

export function fmtSnapshot(ts: string | null): string {
  return ts ? `${ts.slice(0, 4)}-${ts.slice(4, 6)}-${ts.slice(6, 8)}` : '—'
}

export const DOC_TYPE_LABEL: Record<string, string> = { tos: 'Términos', privacy: 'Privacidad', other: 'Documento' }

export function Spinner() {
  return <span className="inline-block size-4 animate-spin rounded-full border-2 border-current border-r-transparent" />
}

export function ErrorBox({ error }: { error: string }) {
  return <div className="rounded-lg border border-stop/40 bg-stop/10 p-3 text-sm text-stop">{error}</div>
}
