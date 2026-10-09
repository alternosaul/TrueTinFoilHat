"""Alineación de cláusulas entre dos versiones de un documento."""

import difflib
import re

from rapidfuzz import fuzz

from app.extract.segment import Segment

MODIFIED_THRESHOLD = 55  # similitud mínima (0-100) para considerar dos cláusulas "la misma, modificada"
SAME_HEADING_BONUS = 15  # misma sección → más probable que sea la misma cláusula reescrita
MAX_CHANGE_TEXT = 1500


def normalize_text(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def align(old: list[Segment], new: list[Segment]) -> list[dict]:
    """Devuelve cambios: [{id, type: added|removed|modified, old_idx, new_idx, old_text, new_text, similarity}]."""
    old_n = [normalize_text(s.text) for s in old]
    new_n = [normalize_text(s.text) for s in new]

    matcher = difflib.SequenceMatcher(a=old_n, b=new_n, autojunk=False)
    unmatched_old: list[int] = []
    unmatched_new: list[int] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            unmatched_old.extend(range(i1, i2))
            unmatched_new.extend(range(j1, j2))

    # empareja codiciosamente por similitud las cláusulas no idénticas
    def similarity(i: int, j: int) -> float:
        score = fuzz.token_sort_ratio(old_n[i], new_n[j])
        if old[i].heading and old[i].heading == new[j].heading:
            score += SAME_HEADING_BONUS
        return score

    candidates = sorted(
        ((similarity(i, j), i, j) for i in unmatched_old for j in unmatched_new), reverse=True,
    )
    used_old: set[int] = set()
    used_new: set[int] = set()
    pairs: list[tuple[int, int, float]] = []
    for score, i, j in candidates:
        if score < MODIFIED_THRESHOLD:
            break
        if i in used_old or j in used_new:
            continue
        used_old.add(i)
        used_new.add(j)
        pairs.append((i, j, score))

    raw: list[dict] = []
    for i, j, score in pairs:
        if old_n[i] == new_n[j]:  # solo cambios de puntuación/espacios
            continue
        raw.append({"type": "modified", "old_idx": i, "new_idx": j, "similarity": round(min(score, 100), 1)})
    for i in unmatched_old:
        if i not in used_old:
            raw.append({"type": "removed", "old_idx": i, "new_idx": None, "similarity": None})
    for j in unmatched_new:
        if j not in used_new:
            raw.append({"type": "added", "old_idx": None, "new_idx": j, "similarity": None})

    def sort_key(c: dict) -> tuple[float, float]:
        return (c["new_idx"] if c["new_idx"] is not None else c["old_idx"] - 0.5, c["old_idx"] or 0)

    changes = []
    for n, c in enumerate(sorted(raw, key=sort_key)):
        changes.append({
            "id": n,
            **c,
            "old_heading": old[c["old_idx"]].heading if c["old_idx"] is not None else None,
            "new_heading": new[c["new_idx"]].heading if c["new_idx"] is not None else None,
            "old_text": old[c["old_idx"]].text if c["old_idx"] is not None else None,
            "new_text": new[c["new_idx"]].text if c["new_idx"] is not None else None,
        })
    return changes


def for_llm(changes: list[dict], max_changes: int = 40) -> list[dict]:
    """Versión recortada de los cambios para enviar al LLM."""
    def cut(t: str | None) -> str | None:
        return t if t is None or len(t) <= MAX_CHANGE_TEXT else t[:MAX_CHANGE_TEXT] + " […]"

    return [
        {"id": c["id"], "type": c["type"], "old_text": cut(c["old_text"]), "new_text": cut(c["new_text"])}
        for c in changes[:max_changes]
    ]
