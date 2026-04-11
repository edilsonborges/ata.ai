from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.config import get_settings
from app.db import session_dependency
from app.deps import current_user
from app.models import Job, JobEvent, User
from app.schemas.jobs import JobCreated, JobRead
from app.services.storage import is_supported, upload_path

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
settings = get_settings()


@router.post("", response_model=JobCreated, status_code=status.HTTP_201_CREATED)
async def create_job(
    file: UploadFile = File(...),
    whisper_model: str = Form(...),
    llm_provider: str = Form(...),
    llm_model: str = Form(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> JobCreated:
    if not is_supported(file.filename or ""):
        raise HTTPException(400, "unsupported file type")

    job = Job(
        user_id=user.id,
        input_filename=file.filename or "upload.bin",
        input_size_bytes=0,
        whisper_model=whisper_model,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )
    session.add(job)
    await session.flush()

    dst = upload_path(job.id, job.input_filename)
    size = 0
    with dst.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_mb * 1024 * 1024:
                dst.unlink(missing_ok=True)
                raise HTTPException(413, "file too large")
            f.write(chunk)

    job.input_size_bytes = size
    session.add(JobEvent(job_id=job.id, phase="validating", progress_pct=0, message="Upload recebido"))
    await session.commit()

    return JobCreated(id=job.id)


@router.get("", response_model=list[JobRead])
async def list_jobs(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> list[JobRead]:
    rows = (await session.exec(
        select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc()).limit(100)
    )).all()
    return [JobRead.model_validate(r.model_dump()) for r in rows]


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> JobRead:
    job = (await session.exec(
        select(Job).where(Job.id == job_id, Job.user_id == user.id)
    )).first()
    if not job:
        raise HTTPException(404, "job not found")
    return JobRead.model_validate(job.model_dump())


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> None:
    job = (await session.exec(
        select(Job).where(Job.id == job_id, Job.user_id == user.id)
    )).first()
    if not job:
        return
    # arquivos físicos
    up = upload_path(job.id, job.input_filename)
    if up.exists():
        up.unlink()
    if job.folder_name:
        from shutil import rmtree
        target = settings.analyses_path / job.folder_name
        if target.exists():
            rmtree(target)
    await session.delete(job)
    await session.commit()
