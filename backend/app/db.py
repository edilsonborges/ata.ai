from contextlib import asynccontextmanager
from typing import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def session_dependency() -> AsyncIterator[AsyncSession]:
    async with get_session() as session:
        yield session
