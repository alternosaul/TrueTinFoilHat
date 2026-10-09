# TrueTinFoilHat 🚦

**Un semáforo para la letra pequeña.** Pega la URL de unos términos de servicio o una política de privacidad:
cada cláusula se clasifica en 🟢 verde, 🟡 amarillo o 🔴 rojo según su impacto en ti, con una explicación en
lenguaje simple. Además se busca la versión de hace ~1 año en la **Wayback Machine** y se muestra qué cambió,
lado a lado, indicando si cada cambio es mejor o peor para el usuario.

Todo lo que se analiza se guarda en una **base de datos por empresa, con fecha de análisis**, que alimenta una
galería y se puede exportar/importar para combinar análisis de varias instalaciones.

- **BYOK**: usa tu propia API key de Claude. Se queda en el navegador (`sessionStorage`), viaja solo en el header
  de cada análisis y el servidor nunca la guarda ni la registra.
- **100 % local**: o usa un modelo en tu máquina con [Ollama](https://ollama.com), sin enviar nada fuera.

> ⚠️ Análisis automático y orientativo. No es asesoría legal.

## Cómo funciona

```
URL ─► fetch (httpx + trafilatura, fallback Playwright) ─► segmentación en cláusulas
    ─► clasificación por lotes con rúbrica fija (Claude o Ollama, salida JSON validada)
    ─► Wayback Machine: snapshot más cercano a hoy − 1 año ─► mismo pipeline
    ─► alineación de cláusulas (difflib + rapidfuzz) ─► el LLM resume cada cambio (mejor/peor/neutral)
    ─► SQLite: empresas → documentos → análisis (timestamp, modelo, rúbrica) → cláusulas / comparaciones
```

- **Rúbrica fija y versionada** en [`backend/app/llm/rubric.yaml`](backend/app/llm/rubric.yaml): 14 categorías
  (venta de datos, rastreo, arbitraje, cambios unilaterales, licencia sobre tu contenido, etc.) con criterios
  explícitos para cada color. Cada análisis guarda la versión de rúbrica usada.
- **Cache**: si el texto no cambió (mismo hash, mismo modelo y rúbrica), se reutiliza el análisis y solo se
  actualiza `last_seen_at`.
- **Puntuación** 0–100: `(verdes + 0.5·amarillas) / total`.

## Estructura

```
backend/            FastAPI + SQLAlchemy + Alembic (Python ≥ 3.12, gestionado con uv)
  app/extract/      fetch.py (descarga/extracción), segment.py (cláusulas)
  app/llm/          base.py (prompts/esquemas), anthropic_provider.py, ollama_provider.py, rubric.yaml
  app/wayback.py    availability API + CDX, descarga del HTML original (id_)
  app/diff.py       alineación de cláusulas entre versiones
  app/pipeline.py   orquestación + persistencia
  app/api/          analyze (jobs + SSE), data (galería), export/import, meta
frontend/           React + Vite + TypeScript + Tailwind
scripts/            seed_gallery.py: analiza una lista de apps populares
```

## Puesta en marcha

Requisitos: [uv](https://docs.astral.sh/uv/), Node ≥ 20 y (para modo local) Ollama.

```bash
cp .env.example .env

# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload        # http://localhost:8000 (migra la DB al arrancar)

# Frontend (otra terminal)
cd frontend
npm install
npm run dev                                  # http://localhost:5173 (proxy /api → :8000)
```

Si el puerto 8000 está ocupado: `uvicorn ... --port 8765` y `API_TARGET=http://localhost:8765 npm run dev`.

O todo en un solo proceso: `cd frontend && npm run build`, y el backend sirve la app compilada en `:8000`.

### Modo local con Ollama

```bash
ollama serve
ollama pull qwen2.5:14b        # o qwen2.5:7b / llama3.1:8b si tienes poca memoria
```

Elige “Ollama (local)” en la app. Recomendaciones:

- Usa un modelo **generalista con buen seguimiento de instrucciones** (Qwen 2.5/3, Llama 3.1, Mistral). Los
  modelos especializados (p. ej. de seguridad o código) clasifican peor y a veces omiten cláusulas.
- Los modelos “de razonamiento” gastan tokens pensando antes del JSON: por eso se envía `think: false`
  (`OLLAMA_THINK` en `.env`).
- Un documento típico tiene 30–80 cláusulas; con modelos de ~30B en un portátil puede tardar bastante.
  `OLLAMA_TIMEOUT` controla el tiempo máximo por lote.

### BYOK con Claude

Elige “Claude (tu API key)” y pega tu key en Ajustes. Por defecto se usa `claude-haiku-5-5` (rápido y barato
para clasificar); se puede cambiar a `claude-sonnet-5-5` o `claude-opus-5-5` desde la interfaz o con
`ANTHROPIC_DEFAULT_MODEL`. La salida se valida con esquemas Pydantic (`messages.parse`).

### Instancia pública (`MODE=hosted`)

Con `MODE=hosted` Ollama se desactiva y cada análisis requiere la key del usuario.

```bash
docker compose --profile local up --build      # app + Ollama
MODE=hosted docker compose up --build          # solo app (BYOK)
```

## Base de datos de servicios

SQLite en `backend/data/truetinfoilhat.db` (configurable con `DB_URL`).

| Tabla | Contenido |
|---|---|
| `companies` | nombre, dominio (único) |
| `documents` | URL, tipo (`tos` / `privacy` / `other`) |
| `analyses` | `analyzed_at`, `last_seen_at`, fuente (`live` / `wayback` + fecha del snapshot), hash del texto, proveedor, modelo, versión de rúbrica, conteos y puntuación |
| `clauses` | texto, color, categoría, explicación |
| `comparisons` | análisis viejo ↔ nuevo, resumen y lista de cambios con su impacto |

- `GET /api/export` (JSON completo) y `GET /api/export?format=csv` (resumen por análisis).
- `POST /api/import` fusiona un export y omite análisis duplicados. También desde la galería (botón *Importar*).
- Poblar la galería: `uv run python ../scripts/seed_gallery.py --provider ollama --model qwen2.5:14b`.
- Cambios de esquema: `cd backend && uv run alembic revision --autogenerate -m "..."`.

## API

| Método | Ruta | |
|---|---|---|
| POST | `/api/analyze` | `{url, provider, model?, lang, compare}` + header `X-LLM-Key` (BYOK) → `{job_id}` |
| GET | `/api/jobs/{id}/events` | progreso por SSE |
| GET | `/api/companies`, `/api/companies/{id}` | galería e historial por empresa |
| GET | `/api/analyses/{id}`, `/api/comparisons/{id}` | detalle de un análisis / diff |
| GET | `/api/providers`, `/api/rubric` | proveedores y modelos disponibles, rúbrica |

Documentación interactiva en `/docs`.

## Tests

```bash
cd backend && uv run pytest
```

Cubren segmentación (con los ToS de GitHub, licencia CC0), alineación de versiones, el cliente de Wayback
(respuestas simuladas) y el pipeline completo con un proveedor falso, incluido export → import.

## Roadmap

- Elegir cualquier snapshot del historial (`wayback.list_snapshots` ya existe) y una línea de tiempo por documento.
- Re-análisis periódico de la galería y alertas cuando cambian los términos.
- Más proveedores BYOK.
