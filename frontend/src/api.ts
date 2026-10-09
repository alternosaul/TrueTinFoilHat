export type Color = 'green' | 'yellow' | 'red'
export type Counts = Record<Color, number>

export interface AnalysisBrief {
  id: number
  document_id: number
  analyzed_at: string
  last_seen_at: string
  source: 'live' | 'wayback'
  snapshot_ts: string | null
  provider: string
  model: string
  rubric_version: string
  title: string | null
  score: number
  counts: Counts
}

export interface ClauseOut {
  idx: number
  heading: string | null
  text: string
  color: Color
  category: string
  explanation: string
}

export interface AnalysisFull extends AnalysisBrief {
  url: string
  doc_type: string
  company: { id: number; name: string; domain: string }
  comparison_id: number | null
  clauses: ClauseOut[]
}

export interface Change {
  id: number
  type: 'added' | 'removed' | 'modified'
  old_idx: number | null
  new_idx: number | null
  old_heading: string | null
  new_heading: string | null
  old_text: string | null
  new_text: string | null
  similarity: number | null
  impact?: 'better' | 'worse' | 'neutral'
  explanation?: string
}

export interface ComparisonOut {
  id: number
  created_at: string
  summary: string | null
  changes: Change[]
  old: AnalysisBrief
  new: AnalysisBrief
  url: string
}

export interface GalleryDoc {
  id: number
  url: string
  doc_type: string
  latest: AnalysisBrief | null
  n_analyses: number
}

export interface GalleryCompany {
  id: number
  name: string
  domain: string
  last_analyzed_at: string | null
  documents: GalleryDoc[]
}

export interface CompanyDetail {
  id: number
  name: string
  domain: string
  documents: { id: number; url: string; doc_type: string; analyses: AnalysisBrief[] }[]
}

export interface ProviderInfo {
  id: 'anthropic' | 'ollama'
  label: string
  requires_key: boolean
  available?: boolean
  models: string[]
  default_model: string
}

export interface ProgressEvent {
  stage: string
  message: string
  done?: number
  total?: number
  analysis_id?: number
  comparison_id?: number | null
  snapshot?: string
}

export interface Rubric {
  version: string
  colors: Record<Color, string>
  categories: Record<string, { label: string; red: string; yellow: string; green: string }>
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path)
  if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail ?? `HTTP ${r.status}`)
  return r.json()
}

export const api = {
  providers: () => get<{ mode: 'local' | 'hosted'; providers: ProviderInfo[] }>('/api/providers'),
  rubric: () => get<Rubric>('/api/rubric'),
  companies: () => get<GalleryCompany[]>('/api/companies'),
  company: (id: number | string) => get<CompanyDetail>(`/api/companies/${id}`),
  analysis: (id: number | string) => get<AnalysisFull>(`/api/analyses/${id}`),
  comparison: (id: number | string) => get<ComparisonOut>(`/api/comparisons/${id}`),

  async analyze(body: { url: string; provider: string; model?: string; lang: string; compare: boolean }, key?: string) {
    const r = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(key ? { 'X-LLM-Key': key } : {}) },
      body: JSON.stringify(body),
    })
    const data = await r.json()
    if (!r.ok) throw new Error(data?.detail ?? `HTTP ${r.status}`)
    return data as { job_id: string }
  },

  async importDb(file: File) {
    const r = await fetch('/api/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: await file.text(),
    })
    const data = await r.json()
    if (!r.ok) throw new Error(data?.detail ?? `HTTP ${r.status}`)
    return data as { analyses_added: number; analyses_skipped: number; comparisons_added: number }
  },
}

export function streamJob(jobId: string, onEvent: (e: ProgressEvent) => void): () => void {
  const es = new EventSource(`/api/jobs/${jobId}/events`)
  es.addEventListener('progress', (msg) => {
    const ev = JSON.parse((msg as MessageEvent).data) as ProgressEvent
    onEvent(ev)
    if (ev.stage === 'done' || ev.stage === 'error') es.close()
  })
  es.onerror = () => es.close()
  return () => es.close()
}
