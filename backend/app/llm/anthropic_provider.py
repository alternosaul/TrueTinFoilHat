"""Proveedor Claude (BYOK): la API key llega por request y nunca se persiste."""

import anthropic

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

CLAUDE_MODELS = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise LLMError("Falta la API key de Anthropic (BYOK)")
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=3)

    async def _parse(self, system: str, user: str, output_format, max_tokens: int):  # noqa: ANN001
        try:
            resp = await self._client.messages.parse(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=output_format,
                output_config={"effort": "low"},
            )
        except anthropic.AuthenticationError as e:
            raise LLMError("API key de Anthropic inválida") from e
        except anthropic.RateLimitError as e:
            raise LLMError("Límite de uso de la API alcanzado; intenta más tarde") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"Error de la API de Anthropic ({e.status_code})") from e
        except anthropic.APIConnectionError as e:
            raise LLMError("No se pudo conectar con la API de Anthropic") from e
        if resp.stop_reason == "refusal":
            raise LLMError("El modelo rechazó la solicitud")
        if resp.stop_reason == "max_tokens" or resp.parsed_output is None:
            raise LLMError("Respuesta incompleta del modelo")
        return resp.parsed_output

    async def classify(self, segments: list[Segment], lang: str) -> list[ClauseVerdict]:
        out: BatchVerdict = await self._parse(
            classify_system_prompt(lang), classify_user_prompt(segments), BatchVerdict, 16000
        )
        return out.verdicts

    async def summarize_diff(self, changes: list[dict], lang: str) -> DiffVerdict:
        return await self._parse(diff_system_prompt(lang), diff_user_prompt(changes), DiffVerdict, 16000)
