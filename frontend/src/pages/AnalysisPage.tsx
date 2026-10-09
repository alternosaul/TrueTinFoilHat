import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type AnalysisFull, type Color, type Rubric } from '../api'
import {
  COLOR_LABEL, COLOR_SOFT, Card, Chip, CountsBar, DOC_TYPE_LABEL, Dot, ErrorBox, Score, Spinner, fmtDate, fmtSnapshot,
} from '../components/ui'

export default function AnalysisPage() {
  const { id } = useParams()
  const [a, setA] = useState<AnalysisFull | null>(null)
  const [rubric, setRubric] = useState<Rubric | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [colors, setColors] = useState<Set<Color>>(new Set(['red', 'yellow', 'green']))
  const [category, setCategory] = useState<string | null>(null)

  useEffect(() => {
    setA(null)
    api.analysis(id!).then(setA).catch((e) => setError(e.message))
    api.rubric().then(setRubric).catch(() => {})
  }, [id])

  const label = (cat: string) => rubric?.categories[cat]?.label ?? cat
  const categories = useMemo(() => {
    const m = new Map<string, number>()
    a?.clauses.forEach((c) => m.set(c.category, (m.get(c.category) ?? 0) + 1))
    return [...m.entries()].sort((x, y) => y[1] - x[1])
  }, [a])

  if (error) return <ErrorBox error={error} />
  if (!a) return <div className="flex justify-center py-20"><Spinner /></div>

  const reds = a.clauses.filter((c) => c.color === 'red')
  const visible = a.clauses.filter((c) => colors.has(c.color) && (!category || c.category === category))
  const toggle = (c: Color) => setColors((cur) => {
    const next = new Set(cur)
    if (next.has(c)) next.delete(c)
    else next.add(c)
    return next.size ? next : new Set([c])
  })

  return (
    <div className="grid gap-6">
      <Card className="grid gap-4">
        <div className="flex flex-wrap items-start gap-4">
          <Score score={a.score} />
          <div className="min-w-0 flex-1">
            <Link to={`/company/${a.company.id}`} className="text-sm font-medium text-stone-500 hover:underline">
              {a.company.name} · {DOC_TYPE_LABEL[a.doc_type] ?? a.doc_type}
            </Link>
            <h1 className="text-2xl font-bold">{a.title ?? a.url}</h1>
            <a href={a.url} target="_blank" rel="noreferrer" className="break-all text-sm text-stone-500 underline">{a.url}</a>
          </div>
          {a.comparison_id && (
            <Link to={`/comparison/${a.comparison_id}`} className="rounded-lg bg-stone-900 px-4 py-2 text-sm font-semibold text-white dark:bg-stone-100 dark:text-stone-900">
              ¿Qué cambió en el último año? →
            </Link>
          )}
        </div>
        <CountsBar counts={a.counts} />
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-stone-500">
          <span>{a.source === 'wayback' ? `Snapshot del ${fmtSnapshot(a.snapshot_ts)}` : 'Versión en vivo'}</span>
          <span>Analizado: {fmtDate(a.analyzed_at, true)}</span>
          {a.last_seen_at !== a.analyzed_at && <span>Última verificación: {fmtDate(a.last_seen_at, true)}</span>}
          <span>Modelo: {a.provider}/{a.model}</span>
          <span>Rúbrica {a.rubric_version}</span>
        </div>
      </Card>

      {reds.length > 0 && (
        <Card className="border-stop/40">
          <h2 className="mb-3 flex items-center gap-2 font-bold"><Dot color="red" /> Lo que más deberías saber</h2>
          <ul className="grid gap-2 text-sm">
            {reds.slice(0, 6).map((c) => (
              <li key={c.idx}>
                <a href={`#c${c.idx}`} className="hover:underline"><b>{label(c.category)}:</b> {c.explanation}</a>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {(['red', 'yellow', 'green'] as Color[]).map((c) => (
          <Chip key={c} active={colors.has(c)} onClick={() => toggle(c)}>
            <Dot color={c} /> {COLOR_LABEL[c]} ({a.counts[c]})
          </Chip>
        ))}
        <select
          value={category ?? ''}
          onChange={(e) => setCategory(e.target.value || null)}
          className="rounded-full border border-stone-300 bg-transparent px-3 py-1 text-sm dark:border-stone-700"
        >
          <option value="">Todas las categorías</option>
          {categories.map(([cat, n]) => <option key={cat} value={cat}>{label(cat)} ({n})</option>)}
        </select>
      </div>

      <div className="grid gap-3">
        {visible.map((c) => (
          <details key={c.idx} id={`c${c.idx}`} className={`group rounded-xl border p-4 ${COLOR_SOFT[c.color]}`}>
            <summary className="flex cursor-pointer list-none items-start gap-3">
              <Dot color={c.color} className="mt-1.5" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline gap-x-2 text-xs text-stone-500">
                  <span className="font-semibold uppercase tracking-wide">{label(c.category)}</span>
                  {c.heading && <span className="truncate">· {c.heading}</span>}
                </div>
                <p className="mt-1">{c.explanation}</p>
                <span className="mt-1 inline-block text-xs text-stone-500 group-open:hidden">Ver texto original ▾</span>
              </div>
            </summary>
            <blockquote className="mt-3 whitespace-pre-line border-l-2 border-stone-300 pl-4 text-sm text-stone-600 dark:border-stone-700 dark:text-stone-400">
              {c.text}
            </blockquote>
          </details>
        ))}
        {visible.length === 0 && <p className="text-sm text-stone-500">Ninguna cláusula coincide con el filtro.</p>}
      </div>
    </div>
  )
}
