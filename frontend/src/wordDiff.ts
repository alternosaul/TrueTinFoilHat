export type Part = { text: string; kind: 'same' | 'del' | 'add' }

const MAX_CELLS = 400_000

/** Diff por palabras (LCS). Devuelve partes para el texto viejo y el nuevo. */
export function wordDiff(a: string, b: string): { old: Part[]; new: Part[] } | null {
  const x = a.split(/(\s+)/)
  const y = b.split(/(\s+)/)
  if (x.length * y.length > MAX_CELLS) return null
  const n = x.length
  const m = y.length
  const dp = Array.from({ length: n + 1 }, () => new Uint32Array(m + 1))
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      dp[i][j] = x[i] === y[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])

  const oldParts: Part[] = []
  const newParts: Part[] = []
  const push = (arr: Part[], text: string, kind: Part['kind']) => {
    const last = arr.at(-1)
    if (last && last.kind === kind) last.text += text
    else arr.push({ text, kind })
  }
  let i = 0
  let j = 0
  while (i < n && j < m) {
    if (x[i] === y[j]) { push(oldParts, x[i], 'same'); push(newParts, y[j], 'same'); i++; j++ }
    else if (dp[i + 1][j] >= dp[i][j + 1]) push(oldParts, x[i++], 'del')
    else push(newParts, y[j++], 'add')
  }
  while (i < n) push(oldParts, x[i++], 'del')
  while (j < m) push(newParts, y[j++], 'add')
  return { old: oldParts, new: newParts }
}
