"""Registro en memoria de trabajos de análisis con eventos de progreso (para SSE)."""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Job:
    id: str
    status: str = "pending"  # pending | running | done | error
    events: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    error: str | None = None
    _cond: asyncio.Condition = field(default_factory=asyncio.Condition)

    async def emit(self, stage: str, message: str, **data: Any) -> None:
        async with self._cond:
            self.events.append({"stage": stage, "message": message, **data})
            self._cond.notify_all()

    async def wait_for(self, n_seen: int) -> None:
        async with self._cond:
            await self._cond.wait_for(lambda: len(self.events) > n_seen or self.status in ("done", "error"))


_jobs: dict[str, Job] = {}


def create_job() -> Job:
    job = Job(id=uuid.uuid4().hex)
    _jobs[job.id] = job
    return job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)
