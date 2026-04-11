import asyncio
from logging.config import fileConfig
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from sqlmodel import SQLModel

from app.config import get_settings
from app import models  # noqa: F401  registra tabelas

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_online() -> None:
    settings = get_settings()
    connectable = create_async_engine(settings.database_url, future=True)

    async def run() -> None:
        async with connectable.connect() as conn:
            await conn.run_sync(do_run_migrations)
        await connectable.dispose()

    asyncio.run(run())


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


run_migrations_online()
