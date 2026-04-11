import asyncio
import time
from datetime import datetime
from pathlib import Path
from shutil import copy2
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import get_settings
from app.db import get_session
from app.models import Job, JobEvent, ProviderCredential
from app.security import decrypt_secret
from app.services.analysis import get_provider
from app.services.benchmark import record as record_benchmark
from app.services.ffprobe import get_duration_seconds
from app.services.renderer.dashboard import render_dashboard
from app.services.renderer.markdown import render_markdown
from app.services.storage import analysis_folder, is_video


settings = get_settings()


async def _emit(session: AsyncSession, job_id: UUID, phase: str, pct: int, msg: str, level: str = "info") -> None:
    session.add(JobEvent(job_id=job_id, phase=phase, progress_pct=pct, message=msg, level=level))
    await session.commit()


async def _update_job(session: AsyncSession, job: Job, **fields) -> None:
    for k, v in fields.items():
        setattr(job, k, v)
    session.add(job)
    await session.commit()


async def process_job(ctx, job_id_str: str) -> None:
    job_id = UUID(job_id_str)
    async with get_session() as session:
        job = (await session.exec(select(Job).where(Job.id == job_id))).first()
        if not job:
            return

        await _update_job(session, job, status="running", phase="validating",
                          progress_pct=1, started_at=datetime.utcnow())
        await _emit(session, job_id, "validating", 5, "Validando arquivo")

        try:
            upload = settings.uploads_path / f"{job_id}_{job.input_filename}"
            if not upload.exists():
                raise FileNotFoundError(f"upload missing: {upload}")

            duration_s = await get_duration_seconds(upload)
            await _update_job(session, job, media_duration_s=duration_s, phase="extracting_audio", progress_pct=10)
            await _emit(session, job_id, "extracting_audio", 10, f"Duracao detectada: {duration_s}s")

            wav_path = Path(f"/tmp/{job_id}_audio.wav")
            if is_video(job.input_filename):
                await _run_ffmpeg(upload, wav_path)
                await _emit(session, job_id, "extracting_audio", 15, "Audio extraido")
            else:
                copy2(upload, wav_path)
                await _emit(session, job_id, "extracting_audio", 15, "Audio copiado")

            await _update_job(session, job, phase="transcribing", progress_pct=20)
            await _emit(session, job_id, "transcribing", 20, f"Carregando modelo {job.whisper_model}")

            whisper_started = time.time()
            result = await asyncio.to_thread(_run_whisper, job.whisper_model, wav_path, job_id)
            wall = int(time.time() - whisper_started)

            await record_benchmark(session, job.whisper_model, duration_s, wall)
            await _emit(session, job_id, "transcribing", 70, f"Transcricao concluida em {wall}s")

            await _update_job(session, job, phase="analyzing", progress_pct=72)
            await _emit(session, job_id, "analyzing", 75, f"Analise com {job.llm_provider}")

            cred = (await session.exec(
                select(ProviderCredential).where(
                    ProviderCredential.user_id == job.user_id,
                    ProviderCredential.provider == job.llm_provider,
                )
            )).first()
            api_key = decrypt_secret(cred.api_key_encrypted) if (cred and cred.api_key_encrypted) else None

            provider = get_provider(job.llm_provider)
            analysis = await provider.analyze(
                transcript=result["text"],
                segments_json=_segments_json(result["segments"]),
                model=job.llm_model,
                api_key=api_key,
            )

            await _update_job(session, job, phase="rendering", progress_pct=90)
            await _emit(session, job_id, "rendering", 92, "Gerando artefatos")

            folder = analysis_folder(datetime.utcnow(), analysis.slug)
            folder_name = folder.name

            (folder / "transcricao.vtt").write_bytes(result["vtt_path"].read_bytes())
            (folder / "analise.md").write_text(render_markdown(analysis), encoding="utf-8")
            (folder / "dashboard.html").write_text(render_dashboard(analysis, result["text"]), encoding="utf-8")

            await _update_job(
                session, job, status="done", phase="done",
                progress_pct=100, finished_at=datetime.utcnow(),
                folder_name=folder_name,
            )
            await _emit(session, job_id, "done", 100, "Concluido")

        except Exception as exc:
            await _update_job(
                session, job, status="error", error_message=str(exc)[:2000],
                finished_at=datetime.utcnow(),
            )
            await _emit(session, job_id, job.phase, job.progress_pct, f"Erro: {exc}", level="error")
            raise


async def _run_ffmpeg(src: Path, dst: Path) -> None:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(src),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(dst),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()[:500]}")


def _run_whisper(model_name: str, audio_path: Path, job_id: UUID) -> dict:
    from app.services.whisper_runner import WhisperRunner
    out_dir = Path(f"/tmp/{job_id}_whisper")
    runner = WhisperRunner(model_name)
    return runner.transcribe(audio_path, out_dir)


def _segments_json(segments: list[dict]) -> str:
    import json
    return json.dumps(segments, ensure_ascii=False)
