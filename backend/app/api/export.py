"""Export/import de la base de datos para compartir y fusionar galerías entre instalaciones."""

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Analysis, Clause, Company, Comparison, Document
from app.db.session import get_db
from app.pipeline import upsert_document

router = APIRouter(prefix="/api", tags=["export"])
EXPORT_VERSION = 1


def _key(a: Analysis) -> list:
    return [a.document.url, a.content_hash, a.provider, a.model, a.rubric_version, a.source]


@router.get("/export")
def export(format: str = Query("json", pattern="^(json|csv)$"), db: Session = Depends(get_db)):
    companies = db.scalars(
        select(Company).options(
            selectinload(Company.documents).selectinload(Document.analyses).selectinload(Analysis.clauses))
    ).all()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["company", "domain", "url", "doc_type", "analyzed_at", "source", "snapshot_ts", "provider",
                    "model", "rubric_version", "score", "green", "yellow", "red"])
        for c in companies:
            for d in c.documents:
                for a in d.analyses:
                    w.writerow([c.name, c.domain, d.url, d.doc_type, a.analyzed_at.isoformat(), a.source,
                                a.snapshot_ts, a.provider, a.model, a.rubric_version, a.score,
                                a.count_green, a.count_yellow, a.count_red])
        return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={
            "Content-Disposition": f'attachment; filename="truetinfoilhat-{stamp}.csv"'})

    comparisons = db.scalars(select(Comparison)).all()
    by_id = {a.id: a for c in companies for d in c.documents for a in d.analyses}
    payload = {
        "export_version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "companies": [{
            "name": c.name, "domain": c.domain,
            "documents": [{
                "url": d.url, "doc_type": d.doc_type,
                "analyses": [{
                    "analyzed_at": a.analyzed_at.isoformat(), "last_seen_at": a.last_seen_at.isoformat(),
                    "source": a.source, "snapshot_ts": a.snapshot_ts, "content_hash": a.content_hash,
                    "provider": a.provider, "model": a.model, "rubric_version": a.rubric_version,
                    "title": a.title, "summary": a.summary, "score": a.score,
                    "counts": [a.count_green, a.count_yellow, a.count_red],
                    "clauses": [[cl.idx, cl.heading, cl.text, cl.color, cl.category, cl.explanation]
                                for cl in a.clauses],
                } for a in d.analyses],
            } for d in c.documents],
        } for c in companies],
        "comparisons": [{
            "old": _key(by_id[cmp.old_analysis_id]), "new": _key(by_id[cmp.new_analysis_id]),
            "created_at": cmp.created_at.isoformat(), "summary": cmp.summary, "changes": cmp.changes,
        } for cmp in comparisons if cmp.old_analysis_id in by_id and cmp.new_analysis_id in by_id],
    }
    return JSONResponse(payload, headers={
        "Content-Disposition": f'attachment; filename="truetinfoilhat-{stamp}.json"'})


@router.post("/import")
def import_db(payload: dict = Body(...), db: Session = Depends(get_db)) -> dict:
    """Fusiona un export JSON. Los análisis existentes (misma URL+hash+modelo+rúbrica) se omiten."""
    added = skipped = 0
    key_to_id: dict[tuple, int] = {}
    for c in payload.get("companies", []):
        for d in c.get("documents", []):
            doc = upsert_document(db, d["url"], None)
            doc.doc_type = d.get("doc_type", doc.doc_type)
            if doc.company.name != c["name"] and doc.company.domain == c["domain"]:
                doc.company.name = c["name"]
            for a in d.get("analyses", []):
                key = (d["url"], a["content_hash"], a["provider"], a["model"], a["rubric_version"], a["source"])
                existing = db.scalar(select(Analysis).where(
                    Analysis.document_id == doc.id, Analysis.content_hash == a["content_hash"],
                    Analysis.provider == a["provider"], Analysis.model == a["model"],
                    Analysis.rubric_version == a["rubric_version"], Analysis.source == a["source"]))
                if existing:
                    key_to_id[key] = existing.id
                    skipped += 1
                    continue
                g, y, r = a["counts"]
                new = Analysis(
                    document_id=doc.id, analyzed_at=datetime.fromisoformat(a["analyzed_at"]),
                    last_seen_at=datetime.fromisoformat(a.get("last_seen_at") or a["analyzed_at"]),
                    source=a["source"], snapshot_ts=a.get("snapshot_ts"), content_hash=a["content_hash"],
                    provider=a["provider"], model=a["model"], rubric_version=a["rubric_version"],
                    title=a.get("title"), summary=a.get("summary"), score=a["score"],
                    count_green=g, count_yellow=y, count_red=r,
                    clauses=[Clause(idx=i, heading=h, text=t, color=col, category=cat, explanation=exp)
                             for i, h, t, col, cat, exp in a["clauses"]],
                )
                db.add(new)
                db.flush()
                key_to_id[key] = new.id
                added += 1
    n_cmp = 0
    for cmp in payload.get("comparisons", []):
        old_id, new_id = key_to_id.get(tuple(cmp["old"])), key_to_id.get(tuple(cmp["new"]))
        if old_id and new_id and not db.scalar(select(Comparison).where(
                Comparison.old_analysis_id == old_id, Comparison.new_analysis_id == new_id)):
            db.add(Comparison(old_analysis_id=old_id, new_analysis_id=new_id,
                              created_at=datetime.fromisoformat(cmp["created_at"]),
                              summary=cmp.get("summary"), changes=cmp.get("changes", [])))
            n_cmp += 1
    db.commit()
    return {"analyses_added": added, "analyses_skipped": skipped, "comparisons_added": n_cmp}
