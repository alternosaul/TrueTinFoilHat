"""Segmenta un documento legal en cláusulas usando headings y numeración."""

import re
from dataclasses import dataclass

MAX_CLAUSE_CHARS = 1500
MIN_CLAUSE_CHARS = 120
TINY_CLAUSE_CHARS = 40

_MD_HEADING = re.compile(r"^#{1,6}\s+(.*)$")
_NUMBERED = re.compile(
    r"^(?:(?:section|sección|article|artículo|cláusula|clause)\s+)?"
    r"(\d+(?:\.\d+)*|[IVXLC]+)[.)]?\s+(\S.{0,120})$",
    re.IGNORECASE,
)
_MD_ESCAPE = re.compile(r"\\([.\-*_#()\[\]!+])")
_LIST_ITEM = re.compile(r"^(?:[-*•]|\d+[.)]|\([a-z0-9]+\))\s")
_SENTENCE_END = re.compile(r"(?<=[.;:!?])\s+(?=[A-Z0-9\"“(¿¡])")
_BOLD_LINE = re.compile(r"^\*\*(.{3,120})\*\*:?$")


@dataclass
class Segment:
    idx: int
    heading: str | None
    text: str


def _heading_of(line: str) -> str | None:
    if m := _MD_HEADING.match(line):
        return m.group(1).strip(" *")
    if m := _BOLD_LINE.match(line):
        return m.group(1).strip()
    if (m := _NUMBERED.match(line)) and len(line) <= 120 and not line.rstrip().endswith((".", ";", ",")):
        return line.strip()
    if 3 < len(line) <= 80 and line.isupper() and any(c.isalpha() for c in line):
        return line.strip()
    return None


def _split_long(paragraphs: list[str]) -> list[str]:
    """Agrupa párrafos en trozos de hasta MAX_CLAUSE_CHARS."""
    pieces: list[str] = []
    for p in paragraphs:
        pieces.extend(_SENTENCE_END.split(p) if len(p) > MAX_CLAUSE_CHARS else [p])
    chunks: list[str] = []
    buf = ""
    for p in pieces:
        if buf and len(buf) + len(p) + 2 > MAX_CLAUSE_CHARS:
            chunks.append(buf)
            buf = p
        else:
            sep = " " if buf and not _LIST_ITEM.match(p) and not buf.endswith((".", ":", ";")) else "\n\n"
            buf = f"{buf}{sep}{p}" if buf else p
    if buf:
        chunks.append(buf)
    return chunks


def segment(text: str) -> list[Segment]:
    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    para: list[str] = []

    def flush_para() -> None:
        if para:
            sections[-1][1].append(" ".join(para).strip())
            para.clear()

    text = _MD_ESCAPE.sub(r"\1", text)
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush_para()
            continue
        if (h := _heading_of(line)) is not None:
            flush_para()
            sections.append((h, []))
            continue
        # bullets en su propio párrafo
        if _LIST_ITEM.match(line) and para:
            flush_para()
        para.append(line)
    flush_para()

    raw_segments: list[tuple[str | None, str]] = []
    for heading, paras in sections:
        paras = [p for p in paras if p]
        if not paras:
            continue
        for chunk in _split_long(paras):
            raw_segments.append((heading, chunk))

    # fusiona fragmentos muy cortos con el siguiente (el heading del corto pasa al texto)
    merged: list[tuple[str | None, str]] = []
    for heading, chunk in raw_segments:
        prev_heading, prev_text = merged[-1] if merged else (None, "")
        tiny = len(prev_text) < TINY_CLAUSE_CHARS
        short_same_section = len(prev_text) < MIN_CLAUSE_CHARS and prev_heading in (None, heading)
        if merged and (tiny or short_same_section):
            if prev_heading != heading and prev_heading:
                prev_text = f"{prev_heading}: {prev_text}"
            merged[-1] = (heading or prev_heading, f"{prev_text}\n\n{chunk}")
        else:
            merged.append((heading, chunk))

    return [Segment(idx=i, heading=h, text=t) for i, (h, t) in enumerate(merged)]
