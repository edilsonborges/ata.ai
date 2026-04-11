import asyncio
import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import psycopg
from app.config import get_settings
from app.db import session_dependency
from app.deps import current_user
from app.models import Job, User

router = APIRouter(prefix="/api/jobs", tags=["events"])
settings = get_settings()


def _psycopg_dsn() -> str:
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    return url


async def _listen_for_job(job_id: UUID):
    """Connect to postgres, LISTEN job_event, yield matching payloads as SSE lines."""
    async with await psycopg.AsyncConnection.connect(_psycopg_dsn(), autocommit=True) as conn:
        async with conn.cursor() as cur:
            await cur.execute("LISTEN job_event;")
        gen = conn.notifies()
        async for note in gen:
            try:
                payload = json.loads(note.payload)
            except Exception:
                continue
            if payload.get("job_id") != str(job_id):
                continue
            yield f"data: {json.dumps(payload)}\n\n"
            if payload.get("phase") == "done" or payload.get("level") == "error":
                break


@router.get("/{job_id}/events")
async def job_events(
    job_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> StreamingResponse:
    job = (await session.exec(
        select(Job).where(Job.id == job_id, Job.user_id == user.id)
    )).first()
    if not job:
        raise HTTPException(404, "job not found")

    async def stream():
        # evento inicial com estado atual do job
        initial = {
            "job_id": str(job_id),
            "phase": job.phase,
            "progress_pct": job.progress_pct,
            "message": "snapshot",
            "level": "info",
        }
        yield f"data: {json.dumps(initial)}\n\n"

        # se já está terminal, encerra
        if job.status in {"done", "error", "canceled"}:
            return

        async for line in _listen_for_job(job_id):
            yield line

    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })
