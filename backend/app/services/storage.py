import re
from datetime import datetime
from pathlib import Path
from unicodedata import normalize
from uuid import UUID
from app.config import get_settings


_settings = get_settings()

VIDEO_EXTS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}
SUPPORTED = VIDEO_EXTS | AUDIO_EXTS


def is_supported(filename: str) -> bool:
    return Path(filename).suffix.lower() in SUPPORTED


def is_video(filename: str) -> bool:
    return Path(filename).suffix.lower() in VIDEO_EXTS


def upload_path(job_id: UUID, filename: str) -> Path:
    _settings.uploads_path.mkdir(parents=True, exist_ok=True)
    safe = Path(filename).name
    return _settings.uploads_path / f"{job_id}_{safe}"


def analysis_folder(when: datetime, slug: str) -> Path:
    name = f"analise_{when:%d-%m-%Y}_{when:%H-%M-%S}_{slug}"
    p = _settings.analyses_path / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def slugify(text: str, max_words: int = 5) -> str:
    ascii_text = normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9\s-]", "", ascii_text)
    words = [w for w in ascii_text.split() if w][:max_words]
    return "-".join(words) or "reuniao"
