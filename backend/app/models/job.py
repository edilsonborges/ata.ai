from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    status: str = Field(default="queued")  # queued|running|done|error|canceled
    phase: str = Field(default="validating")
    progress_pct: int = Field(default=0)
    eta_seconds: int | None = None
    input_filename: str
    input_size_bytes: int
    media_duration_s: int | None = None
    whisper_model: str
    llm_provider: str
    llm_model: str
    folder_name: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobEvent(SQLModel, table=True):
    __tablename__ = "job_events"

    id: int | None = Field(default=None, primary_key=True)
    job_id: UUID = Field(foreign_key="jobs.id", index=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    phase: str
    progress_pct: int
    message: str
    level: str = Field(default="info")  # info|warn|error
