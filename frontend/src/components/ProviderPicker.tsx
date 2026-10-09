import { useEffect, useState } from 'react'
import { api, type ProviderInfo } from '../api'
import { loadApiKey, saveApiKey, type Prefs } from '../settings'

interface Props {
  prefs: Prefs
  setPrefs: (p: Partial<Prefs>) => void
  compact?: boolean
}

export function useProviders() {
  const [data, setData] = useState<{ mode: string; providers: ProviderInfo[] } | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    api.providers().then(setData).catch((e) => setError(String(e.message ?? e)))
  }, [])
  return { data, error }
}

export default function ProviderPicker({ prefs, setPrefs, compact = false }: Props) {
  const { data, error } = useProviders()
  const [key, setKey] = useState(loadApiKey)

  const providers = data?.providers ?? []
  const current = providers.find((p) => p.id === prefs.provider) ?? providers[0]

  // si el proveedor guardado no existe (p. ej. modo hosted), usa el primero disponible
  useEffect(() => {
    if (current && current.id !== prefs.provider) setPrefs({ provider: current.id, model: current.default_model })
    else if (current && !current.models.includes(prefs.model) && current.models.length) setPrefs({ model: current.default_model })
  }, [current, prefs.provider, prefs.model, setPrefs])

  if (error) return <p className="text-sm text-stop">No se pudo contactar el backend: {error}</p>
  if (!current) return <p className="text-sm text-stone-500">Cargando proveedores…</p>

  const input = 'w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm dark:border-stone-700 dark:bg-stone-900'

  return (
    <div className={`grid gap-3 ${compact ? 'sm:grid-cols-3' : ''}`}>
      <label className="grid gap-1 text-sm">
        <span className="font-medium">Proveedor</span>
        <select className={input} value={current.id} onChange={(e) => {
          const p = providers.find((x) => x.id === e.target.value)!
          setPrefs({ provider: p.id, model: p.default_model })
        }}>
          {providers.map((p) => (
            <option key={p.id} value={p.id}>{p.label}{p.available === false ? ' — no disponible' : ''}</option>
          ))}
        </select>
      </label>
      <label className="grid gap-1 text-sm">
        <span className="font-medium">Modelo</span>
        {current.models.length ? (
          <select className={input} value={prefs.model} onChange={(e) => setPrefs({ model: e.target.value })}>
            {current.models.map((m) => <option key={m}>{m}</option>)}
          </select>
        ) : (
          <input className={input} value={prefs.model} placeholder={current.default_model} onChange={(e) => setPrefs({ model: e.target.value })} />
        )}
      </label>
      {current.requires_key && (
        <label className="grid gap-1 text-sm">
          <span className="font-medium">API key de Anthropic</span>
          <input
            className={input}
            type="password"
            autoComplete="off"
            placeholder="sk-ant-…"
            value={key}
            onChange={(e) => { setKey(e.target.value); saveApiKey(e.target.value.trim()) }}
          />
          {!compact && (
            <span className="text-xs text-stone-500">
              Se guarda solo en esta pestaña (sessionStorage) y se envía únicamente en cada análisis. El servidor no la almacena.
            </span>
          )}
        </label>
      )}
      {current.id === 'ollama' && current.available === false && (
        <p className="text-sm text-warn sm:col-span-3">
          Ollama no responde o no tiene modelos. Ejecuta <code>ollama serve</code> y <code>ollama pull qwen2.5:7b</code>.
        </p>
      )}
    </div>
  )
}
