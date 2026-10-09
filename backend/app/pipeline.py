"""Orquesta: fetch → segment → classify → wayback → diff → persist."""

import asyncio
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import wayback
from app.config import get_settings
from app.db.models import Analysis, Clause, Company, Comparison, Document
from app.db.session import SessionLocal
from app.diff import align, for_llm, normalize_text
from app.extract.fetch import ExtractedDoc, fetch_document
from app.extract.segment import Segment, segment
from app.jobs import Job
from app.llm.base import ClauseVerdict, LLMError, Provider, normalize_verdicts, rubric_version

log = logging.getLogger(__name__)

MAX_SEGMENTS = 250


def domain_of(url: str) -> str:
    host = urlparse(url).hostname or url
    return host.removeprefix("www.")


def company_name_from_domain(domain: str) -> str:
    parts = domain.split(".")
    core = parts[-2] if len(parts) >= 2 else parts[0]
    return core.capitalize()


def guess_doc_type(url: str, title: str | None) -> str:
    hay = f"{url} {title or ''}".lower()
    if any(k in hay for k in ("privacy", "privacidad", "datenschutz", "cookie")):
        return "privacy"
    if any(k in hay for k in ("terms", "tos", "condiciones", "términos", "terminos", "legal", "agreement", "eula")):
        return "tos"
    return "other"


def upsert_document(db: Session, url: str, title: str | None) -> Document:
    doc = db.scalar(select(Document).where(Document.url == url))
    if doc:
        return doc
    domain = domain_of(url)
    company = db.scalar(select(Company).where(Company.domain == domain))
    if not company:
        company = Company(name=company_name_from_domain(domain), domain=domain)
        db.add(company)
        db.flush()
    doc = Document(company_id=company.id, url=url, doc_type=guess_doc_type(url, title))
    db.add(doc)
    db.flush()
    return doc


def score_of(green: int, yellow: int, red: int) -> int:
    total = green + yellow + red
    return round(100 * (green + 0.5 * yellow) / total) if total else 0


async def classify_all(provider: Provider, segments: list[Segment], lang: str, job: Job, label: str) -> list:
    size = get_settings().classify_batch_size
    batches = [segments[i:i + size] for i in range(0, len(segments), size)]
    sem = asyncio.Semaphore(1 if provider.name == "ollama" else 4)
    done = 0

    async def run(batch: list[Segment]) -> list:
        nonlocal done
        async with sem:
            verdicts = await provider.classify(batch, lang)
        done += len(batch)
        await job.emit("classifying", f"Clasificando {label}: {done}/{len(segments)} cláusulas",
                       done=done, total=len(segments))
        return normalize_verdicts(batch, verdicts)

    results = await asyncio.gather(*(run(b) for b in batches))
    return [v for r in results for v in r]


async def analyze_doc(
    db: Session, provider: Provider, document: Document, extracted: ExtractedDoc, lang: str, job: Job,
    source: str, snapshot_ts: str | None = None, label: str = "versión actual", reuse_from: Analysis | None = None,
) -> tuple[Analysis, list[Segment], bool]:
    """Analiza (o reutiliza de cache) un texto. Devuelve (analysis, segmentos, cache_hit).

    Con `reuse_from`, las cláusulas cuyo texto es idéntico a una de ese análisis copian su veredicto
    en vez de volver a pasar por el LLM (entre versiones de un mismo documento, casi todo coincide).
    """
    segments = segment(extracted.text)[:MAX_SEGMENTS]
    cached = db.scalar(
        select(Analysis)
        .where(Analysis.document_id == document.id, Analysis.content_hash == extracted.content_hash,
               Analysis.provider == provider.name, Analysis.model == provider.model,
               Analysis.rubric_version == rubric_version(), Analysis.source == source)
        .order_by(Analysis.analyzed_at.desc())
    )
    if cached:
        cached.last_seen_at = datetime.now(timezone.utc)
        db.commit()
        await job.emit("cache", f"Texto sin cambios desde {cached.analyzed_at:%Y-%m-%d}; reutilizando análisis ({label})")
        return cached, segments, True

    await job.emit("segmenting", f"{len(segments)} cláusulas detectadas ({label})", total=len(segments))
    known = {normalize_text(c.text): c for c in reuse_from.clauses} if reuse_from else {}
    todo = [s for s in segments if normalize_text(s.text) not in known]
    if len(todo) < len(segments):
        await job.emit("cache", f"{len(segments) - len(todo)} cláusulas idénticas a la otra versión; "
                                f"se clasifican solo {len(todo)} ({label})")
    fresh = {v.idx: v for v in (await classify_all(provider, todo, lang, job, label) if todo else [])}
    verdicts = []
    for s in segments:
        if (v := fresh.get(s.idx)) is None:
            c = known[normalize_text(s.text)]
            v = ClauseVerdict(idx=s.idx, color=c.color, category=c.category, explanation=c.explanation)
        verdicts.append(v)
    counts = {c: sum(v.color == c for v in verdicts) for c in ("green", "yellow", "red")}
    analysis = Analysis(
        document_id=document.id, source=source, snapshot_ts=snapshot_ts, content_hash=extracted.content_hash,
        provider=provider.name, model=provider.model, rubric_version=rubric_version(), title=extracted.title,
        count_green=counts["green"], count_yellow=counts["yellow"], count_red=counts["red"],
        score=score_of(counts["green"], counts["yellow"], counts["red"]),
        clauses=[
            Clause(idx=s.idx, heading=s.heading, text=s.text, color=v.color, category=v.category,
                   explanation=v.explanation)
            for s, v in zip(segments, verdicts)
        ],
    )
    db.add(analysis)
    db.commit()
    return analysis, segments, False


async def compare_with_wayback(
    db: Session, provider: Provider, document: Document, current: Analysis, current_segments: list[Segment],
    url: str, lang: str, job: Job,
) -> Comparison | None:
    target = wayback.target_timestamp(get_settings().wayback_years_back)
    await job.emit("wayback", f"Buscando versión archivada cercana a {target[:4]}-{target[4:6]}-{target[6:]}")
    try:
        snap = await wayback.closest_snapshot(url, target)
    except Exception as e:  # noqa: BLE001 — Wayback es best-effort
        await job.emit("wayback", f"Wayback Machine no respondió: {e}")
        return None
    if not snap:
        await job.emit("wayback", "No hay versiones archivadas de esta URL")
        return None
    await job.emit("wayback", f"Usando snapshot del {snap.date:%Y-%m-%d}", snapshot=snap.view_url)

    html = await wayback.fetch_snapshot_html(snap)
    old_doc = await fetch_document(url, html=html)
    old_analysis, old_segments, _ = await analyze_doc(
        db, provider, document, old_doc, lang, job, source="wayback", snapshot_ts=snap.timestamp,
        label=f"versión {snap.date:%Y-%m}", reuse_from=current,
    )

    existing = db.scalar(select(Comparison).where(
        Comparison.old_analysis_id == old_analysis.id, Comparison.new_analysis_id == current.id))
    if existing:
        return existing

    await job.emit("diff", "Comparando versiones")
    changes = align(old_segments, current_segments)
    summary = "Sin cambios relevantes entre ambas versiones."
    if changes:
        try:
            verdict = await provider.summarize_diff(for_llm(changes), lang)
            impacts = {c.change_id: c for c in verdict.changes}
            for c in changes:
                if v := impacts.get(c["id"]):
                    c["impact"], c["explanation"] = v.impact, v.explanation
            summary = verdict.summary
        except LLMError as e:
            summary = f"No se pudo resumir el diff: {e}"
    comparison = Comparison(old_analysis_id=old_analysis.id, new_analysis_id=current.id,
                            summary=summary, changes=changes)
    db.add(comparison)
    db.commit()
    return comparison


async def run_analysis(job: Job, url: str, provider: Provider, lang: str, compare: bool) -> None:
    job.status = "running"
    try:
        with SessionLocal() as db:
            await job.emit("fetching", f"Descargando {url}")
            extracted = await fetch_document(url)
            document = upsert_document(db, url, extracted.title)
            db.commit()
            analysis, segments, cache_hit = await analyze_doc(db, provider, document, extracted, lang, job, "live")
            comparison = None
            if compare:
                try:
                    comparison = await compare_with_wayback(db, provider, document, analysis, segments, url, lang, job)
                except (httpx.HTTPError, ValueError) as e:  # Wayback es best-effort; el análisis en vivo ya está guardado
                    db.rollback()
                    await job.emit("wayback", f"No se pudo comparar con la versión archivada: {e}")
            job.result = {
                "analysis_id": analysis.id,
                "company_id": document.company_id,
                "comparison_id": comparison.id if comparison else None,
                "cached": cache_hit,
            }
        job.status = "done"
        await job.emit("done", "Análisis completo", **job.result)
    except Exception as e:  # noqa: BLE001
        log.exception("analysis failed for %s", url)
        job.status = "error"
        job.error = str(e) if isinstance(e, (LLMError, ValueError)) else f"{type(e).__name__}: {e}"
        await job.emit("error", job.error)
