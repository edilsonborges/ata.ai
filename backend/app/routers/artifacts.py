from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.config import get_settings
from app.db import session_dependency
from app.deps import current_user
from app.models import Job, User

router = APIRouter(prefix="/api/jobs", tags=["artifacts"])
settings = get_settings()


_ALLOWED = {
    "transcricao.vtt": "text/vtt",
    "analise.md": "text/markdown",
    "dashboard.html": "text/html",
}


@router.get("/{job_id}/artifacts/{name}")
async def get_artifact(
    job_id: UUID,
    name: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> FileResponse:
    if name not in _ALLOWED:
        raise HTTPException(404, "unknown artifact")
    job = (await session.exec(
        select(Job).where(Job.id == job_id, Job.user_id == user.id)
    )).first()
    if not job or not job.folder_name:
        raise HTTPException(404, "not found")
    path = settings.analyses_path / job.folder_name / name
    if not path.exists():
        raise HTTPException(404, "file missing")
    return FileResponse(path, media_type=_ALLOWED[name], filename=name if name != "dashboard.html" else None)
