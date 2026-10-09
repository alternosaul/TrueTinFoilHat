"""Proveedor local vía Ollama (/api/chat con `format` = JSON schema)."""

import httpx
from pydantic import BaseModel, ValidationError

from app.config import get_settings
from app.extract.segment import Segment
from app.llm.base import (
    BatchVerdict,
    ClauseVerdict,
    DiffVerdict,
    LLMError,
    classify_system_prompt,
    classify_user_prompt,
    diff_system_prompt,
    diff_user_prompt,
)


async def list_ollama_models() -> list[str]:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{settings.ollama_url}/api/tags")
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]
    except httpx.HTTPError:
        return []


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str | None = None):
        settings = get_settings()
        self.model = model or settings.ollama_model
        self._url = f"{settings.ollama_url}/api/chat"
        self._think = settings.ollama_think
        self._timeout = settings.ollama_timeout

    async def _chat[T: BaseModel](self, system: str, user: str, schema: type[T], retries: int = 2) -> T:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        last_err: Exception | None = None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for _ in range(retries + 1):
                try:
                    r = await client.post(self._url, json={
                        "model": self.model,
                        "messages": messages,
                        "format": schema.model_json_schema(),
                        "stream": False,
                        # modelos con razonamiento (qwen3, gpt-oss…) gastan el presupuesto pensando antes del JSON
                        "think": self._think,
                        "options": {"temperature": 0, "num_ctx": 16384},
                    })
                    r.raise_for_status()
                except httpx.ConnectError as e:
                    raise LLMError("Ollama no está corriendo (ollama serve)") from e
                except httpx.TimeoutException as e:
                    raise LLMError(f"Ollama tardó más de {self._timeout:.0f}s; prueba un modelo más pequeño") from e
                except httpx.HTTPStatusError as e:
                    raise LLMError(f"Ollama respondió {e.response.status_code}: {e.response.text[:200]}") from e
                try:
                    return schema.model_validate_json(r.json()["message"]["content"])
                except (ValidationError, KeyError) as e:
                    last_err = e
        raise LLMError(f"El modelo local devolvió JSON inválido: {last_err}")

    async def classify(self, segments: list[Segment], lang: str) -> list[ClauseVerdict]:
        out = await self._chat(classify_system_prompt(lang), classify_user_prompt(segments), BatchVerdict)
        return out.verdicts

    async def summarize_diff(self, changes: list[dict], lang: str) -> DiffVerdict:
        return await self._chat(diff_system_prompt(lang), diff_user_prompt(changes), DiffVerdict)
