import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type Change, type ComparisonOut } from '../api'
import { Card, Chip, ErrorBox, Score, Spinner, fmtDate, fmtSnapshot } from '../components/ui'
import { wordDiff, type Part } from '../wordDiff'

const IMPACT = {
  worse: { label: 'Peor para ti', cls: 'border-stop/50 bg-stop/5', badge: 'bg-stop text-white' },
  better: { label: 'Mejor para ti', cls: 'border-go/50 bg-go/5', badge: 'bg-go text-white' },
  neutral: { label: 'Neutral', cls: 'border-stone-300 dark:border-stone-700', badge: 'bg-stone-300 text-stone-800 dark:bg-stone-700 dark:text-stone-100' },
} as const

const TYPE_LABEL = { added: 'Añadida', removed: 'Eliminada', modified: 'Modificada' } as const

function Parts({ parts }: { parts: Part[] }) {
  return (
    <>
      {parts.map((p, i) =>
        p.kind === 'same' ? <span key={i}>{p.text}</span>
          : p.kind === 'del' ? <del key={i} className="bg-stop/20 decoration-stop/60">{p.text}</del>
            : <ins key={i} className="bg-go/20 no-underline">{p.text}</ins>,
      )}
    </>
  )
}

function ChangeRow({ c }: { c: Change }) {
  const impact = IMPACT[c.impact ?? 'neutral']
  const diff = useMemo(() => (c.type === 'modified' && c.old_text && c.new_text ? wordDiff(c.old_text, c.new_text) : null), [c])
  const col = 'whitespace-pre-line rounded-lg bg-white/60 p-3 text-sm dark:bg-stone-900/60'

  return (
    <div className={`grid gap-3 rounded-xl border p-4 ${impact.cls}`}>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className={`rounded-full px-2 py-0.5 font-semibold ${impact.badge}`}>{impact.label}</span>
        <span className="rounded-full border border-stone-300 px-2 py-0.5 dark:border-stone-700">{TYPE_LABEL[c.type]}</span>
        {(c.new_heading || c.old_heading) && <span className="text-stone-500">{c.new_heading ?? c.old_heading}</span>}
      </div>
      {c.explanation && <p className="font-medium">{c.explanation}</p>}
      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <div className="mb-1 text-xs font-semibold uppercase text-stone-500">Antes</div>
          <div className={col}>
            {c.old_text == null ? <span className="italic text-stone-400">(no existía)</span>
              : diff ? <Parts parts={diff.old} /> : c.type === 'removed' ? <del className="bg-stop/20">{c.old_text}</del> : c.old_text}
          </div>
        </div>
        <div>
          <div className="mb-1 text-xs font-semibold uppercase text-stone-500">Ahora</div>
          <div className={col}>
            {c.new_text == null ? <span className="italic text-stone-400">(eliminada)</span>
              : diff ? <Parts parts={diff.new} /> : c.type === 'added' ? <ins className="bg-go/20 no-underline">{c.new_text}</ins> : c.new_text}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function DiffPage() {
  const { id } = useParams()
  const [cmp, setCmp] = useState<ComparisonOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'worse' | 'better' | 'neutral'>('all')

  useEffect(() => {
    api.comparison(id!).then(setCmp).catch((e) => setError(e.message))
  }, [id])

  if (error) return <ErrorBox error={error} />
  if (!cmp) return <div className="flex justify-center py-20"><Spinner /></div>

  const count = (k: string) => cmp.changes.filter((c) => (c.impact ?? 'neutral') === k).length
  const visible = cmp.changes.filter((c) => filter === 'all' || (c.impact ?? 'neutral') === filter)

  return (
    <div className="grid gap-6">
      <Card className="grid gap-4">
        <div className="text-sm text-stone-500">
          <Link to={`/analysis/${cmp.new.id}`} className="hover:underline">← Volver al análisis</Link>
        </div>
        <h1 className="text-2xl font-bold">¿Qué cambió?</h1>
        <a href={cmp.url} target="_blank" rel="noreferrer" className="break-all text-sm text-stone-500 underline">{cmp.url}</a>
        <div className="grid gap-4 sm:grid-cols-2">
          {([['Antes', cmp.old, `Wayback Machine · ${fmtSnapshot(cmp.old.snapshot_ts)}`], ['Ahora', cmp.new, `En vivo · ${fmtDate(cmp.new.analyzed_at)}`]] as const).map(([lbl, a, sub]) => (
            <Link key={lbl} to={`/analysis/${a.id}`} className="flex items-center gap-3 rounded-lg border border-stone-200 p-3 hover:border-stone-400 dark:border-stone-800">
              <Score score={a.score} size="sm" />
              <div>
                <div className="font-semibold">{lbl}</div>
                <div className="text-xs text-stone-500">{sub}</div>
                <div className="text-xs text-stone-500">🔴 {a.counts.red} · 🟡 {a.counts.yellow} · 🟢 {a.counts.green}</div>
              </div>
            </Link>
          ))}
        </div>
        {cmp.summary && <p className="rounded-lg bg-stone-100 p-3 dark:bg-stone-800">{cmp.summary}</p>}
      </Card>

      <div className="flex flex-wrap gap-2">
        <Chip active={filter === 'all'} onClick={() => setFilter('all')}>Todos ({cmp.changes.length})</Chip>
        <Chip active={filter === 'worse'} onClick={() => setFilter('worse')}>Peor ({count('worse')})</Chip>
        <Chip active={filter === 'better'} onClick={() => setFilter('better')}>Mejor ({count('better')})</Chip>
        <Chip active={filter === 'neutral'} onClick={() => setFilter('neutral')}>Neutral ({count('neutral')})</Chip>
      </div>

      <div className="grid gap-4">
        {visible.map((c) => <ChangeRow key={c.id} c={c} />)}
        {cmp.changes.length === 0 && <p className="text-stone-500">El texto no cambió entre ambas versiones.</p>}
      </div>
    </div>
  )
}
