import { useCallback, useEffect, useState } from 'react'

// Preferencias no sensibles: localStorage. La API key: solo sessionStorage (se borra al cerrar la pestaña)
// y nunca se envía al backend salvo en el header de cada análisis.
export interface Prefs {
  provider: 'anthropic' | 'ollama'
  model: string
  lang: 'es' | 'en'
  compare: boolean
}

const PREFS_KEY = 'ttfh.prefs'
const API_KEY = 'ttfh.apiKey'
const DEFAULT_PREFS: Prefs = { provider: 'ollama', model: '', lang: 'es', compare: true }

function safe<T>(fn: () => T, fallback: T): T {
  try {
    return fn()
  } catch {
    return fallback
  }
}

export function loadPrefs(): Prefs {
  return safe(() => ({ ...DEFAULT_PREFS, ...JSON.parse(localStorage.getItem(PREFS_KEY) ?? '{}') }), DEFAULT_PREFS)
}

export function savePrefs(p: Prefs) {
  safe(() => localStorage.setItem(PREFS_KEY, JSON.stringify(p)), undefined)
}

export function loadApiKey(): string {
  return safe(() => sessionStorage.getItem(API_KEY) ?? '', '')
}

export function saveApiKey(k: string) {
  safe(() => (k ? sessionStorage.setItem(API_KEY, k) : sessionStorage.removeItem(API_KEY)), undefined)
}

export function usePrefs(): [Prefs, (p: Partial<Prefs>) => void] {
  const [prefs, setPrefs] = useState<Prefs>(loadPrefs)
  useEffect(() => savePrefs(prefs), [prefs])
  const update = useCallback((p: Partial<Prefs>) => setPrefs((cur) => ({ ...cur, ...p })), [])
  return [prefs, update]
}
