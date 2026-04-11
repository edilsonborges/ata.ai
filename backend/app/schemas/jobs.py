from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class JobRead(BaseModel):
    id: UUID
    status: str
    phase: str
    progress_pct: int
    eta_seconds: int | None
    input_filename: str
    input_size_bytes: int
    media_duration_s: int | None
    whisper_model: str
    llm_provider: str
    llm_model: str
    folder_name: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JobCreated(BaseModel):
    id: UUID
