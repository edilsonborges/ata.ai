from datetime import datetime
from sqlmodel import Field, SQLModel


class WhisperBenchmark(SQLModel, table=True):
    __tablename__ = "whisper_benchmarks"

    id: int | None = Field(default=None, primary_key=True)
    whisper_model: str = Field(index=True)
    audio_duration_s: int
    wall_time_s: int
    hostname: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
