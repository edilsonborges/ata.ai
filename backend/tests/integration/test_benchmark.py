import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from app import models  # noqa
from app.config import get_settings
from app.services.benchmark import estimate_seconds, record, DEFAULT_FACTORS


@pytest.mark.asyncio
async def test_estimate_with_no_history_uses_default(client):
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    Sess = async_sessionmaker(engine, expire_on_commit=False)
    async with Sess() as s:
        eta = await estimate_seconds(s, "medium", 600)
    assert eta == int(600 * DEFAULT_FACTORS["medium"])


@pytest.mark.asyncio
async def test_record_then_estimate(client):
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    Sess = async_sessionmaker(engine, expire_on_commit=False)
    async with Sess() as s:
        # dois benchmarks reais muito mais rápidos que o default
        await record(s, "medium", 600, 60)
        await record(s, "medium", 600, 60)
        eta = await estimate_seconds(s, "medium", 600)
    assert eta < int(600 * DEFAULT_FACTORS["medium"])
