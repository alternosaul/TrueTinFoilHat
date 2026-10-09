from app.config import get_settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LLMError, Provider
from app.llm.ollama_provider import OllamaProvider


def make_provider(provider: str, model: str | None, api_key: str | None) -> Provider:
    settings = get_settings()
    if provider == "anthropic":
        return AnthropicProvider(api_key=api_key or "", model=model or settings.anthropic_default_model)
    if provider == "ollama":
        if not settings.ollama_enabled:
            raise LLMError("Ollama no está disponible en modo hosted; usa tu propia API key")
        return OllamaProvider(model=model)
    raise LLMError(f"Proveedor desconocido: {provider}")
