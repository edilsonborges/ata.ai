from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class ProviderCredential(SQLModel, table=True):
    __tablename__ = "provider_credentials"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    provider: str  # 'anthropic' | 'openai' | 'openrouter' | 'claude_cli'
    api_key_encrypted: bytes | None = None
    default_model: str
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
