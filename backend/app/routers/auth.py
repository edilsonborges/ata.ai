from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from uuid import UUID
from app.db import session_dependency
from app.deps import current_user
from app.models import User
from app.schemas.auth import LoginRequest, Me, RefreshRequest, TokenPair
from app.security import create_token, decode_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(session_dependency),
) -> TokenPair:
    user = (await session.exec(select(User).where(User.email == body.email))).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return TokenPair(
        access_token=create_token(str(user.id), "access"),
        refresh_token=create_token(str(user.id), "refresh"),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(session_dependency),
) -> TokenPair:
    try:
        sub = decode_token(body.refresh_token, "refresh")
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token")
    user = (await session.exec(select(User).where(User.id == UUID(sub)))).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return TokenPair(
        access_token=create_token(str(user.id), "access"),
        refresh_token=create_token(str(user.id), "refresh"),
    )


@router.get("/me", response_model=Me)
async def me(user: User = Depends(current_user)) -> Me:
    return Me(id=user.id, email=user.email, role=user.role)
