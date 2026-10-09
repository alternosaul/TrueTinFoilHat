import asyncio
import json
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, HttpUrl
from sse_starlette.sse import EventSourceResponse

from app.jobs import create_job, get_job
from app.llm.base import LLMError
from app.llm.factory import make_provider
from app.pipeline import run_analysis

router = APIRouter(prefix="/api", tags=["analyze"])
_tasks: set[asyncio.Task] = set()


class AnalyzeRequest(BaseModel):
    url: HttpUrl
    provider: Literal["anthropic", "ollama"] = "ollama"
    model: str | None = None
    lang: Literal["es", "en"] = "es"
    compare: bool = True


@router.post("/analyze")
async def analyze(req: AnalyzeRequest, x_llm_key: str | None = Header(default=None)) -> dict:
    # La key (BYOK) solo vive en memoria durante este trabajo: no se guarda ni se registra.
    try:
        provider = make_provider(req.provider, req.model, x_llm_key)
    except LLMError as e:
        raise HTTPException(400, str(e)) from e
    job = create_job()
    task = asyncio.create_task(run_analysis(job, str(req.url), provider, req.lang, req.compare))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return {"job_id": job.id}


@router.get("/jobs/{job_id}")
async def job_status(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    return {"id": job.id, "status": job.status, "events": job.events, "result": job.result, "error": job.error}


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str) -> EventSourceResponse:
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")

    async def stream():
        seen = 0
        while True:
            while seen < len(job.events):
                yield {"event": "progress", "data": json.dumps(job.events[seen], ensure_ascii=False)}
                seen += 1
            if job.status in ("done", "error"):
                return
            await job.wait_for(seen)

    return EventSourceResponse(stream())
