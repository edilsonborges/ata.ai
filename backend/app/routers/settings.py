from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.db import session_dependency
from app.deps import current_user
from app.models import ProviderCredential, User
from app.schemas.settings import (
    ProviderCredentialRead, ProviderCredentialUpsert, VALID_PROVIDERS,
)
from app.security import encrypt_secret

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _to_read(c: ProviderCredential) -> ProviderCredentialRead:
    return ProviderCredentialRead(
        id=c.id,
        provider=c.provider,
        default_model=c.default_model,
        enabled=c.enabled,
        has_api_key=c.api_key_encrypted is not None,
    )


@router.get("/providers", response_model=list[ProviderCredentialRead])
async def list_providers(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> list[ProviderCredentialRead]:
    rows = (await session.exec(
        select(ProviderCredential).where(ProviderCredential.user_id == user.id)
    )).all()
    return [_to_read(r) for r in rows]


@router.put("/providers/{provider}", response_model=ProviderCredentialRead)
async def upsert_provider(
    provider: str,
    body: ProviderCredentialUpsert,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> ProviderCredentialRead:
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown provider")

    row = (await session.exec(
        select(ProviderCredential).where(
            ProviderCredential.user_id == user.id,
            ProviderCredential.provider == provider,
        )
    )).first()

    if row is None:
        row = ProviderCredential(
            user_id=user.id,
            provider=provider,
            default_model=body.default_model,
            enabled=body.enabled,
        )
        session.add(row)

    row.default_model = body.default_model
    row.enabled = body.enabled
    if body.api_key is not None and provider != "claude_cli":
        row.api_key_encrypted = encrypt_secret(body.api_key)

    await session.commit()
    await session.refresh(row)
    return _to_read(row)


@router.delete("/providers/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> None:
    row = (await session.exec(
        select(ProviderCredential).where(
            ProviderCredential.user_id == user.id,
            ProviderCredential.provider == provider,
        )
    )).first()
    if row:
        await session.delete(row)
        await session.commit()
