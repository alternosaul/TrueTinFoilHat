import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type GalleryCompany } from '../api'
import { Card, CountsBar, DOC_TYPE_LABEL, ErrorBox, Score, Spinner, fmtDate } from '../components/ui'

export default function GalleryPage() {
  const [companies, setCompanies] = useState<GalleryCompany[] | null>(null)
  const [q, setQ] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = () => api.companies().then(setCompanies).catch((e) => setError(e.message))
  useEffect(() => { load() }, [])

  async function onImport(file: File) {
    try {
      const r = await api.importDb(file)
      setMsg(`Importados ${r.analyses_added} análisis (${r.analyses_skipped} ya existían), ${r.comparisons_added} comparaciones.`)
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  if (error) return <ErrorBox error={error} />
  if (!companies) return <div className="flex justify-center py-20"><Spinner /></div>

  const needle = q.toLowerCase()
  const shown = companies.filter((c) => !needle || c.name.toLowerCase().includes(needle) || c.domain.includes(needle))
  const btn = 'rounded-lg border border-stone-300 px-3 py-1.5 text-sm hover:border-stone-500 dark:border-stone-700'

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Galería</h1>
          <p className="text-stone-500">{companies.length} empresas analizadas. Cada análisis guarda cuándo se hizo y con qué modelo.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar empresa…" className="rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-sm dark:border-stone-700 dark:bg-stone-900" />
          <a href="/api/export" className={btn}>Exportar JSON</a>
          <a href="/api/export?format=csv" className={btn}>CSV</a>
          <button className={btn} onClick={() => fileRef.current?.click()}>Importar</button>
          <input ref={fileRef} type="file" accept="application/json" hidden onChange={(e) => e.target.files?.[0] && onImport(e.target.files[0])} />
        </div>
      </div>
      {msg && <p className="rounded-lg bg-go/10 p-3 text-sm">{msg}</p>}

      {shown.length === 0 ? (
        <Card className="py-10 text-center text-stone-500">
          Aún no hay nada aquí. <Link to="/" className="underline">Analiza tu primer documento</Link>.
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {shown.map((c) => (
            <Card key={c.id} className="grid content-start gap-3">
              <div className="flex items-baseline justify-between gap-2">
                <Link to={`/company/${c.id}`} className="text-lg font-bold hover:underline">{c.name}</Link>
                <span className="text-xs text-stone-500">{c.domain}</span>
              </div>
              {c.documents.map((d) => d.latest && (
                <Link key={d.id} to={`/analysis/${d.latest.id}`} className="flex items-center gap-3 rounded-lg p-2 hover:bg-stone-100 dark:hover:bg-stone-800">
                  <Score score={d.latest.score} size="sm" />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium">{DOC_TYPE_LABEL[d.doc_type] ?? d.doc_type}</div>
                    <CountsBar counts={d.latest.counts} className="my-1" />
                    <div className="text-xs text-stone-500">
                      {fmtDate(d.latest.analyzed_at, true)} · {d.n_analyses} análisis
                    </div>
                  </div>
                </Link>
              ))}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
