from typing import Annotated
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.db import session_dependency
from app.models import User
from app.security import decode_token


async def current_user(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(session_dependency),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        sub = decode_token(token, "access")
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")
    user = (await session.exec(select(User).where(User.id == UUID(sub)))).first()
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return user
