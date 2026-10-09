from fastapi import APIRouter

from app.config import get_settings
from app.llm.anthropic_provider import CLAUDE_MODELS
from app.llm.base import load_rubric
from app.llm.ollama_provider import list_ollama_models

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/providers")
async def providers() -> dict:
    s = get_settings()
    out = {
        "mode": s.mode,
        "providers": [{
            "id": "anthropic", "label": "Claude (tu API key)", "requires_key": True,
            "models": CLAUDE_MODELS, "default_model": s.anthropic_default_model,
        }],
    }
    if s.ollama_enabled:
        models = await list_ollama_models()
        out["providers"].insert(0, {
            "id": "ollama", "label": "Ollama (local)", "requires_key": False, "available": bool(models),
            "models": models, "default_model": s.ollama_model if s.ollama_model in models else (models[0] if models else s.ollama_model),
        })
    return out


@router.get("/rubric")
def rubric() -> dict:
    return load_rubric()
