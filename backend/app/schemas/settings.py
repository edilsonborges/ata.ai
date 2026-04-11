from uuid import UUID
from pydantic import BaseModel, Field


VALID_PROVIDERS = ("anthropic", "openai", "openrouter", "claude_cli")


class ProviderCredentialRead(BaseModel):
    id: UUID
    provider: str
    default_model: str
    enabled: bool
    has_api_key: bool


class ProviderCredentialUpsert(BaseModel):
    api_key: str | None = Field(default=None, description="Omit to keep existing")
    default_model: str
    enabled: bool
