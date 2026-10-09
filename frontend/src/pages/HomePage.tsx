import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, streamJob, type GalleryCompany, type ProgressEvent } from '../api'
import ProviderPicker from '../components/ProviderPicker'
import { Card, CountsBar, ErrorBox, Score, Spinner, fmtDate } from '../components/ui'
import { loadApiKey, usePrefs } from '../settings'

const EXAMPLES = [
  'https://docs.github.com/en/site-policy/github-terms/github-terms-of-service',
  'https://www.spotify.com/us/legal/privacy-policy/',
  'https://discord.com/terms',
  'https://www.reddit.com/policies/user-agreement',
]

export default function HomePage() {
  const [prefs, setPrefs] = usePrefs()
  const [url, setUrl] = useState('')
  const [events, setEvents] = useState<ProgressEvent[]>([])
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [recent, setRecent] = useState<GalleryCompany[]>([])
  const stopRef = useRef<() => void>(undefined)
  const navigate = useNavigate()

  useEffect(() => {
    api.companies().then((c) => setRecent(c.slice(0, 6))).catch(() => {})
    return () => stopRef.current?.()
  }, [])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setEvents([])
    setRunning(true)
    try {
      const { job_id } = await api.analyze(
        { url: url.trim(), provider: prefs.provider, model: prefs.model || undefined, lang: prefs.lang, compare: prefs.compare },
        prefs.provider === 'anthropic' ? loadApiKey() : undefined,
      )
      stopRef.current = streamJob(job_id, (ev) => {
        setEvents((cur) => [...cur, ev])
        if (ev.stage === 'done' && ev.analysis_id) navigate(`/analysis/${ev.analysis_id}`)
        if (ev.stage === 'error') { setError(ev.message); setRunning(false) }
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setRunning(false)
    }
  }

  const last = events.at(-1)
  const progress = [...events].reverse().find((e) => e.total && e.done !== undefined)

  return (
    <div className="grid gap-10">
      <section className="mx-auto grid max-w-3xl gap-4 text-center">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">Un semáforo para la letra pequeña</h1>
        <p className="text-lg text-stone-600 dark:text-stone-400">
          Pega la URL de unos términos de servicio o una política de privacidad. Clasificamos cada cláusula en
          <span className="mx-1 font-semibold text-go">verde</span>,
          <span className="mx-1 font-semibold text-warn">amarillo</span> o
          <span className="mx-1 font-semibold text-stop">rojo</span>
          y te contamos qué cambió desde hace un año.
        </p>
      </section>

      <Card className="mx-auto w-full max-w-3xl">
        <form onSubmit={submit} className="grid gap-4">
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              type="url"
              required
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://ejemplo.com/terms"
              className="flex-1 rounded-lg border border-stone-300 bg-white px-4 py-3 dark:border-stone-700 dark:bg-stone-950"
            />
            <button
              disabled={running}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-stone-900 px-6 py-3 font-semibold text-white disabled:opacity-60 dark:bg-stone-100 dark:text-stone-900"
            >
              {running && <Spinner />} Analizar
            </button>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="text-stone-500">Ejemplos:</span>
            {EXAMPLES.map((u) => (
              <button type="button" key={u} onClick={() => setUrl(u)} className="text-stone-600 underline decoration-dotted hover:text-stone-900 dark:text-stone-400">
                {new URL(u).hostname.replace('www.', '')}
              </button>
            ))}
          </div>
          <ProviderPicker prefs={prefs} setPrefs={setPrefs} compact />
          <div className="flex flex-wrap gap-4 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={prefs.compare} onChange={(e) => setPrefs({ compare: e.target.checked })} />
              Comparar con la versión de hace 1 año (Wayback Machine)
            </label>
            <label className="flex items-center gap-2">
              Idioma de las explicaciones
              <select value={prefs.lang} onChange={(e) => setPrefs({ lang: e.target.value as 'es' | 'en' })} className="rounded border border-stone-300 bg-transparent px-1 dark:border-stone-700">
                <option value="es">Español</option>
                <option value="en">English</option>
              </select>
            </label>
          </div>
        </form>

        {(running || events.length > 0) && (
          <div className="mt-4 grid gap-2 border-t border-stone-200 pt-4 dark:border-stone-800">
            {progress?.total ? (
              <div className="h-1.5 overflow-hidden rounded-full bg-stone-200 dark:bg-stone-800">
                <div className="h-full bg-stone-900 transition-all dark:bg-stone-100" style={{ width: `${(100 * (progress.done ?? 0)) / progress.total}%` }} />
              </div>
            ) : null}
            <ol className="grid gap-1 text-sm text-stone-600 dark:text-stone-400">
              {events.map((ev, i) => (
                ev.stage === 'classifying' && ev !== last ? null : (
                  <li key={i} className="flex items-center gap-2">
                    {ev === last && running && ev.stage !== 'done' && ev.stage !== 'error' ? <Spinner /> : <span>•</span>}
                    {ev.message}
                    {ev.snapshot && <a href={ev.snapshot} target="_blank" rel="noreferrer" className="underline">ver snapshot</a>}
                  </li>
                )
              ))}
            </ol>
          </div>
        )}
        {error && <div className="mt-4"><ErrorBox error={error} /></div>}
      </Card>

      {recent.length > 0 && (
        <section className="grid gap-4">
          <div className="flex items-baseline justify-between">
            <h2 className="text-xl font-bold">Analizados recientemente</h2>
            <Link to="/gallery" className="text-sm underline">Ver galería</Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {recent.flatMap((c) => c.documents.filter((d) => d.latest).map((d) => (
              <Link key={d.id} to={`/analysis/${d.latest!.id}`}>
                <Card className="flex items-center gap-3 transition hover:border-stone-400">
                  <Score score={d.latest!.score} size="sm" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-semibold">{c.name}</div>
                    <div className="truncate text-xs text-stone-500">{d.latest!.title ?? d.url}</div>
                    <CountsBar counts={d.latest!.counts} className="mt-2" />
                    <div className="mt-1 text-xs text-stone-500">{fmtDate(d.latest!.analyzed_at)}</div>
                  </div>
                </Card>
              </Link>
            )))}
          </div>
        </section>
      )}
    </div>
  )
}
