from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Analysis, Company, Comparison, Document
from app.db.session import get_db

router = APIRouter(prefix="/api", tags=["data"])


def analysis_brief(a: Analysis) -> dict:
    return {
        "id": a.id, "document_id": a.document_id, "analyzed_at": a.analyzed_at, "last_seen_at": a.last_seen_at,
        "source": a.source, "snapshot_ts": a.snapshot_ts, "provider": a.provider, "model": a.model,
        "rubric_version": a.rubric_version, "title": a.title, "score": a.score,
        "counts": {"green": a.count_green, "yellow": a.count_yellow, "red": a.count_red},
    }


@router.get("/companies")
def list_companies(db: Session = Depends(get_db)) -> list[dict]:
    """Galería: cada empresa con su último análisis en vivo por documento."""
    companies = db.scalars(
        select(Company).options(selectinload(Company.documents).selectinload(Document.analyses)).order_by(Company.name)
    ).all()
    out = []
    for c in companies:
        docs = []
        for d in c.documents:
            live = [a for a in d.analyses if a.source == "live"]
            latest = max(live, key=lambda a: a.analyzed_at, default=None)
            docs.append({"id": d.id, "url": d.url, "doc_type": d.doc_type,
                         "latest": analysis_brief(latest) if latest else None,
                         "n_analyses": len(live)})
        last = max((d["latest"]["analyzed_at"] for d in docs if d["latest"]), default=None)
        out.append({"id": c.id, "name": c.name, "domain": c.domain, "last_analyzed_at": last, "documents": docs})
    out.sort(key=lambda c: c["last_analyzed_at"] or datetime.min, reverse=True)
    return out


@router.get("/companies/{company_id}")
def get_company(company_id: int, db: Session = Depends(get_db)) -> dict:
    c = db.get(Company, company_id)
    if not c:
        raise HTTPException(404, "Empresa no encontrada")
    return {
        "id": c.id, "name": c.name, "domain": c.domain,
        "documents": [
            {"id": d.id, "url": d.url, "doc_type": d.doc_type,
             "analyses": [analysis_brief(a) for a in sorted(d.analyses, key=lambda a: a.analyzed_at, reverse=True)]}
            for d in c.documents
        ],
    }


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: int, db: Session = Depends(get_db)) -> dict:
    a = db.get(Analysis, analysis_id)
    if not a:
        raise HTTPException(404, "Análisis no encontrado")
    comparison = db.scalar(
        select(Comparison).where(Comparison.new_analysis_id == a.id).order_by(Comparison.created_at.desc())
    )
    return {
        **analysis_brief(a),
        "url": a.document.url,
        "doc_type": a.document.doc_type,
        "company": {"id": a.document.company.id, "name": a.document.company.name, "domain": a.document.company.domain},
        "comparison_id": comparison.id if comparison else None,
        "clauses": [
            {"idx": c.idx, "heading": c.heading, "text": c.text, "color": c.color, "category": c.category,
             "explanation": c.explanation}
            for c in a.clauses
        ],
    }


@router.get("/comparisons/{comparison_id}")
def get_comparison(comparison_id: int, db: Session = Depends(get_db)) -> dict:
    cmp = db.get(Comparison, comparison_id)
    if not cmp:
        raise HTTPException(404, "Comparación no encontrada")
    old, new = db.get(Analysis, cmp.old_analysis_id), db.get(Analysis, cmp.new_analysis_id)
    return {
        "id": cmp.id, "created_at": cmp.created_at, "summary": cmp.summary, "changes": cmp.changes,
        "old": analysis_brief(old), "new": analysis_brief(new), "url": new.document.url,
    }


@router.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    return {
        "companies": db.scalar(select(func.count(Company.id))),
        "documents": db.scalar(select(func.count(Document.id))),
        "analyses": db.scalar(select(func.count(Analysis.id))),
    }
