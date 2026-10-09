from app.extract.segment import Segment
from app.llm.base import ChangeVerdict, ClauseVerdict, DiffVerdict


class FakeProvider:
    """Clasifica por palabras clave; sirve para tests sin red."""

    name = "fake"
    model = "fake-1"

    def __init__(self) -> None:
        self.classified = 0

    async def classify(self, segments: list[Segment], lang: str) -> list[ClauseVerdict]:
        self.classified += len(segments)
        out = []
        for s in segments:
            t = s.text.lower()
            if "arbitration" in t or "sell" in t:
                color, cat = "red", "arbitration" if "arbitration" in t else "data_sharing"
            elif "cookie" in t:
                color, cat = "yellow", "tracking"
            else:
                color, cat = "green", "other"
            out.append(ClauseVerdict(idx=s.idx, color=color, category=cat, explanation=f"fake {color}"))
        return out

    async def summarize_diff(self, changes: list[dict], lang: str) -> DiffVerdict:
        return DiffVerdict(
            summary=f"{len(changes)} cambios",
            changes=[ChangeVerdict(change_id=c["id"], impact="worse" if c["type"] == "added" else "neutral",
                                   explanation="fake") for c in changes],
        )
