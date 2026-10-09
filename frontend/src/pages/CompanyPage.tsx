import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type CompanyDetail } from '../api'
import { Card, CountsBar, DOC_TYPE_LABEL, ErrorBox, Score, Spinner, fmtDate, fmtSnapshot } from '../components/ui'

export default function CompanyPage() {
  const { id } = useParams()
  const [c, setC] = useState<CompanyDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.company(id!).then(setC).catch((e) => setError(e.message))
  }, [id])

  if (error) return <ErrorBox error={error} />
  if (!c) return <div className="flex justify-center py-20"><Spinner /></div>

  return (
    <div className="grid gap-6">
      <div>
        <Link to="/gallery" className="text-sm text-stone-500 hover:underline">← Galería</Link>
        <h1 className="text-3xl font-bold">{c.name}</h1>
        <p className="text-stone-500">{c.domain}</p>
      </div>
      {c.documents.map((d) => (
        <Card key={d.id} className="grid gap-3">
          <div>
            <h2 className="text-lg font-bold">{DOC_TYPE_LABEL[d.doc_type] ?? d.doc_type}</h2>
            <a href={d.url} target="_blank" rel="noreferrer" className="break-all text-sm text-stone-500 underline">{d.url}</a>
          </div>
          <ol className="grid gap-2">
            {d.analyses.map((a) => (
              <li key={a.id}>
                <Link to={`/analysis/${a.id}`} className="flex items-center gap-3 rounded-lg p-2 hover:bg-stone-100 dark:hover:bg-stone-800">
                  <Score score={a.score} size="sm" />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium">
                      {a.source === 'wayback' ? `Versión archivada del ${fmtSnapshot(a.snapshot_ts)}` : 'Versión en vivo'}
                    </div>
                    <CountsBar counts={a.counts} className="my-1" />
                    <div className="text-xs text-stone-500">
                      Analizado {fmtDate(a.analyzed_at, true)} · {a.provider}/{a.model} · rúbrica {a.rubric_version}
                    </div>
                  </div>
                </Link>
              </li>
            ))}
          </ol>
        </Card>
      ))}
    </div>
  )
}
