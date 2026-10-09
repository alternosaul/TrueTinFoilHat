import { useEffect, useState } from 'react'
import { api, type Color, type Rubric } from '../api'
import ProviderPicker, { useProviders } from '../components/ProviderPicker'
import { COLOR_LABEL, Card, Dot } from '../components/ui'
import { usePrefs } from '../settings'

export default function SettingsPage() {
  const [prefs, setPrefs] = usePrefs()
  const [rubric, setRubric] = useState<Rubric | null>(null)
  const { data } = useProviders()

  useEffect(() => { api.rubric().then(setRubric).catch(() => {}) }, [])

  return (
    <div className="grid gap-6">
      <h1 className="text-3xl font-bold">Ajustes</h1>
      <Card className="grid gap-4">
        <div>
          <h2 className="text-lg font-bold">Modelo</h2>
          <p className="text-sm text-stone-500">
            {data?.mode === 'hosted'
              ? 'Instancia pública: trae tu propia API key (BYOK).'
              : 'Modo local: usa Ollama en tu máquina o tu propia API key de Claude.'}
          </p>
        </div>
        <ProviderPicker prefs={prefs} setPrefs={setPrefs} />
      </Card>

      {rubric && (
        <Card className="grid gap-4">
          <div>
            <h2 className="text-lg font-bold">Rúbrica <span className="text-sm font-normal text-stone-500">v{rubric.version}</span></h2>
            <p className="text-sm text-stone-500">Criterios fijos que usa el modelo para clasificar cada cláusula.</p>
          </div>
          <div className="grid gap-1 text-sm">
            {(['green', 'yellow', 'red'] as Color[]).map((c) => (
              <div key={c} className="flex gap-2"><Dot color={c} className="mt-1" /><b>{COLOR_LABEL[c]}:</b> {rubric.colors[c]}</div>
            ))}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-stone-500">
                <tr><th className="p-2">Categoría</th><th className="p-2">Rojo</th><th className="p-2">Amarillo</th><th className="p-2">Verde</th></tr>
              </thead>
              <tbody>
                {Object.entries(rubric.categories).map(([k, v]) => (
                  <tr key={k} className="border-t border-stone-200 align-top dark:border-stone-800">
                    <td className="p-2 font-medium">{v.label}</td>
                    <td className="p-2">{v.red}</td>
                    <td className="p-2">{v.yellow}</td>
                    <td className="p-2">{v.green}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
