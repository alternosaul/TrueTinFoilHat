"""Interfaz común de proveedores LLM + prompts y esquemas compartidos."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Protocol

import yaml
from pydantic import BaseModel, Field

from app.extract.segment import Segment

Color = Literal["green", "yellow", "red"]
Impact = Literal["better", "worse", "neutral"]


@lru_cache
def load_rubric() -> dict:
    return yaml.safe_load((Path(__file__).parent / "rubric.yaml").read_text())


def rubric_version() -> str:
    return load_rubric()["version"]


def category_keys() -> list[str]:
    return list(load_rubric()["categories"].keys())


class ClauseVerdict(BaseModel):
    idx: int = Field(description="Índice de la cláusula tal como viene en la entrada")
    color: Color
    category: str = Field(description="Una de las claves de categoría de la rúbrica")
    explanation: str = Field(description="1-2 frases en lenguaje simple: qué significa para el usuario")


class BatchVerdict(BaseModel):
    verdicts: list[ClauseVerdict]


class ChangeVerdict(BaseModel):
    change_id: int
    impact: Impact = Field(description="better = mejor para el usuario, worse = peor")
    explanation: str


class DiffVerdict(BaseModel):
    summary: str = Field(description="Resumen de 2-4 frases de lo que cambió y si es mejor o peor para el usuario")
    changes: list[ChangeVerdict]


LANG_NAMES = {"es": "español", "en": "English"}


def classify_system_prompt(lang: str) -> str:
    rubric = yaml.safe_dump(load_rubric(), allow_unicode=True, sort_keys=False)
    return (
        "Eres un analista de defensa del consumidor. Lees cláusulas de términos de servicio y "
        "políticas de privacidad y evalúas su impacto en el usuario siguiendo ESTRICTAMENTE esta rúbrica:\n\n"
        f"{rubric}\n"
        "Para cada cláusula devuelve: idx, color (green/yellow/red), category (una clave de `categories`) y "
        f"explanation: 1-2 frases en {LANG_NAMES.get(lang, lang)}, sin jerga legal, dirigidas al usuario "
        "(\"La empresa puede...\"). Juzga solo por el texto dado; si es informativo o neutro usa green. "
        "Devuelve exactamente un veredicto por cláusula recibida."
    )


def classify_user_prompt(segments: list[Segment]) -> str:
    parts = []
    for s in segments:
        heading = f"Sección: {s.heading}\n" if s.heading else ""
        parts.append(f"<clause idx=\"{s.idx}\">\n{heading}{s.text}\n</clause>")
    return "Clasifica estas cláusulas:\n\n" + "\n\n".join(parts)


def diff_system_prompt(lang: str) -> str:
    return (
        "Comparas dos versiones de unos términos de servicio o política de privacidad. Recibes una lista de "
        "cambios (añadido, eliminado, modificado) con el texto anterior y el nuevo. Para cada cambio indica si "
        "es better, worse o neutral para el usuario y explica en una frase simple qué cambia para él (sin repetir la "
        "etiqueta better/worse/neutral en la explicación). Luego da un resumen general. "
        f"Responde en {LANG_NAMES.get(lang, lang)}. Ignora cambios puramente cosméticos (marcándolos neutral)."
    )


def diff_user_prompt(changes: list[dict]) -> str:
    parts = []
    for c in changes:
        parts.append(
            f"<change id=\"{c['id']}\" type=\"{c['type']}\">\n"
            f"<old>{c.get('old_text') or ''}</old>\n<new>{c.get('new_text') or ''}</new>\n</change>"
        )
    return "Cambios entre la versión anterior y la actual:\n\n" + "\n\n".join(parts)


class LLMError(RuntimeError):
    pass


class Provider(Protocol):
    name: str
    model: str

    async def classify(self, segments: list[Segment], lang: str) -> list[ClauseVerdict]: ...

    async def summarize_diff(self, changes: list[dict], lang: str) -> DiffVerdict: ...


def normalize_verdicts(segments: list[Segment], verdicts: list[ClauseVerdict]) -> list[ClauseVerdict]:
    """Garantiza un veredicto válido por segmento (rellena faltantes, corrige categorías desconocidas)."""
    keys = set(category_keys())
    by_idx = {v.idx: v for v in verdicts}
    out = []
    for s in segments:
        v = by_idx.get(s.idx)
        if v is None:
            v = ClauseVerdict(idx=s.idx, color="yellow", category="other",
                              explanation="No se pudo clasificar esta cláusula automáticamente; revísala.")
        elif v.category not in keys:
            v = v.model_copy(update={"category": "other"})
        out.append(v)
    return out
