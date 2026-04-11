from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_access_ttl_seconds: int = 900
    jwt_refresh_ttl_seconds: int = 2592000
    fernet_key: str
    admin_email: str
    admin_password: str
    max_upload_mb: int = 500
    storage_dir: str = "/app/storage"

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_dir)

    @property
    def uploads_path(self) -> Path:
        return self.storage_path / "uploads"

    @property
    def analyses_path(self) -> Path:
        return self.storage_path / "analyses"


@lru_cache
def get_settings() -> Settings:
    return Settings()
