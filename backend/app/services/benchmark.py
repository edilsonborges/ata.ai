import socket
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import WhisperBenchmark


DEFAULT_FACTORS: dict[str, float] = {
    "tiny": 0.08,
    "base": 0.15,
    "small": 0.30,
    "medium": 0.60,
    "large-v3": 1.20,
}

SUPPORTED_MODELS = list(DEFAULT_FACTORS.keys())


async def estimate_seconds(session: AsyncSession, model: str, audio_duration_s: int) -> int:
    if model not in DEFAULT_FACTORS:
        raise ValueError(f"unknown model {model}")
    host = socket.gethostname()
    result = await session.exec(text("""
        SELECT avg(wall_time_s::float / NULLIF(audio_duration_s, 0))
        FROM (
            SELECT wall_time_s, audio_duration_s
            FROM whisper_benchmarks
            WHERE whisper_model = :m AND hostname = :h
            ORDER BY created_at DESC
            LIMIT 10
        ) t
    """).bindparams(m=model, h=host))
    avg = result.scalar()
    factor = float(avg) if avg is not None else DEFAULT_FACTORS[model]
    return max(1, int(audio_duration_s * factor))


async def record(session: AsyncSession, model: str, audio_duration_s: int, wall_time_s: int) -> None:
    session.add(WhisperBenchmark(
        whisper_model=model,
        audio_duration_s=audio_duration_s,
        wall_time_s=wall_time_s,
        hostname=socket.gethostname(),
    ))
    await session.commit()
