# Sistema Web ata.ai — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir uma aplicação web full-stack que executa o mesmo pipeline do slash command `/analisar-reuniao` via upload, fila assíncrona com progresso em tempo real, múltiplos provedores LLM e histórico persistente.

**Architecture:** Monorepo com `backend/` (FastAPI + arq worker + Postgres) e `frontend/` (Next.js + Tailwind). 4 serviços Docker: `postgres`, `api`, `worker`, `web`. Progresso em tempo real via Server-Sent Events alimentados por `LISTEN/NOTIFY` do Postgres. 4 provedores LLM: Anthropic API, OpenAI, OpenRouter e Claude Code CLI local (via volume mount de `~/.claude`).

**Tech Stack:** Python 3.12, FastAPI, SQLModel, Alembic, `arq`, `openai-whisper`, Anthropic/OpenAI SDKs, Next.js 14 (App Router), TypeScript, Tailwind, shadcn/ui, Docker Compose, PostgreSQL 16.

**Spec:** [`docs/superpowers/specs/2026-04-11-sistema-web-ata-ai-design.md`](../specs/2026-04-11-sistema-web-ata-ai-design.md) — leia antes de executar qualquer tarefa.

---

## Fase 0 — Scaffold do monorepo

### Task 0.1: Estrutura de diretórios + .gitignore

**Files:**
- Create: `backend/` `frontend/` `storage/uploads/.gitkeep` `storage/analyses/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1: Criar diretórios base**

```bash
mkdir -p backend/app/{models,schemas,routers,services/analysis,services/renderer,workers}
mkdir -p backend/tests/{unit,integration}
mkdir -p backend/migrations/versions
mkdir -p frontend/src/{app,components,lib}
mkdir -p frontend/src/app/\(auth\)/login
mkdir -p frontend/src/app/\(app\)/{upload,settings}
mkdir -p "frontend/src/app/(app)/jobs/[id]"
mkdir -p storage/uploads storage/analyses
touch storage/uploads/.gitkeep storage/analyses/.gitkeep
```

- [ ] **Step 2: Atualizar `.gitignore`**

```
# Storage runtime
storage/uploads/*
storage/analyses/*
!storage/uploads/.gitkeep
!storage/analyses/.gitkeep

# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/
.mypy_cache/
*.egg-info/

# Node
node_modules/
.next/
out/

# Env
.env
.env.local
.env.*.local

# Tools
.playwright-mcp/
*.png
!docs/**/*.png
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore backend frontend storage
git commit -m "chore: scaffold monorepo structure (backend/frontend/storage)"
```

---

### Task 0.2: `docker-compose.yml` skeleton + `.env.example`

**Files:**
- Create: `docker-compose.yml`, `.env.example`

- [ ] **Step 1: Criar `.env.example`**

```
POSTGRES_DB=ata
POSTGRES_USER=ata
POSTGRES_PASSWORD=change-me-in-production

JWT_SECRET=generate-with-openssl-rand-hex-32
JWT_ACCESS_TTL_SECONDS=900
JWT_REFRESH_TTL_SECONDS=2592000

# Gere com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY=

ADMIN_EMAIL=admin@edilson.dev
ADMIN_PASSWORD=ksjao10so!

MAX_UPLOAD_MB=500
STORAGE_DIR=/app/storage
```

- [ ] **Step 2: Criar `docker-compose.yml` (os serviços `api`/`worker`/`web` apontam para Dockerfiles que serão criados em tasks futuras)**

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 3s
      retries: 10
    ports: ["5432:5432"]

  api:
    build:
      context: ./backend
    command: >
      sh -c "alembic upgrade head &&
             python -m app.seed &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres/${POSTGRES_DB}
      JWT_SECRET: ${JWT_SECRET}
      JWT_ACCESS_TTL_SECONDS: ${JWT_ACCESS_TTL_SECONDS}
      JWT_REFRESH_TTL_SECONDS: ${JWT_REFRESH_TTL_SECONDS}
      FERNET_KEY: ${FERNET_KEY}
      ADMIN_EMAIL: ${ADMIN_EMAIL}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
      MAX_UPLOAD_MB: ${MAX_UPLOAD_MB}
      STORAGE_DIR: ${STORAGE_DIR}
    volumes:
      - ./storage:/app/storage
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
    ports: ["8000:8000"]

  worker:
    build:
      context: ./backend
    command: python -m app.workers.main
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres/${POSTGRES_DB}
      FERNET_KEY: ${FERNET_KEY}
      STORAGE_DIR: ${STORAGE_DIR}
    volumes:
      - ./storage:/app/storage
      - ./backend:/app
      - ${HOME}/.claude:/root/.claude:ro
      - ${HOME}/.claude.json:/root/.claude.json:ro
    depends_on:
      postgres:
        condition: service_healthy

  web:
    build:
      context: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    ports: ["3000:3000"]
    depends_on: [api]

volumes:
  pg_data:
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "chore: docker-compose skeleton with 4 services + env template"
```

---

## Fase 1 — Backend foundation

### Task 1.1: `pyproject.toml` + `Dockerfile` do backend

**Files:**
- Create: `backend/pyproject.toml`, `backend/Dockerfile`, `backend/.dockerignore`

- [ ] **Step 1: `backend/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "ata-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.111",
  "uvicorn[standard]>=0.30",
  "sqlmodel>=0.0.22",
  "asyncpg>=0.29",
  "psycopg[binary]>=3.2",
  "alembic>=1.13",
  "pydantic-settings>=2.3",
  "python-jose[cryptography]>=3.3",
  "passlib[bcrypt]>=1.7",
  "python-multipart>=0.0.9",
  "cryptography>=42",
  "arq>=0.26",
  "openai-whisper==20240930",
  "torch>=2.2",
  "anthropic>=0.34",
  "openai>=1.40",
  "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
  "pytest>=8",
  "pytest-asyncio>=0.23",
  "pytest-httpx>=0.30",
  "mypy>=1.10",
  "ruff>=0.6",
]

[tool.setuptools.packages.find]
include = ["app*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg curl ca-certificates gnupg git \
    && rm -rf /var/lib/apt/lists/*

# Node + Claude Code CLI (usado apenas pelo worker)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g @anthropic-ai/claude-code

WORKDIR /app
COPY pyproject.toml ./
RUN pip install -e .[dev]

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: `backend/.dockerignore`**

```
__pycache__
*.pyc
.venv
.pytest_cache
.mypy_cache
tests/fixtures/*.mp4
tests/fixtures/*.wav
```

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml backend/Dockerfile backend/.dockerignore
git commit -m "backend: pyproject + Dockerfile with ffmpeg and claude-code CLI"
```

---

### Task 1.2: Config (`config.py`) + DB engine (`db.py`) + security primitives (`security.py`)

**Files:**
- Create: `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/security.py`

- [ ] **Step 1: `backend/app/__init__.py`**

```python
```

- [ ] **Step 2: `backend/app/config.py`**

```python
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
```

- [ ] **Step 3: `backend/app/db.py`**

```python
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
```

- [ ] **Step 4: `backend/app/security.py`**

```python
from datetime import datetime, timedelta, timezone
from typing import Literal
from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import get_settings

settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_fernet = Fernet(settings.fernet_key.encode())

TokenType = Literal["access", "refresh"]


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_token(subject: str, token_type: TokenType) -> str:
    ttl = (
        settings.jwt_access_ttl_seconds
        if token_type == "access"
        else settings.jwt_refresh_ttl_seconds
    )
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str, expected_type: TokenType) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
    if payload.get("type") != expected_type:
        raise ValueError(f"wrong token type, expected {expected_type}")
    return payload["sub"]


def encrypt_secret(plaintext: str) -> bytes:
    return _fernet.encrypt(plaintext.encode())


def decrypt_secret(ciphertext: bytes) -> str:
    return _fernet.decrypt(ciphertext).decode()
```

- [ ] **Step 5: Teste unitário de security**

Create `backend/tests/unit/test_security.py`:

```python
import pytest
from app.security import (
    create_token, decode_token, encrypt_secret, decrypt_secret,
    hash_password, verify_password,
)


def test_password_roundtrip():
    h = hash_password("ksjao10so!")
    assert verify_password("ksjao10so!", h)
    assert not verify_password("wrong", h)


def test_token_roundtrip_access():
    tok = create_token("user-123", "access")
    assert decode_token(tok, "access") == "user-123"


def test_token_type_mismatch_raises():
    tok = create_token("user-123", "access")
    with pytest.raises(ValueError):
        decode_token(tok, "refresh")


def test_fernet_roundtrip():
    ct = encrypt_secret("sk-ant-xyz")
    assert decrypt_secret(ct) == "sk-ant-xyz"
```

- [ ] **Step 6: Rodar testes**

```bash
cd backend && pytest tests/unit/test_security.py -v
```

Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/__init__.py backend/app/config.py backend/app/db.py backend/app/security.py backend/tests
git commit -m "backend: config, db engine, security primitives (JWT/bcrypt/Fernet) + tests"
```

---

## Fase 2 — Models, migrations, seed

### Task 2.1: SQLModel models

**Files:**
- Create: `backend/app/models/__init__.py`, `backend/app/models/user.py`, `backend/app/models/provider_credential.py`, `backend/app/models/job.py`, `backend/app/models/whisper_benchmark.py`

- [ ] **Step 1: `backend/app/models/__init__.py`**

```python
from app.models.user import User
from app.models.provider_credential import ProviderCredential
from app.models.job import Job, JobEvent
from app.models.whisper_benchmark import WhisperBenchmark

__all__ = ["User", "ProviderCredential", "Job", "JobEvent", "WhisperBenchmark"]
```

- [ ] **Step 2: `backend/app/models/user.py`**

```python
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    role: str = Field(default="member")
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 3: `backend/app/models/provider_credential.py`**

```python
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
```

- [ ] **Step 4: `backend/app/models/job.py`**

```python
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    status: str = Field(default="queued")  # queued|running|done|error|canceled
    phase: str = Field(default="validating")
    progress_pct: int = Field(default=0)
    eta_seconds: int | None = None
    input_filename: str
    input_size_bytes: int
    media_duration_s: int | None = None
    whisper_model: str
    llm_provider: str
    llm_model: str
    folder_name: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobEvent(SQLModel, table=True):
    __tablename__ = "job_events"

    id: int | None = Field(default=None, primary_key=True)
    job_id: UUID = Field(foreign_key="jobs.id", index=True)
    ts: datetime = Field(default_factory=datetime.utcnow)
    phase: str
    progress_pct: int
    message: str
    level: str = Field(default="info")  # info|warn|error
```

- [ ] **Step 5: `backend/app/models/whisper_benchmark.py`**

```python
from datetime import datetime
from sqlmodel import Field, SQLModel


class WhisperBenchmark(SQLModel, table=True):
    __tablename__ = "whisper_benchmarks"

    id: int | None = Field(default=None, primary_key=True)
    whisper_model: str = Field(index=True)
    audio_duration_s: int
    wall_time_s: int
    hostname: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/models
git commit -m "backend: SQLModel entities (User, ProviderCredential, Job, JobEvent, WhisperBenchmark)"
```

---

### Task 2.2: Alembic setup + migração inicial com trigger NOTIFY

**Files:**
- Create: `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/script.py.mako`, `backend/migrations/versions/0001_initial.py`

- [ ] **Step 1: `backend/alembic.ini`**

```ini
[alembic]
script_location = migrations
sqlalchemy.url = driver://user:pass@host/db
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 2: `backend/migrations/env.py`**

```python
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
```

- [ ] **Step 3: `backend/migrations/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 4: `backend/migrations/versions/0001_initial.py`**

```python
"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-11
"""
from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "provider_credentials",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("api_key_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("default_model", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )
    op.create_index("ix_provider_credentials_user_id", "provider_credentials", ["user_id"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("phase", sa.String(), nullable=False, server_default="validating"),
        sa.Column("progress_pct", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("eta_seconds", sa.Integer(), nullable=True),
        sa.Column("input_filename", sa.String(), nullable=False),
        sa.Column("input_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("media_duration_s", sa.Integer(), nullable=True),
        sa.Column("whisper_model", sa.String(), nullable=False),
        sa.Column("llm_provider", sa.String(), nullable=False),
        sa.Column("llm_model", sa.String(), nullable=False),
        sa.Column("folder_name", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_jobs_user_id_created_at", "jobs", ["user_id", "created_at"])

    op.create_table(
        "job_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("phase", sa.String(), nullable=False),
        sa.Column("progress_pct", sa.SmallInteger(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("level", sa.String(), nullable=False, server_default="info"),
    )
    op.create_index("ix_job_events_job_id", "job_events", ["job_id", "id"])

    op.create_table(
        "whisper_benchmarks",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("whisper_model", sa.String(), nullable=False),
        sa.Column("audio_duration_s", sa.Integer(), nullable=False),
        sa.Column("wall_time_s", sa.Integer(), nullable=False),
        sa.Column("hostname", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_whisper_benchmarks_model_date", "whisper_benchmarks", ["whisper_model", "created_at"])

    # Trigger NOTIFY ao inserir job_event
    op.execute("""
    CREATE OR REPLACE FUNCTION notify_job_event() RETURNS trigger AS $$
    DECLARE
        payload json;
    BEGIN
        payload := json_build_object(
            'job_id', NEW.job_id,
            'phase', NEW.phase,
            'progress_pct', NEW.progress_pct,
            'message', NEW.message,
            'level', NEW.level,
            'ts', extract(epoch from NEW.ts)
        );
        PERFORM pg_notify('job_event', payload::text);
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER trg_job_event_notify
    AFTER INSERT ON job_events
    FOR EACH ROW EXECUTE FUNCTION notify_job_event();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_job_event_notify ON job_events;")
    op.execute("DROP FUNCTION IF EXISTS notify_job_event();")
    op.drop_index("ix_whisper_benchmarks_model_date", "whisper_benchmarks")
    op.drop_table("whisper_benchmarks")
    op.drop_index("ix_job_events_job_id", "job_events")
    op.drop_table("job_events")
    op.drop_index("ix_jobs_user_id_created_at", "jobs")
    op.drop_table("jobs")
    op.drop_index("ix_provider_credentials_user_id", "provider_credentials")
    op.drop_table("provider_credentials")
    op.drop_table("users")
```

- [ ] **Step 5: Commit**

```bash
git add backend/alembic.ini backend/migrations
git commit -m "backend: alembic initial migration with NOTIFY trigger on job_events"
```

---

### Task 2.3: Admin seed

**Files:**
- Create: `backend/app/seed.py`

- [ ] **Step 1: `backend/app/seed.py`**

```python
import asyncio
from sqlmodel import select
from app.config import get_settings
from app.db import get_session
from app.models import User, ProviderCredential
from app.security import hash_password


DEFAULT_PROVIDERS = [
    ("anthropic", "claude-opus-4-6"),
    ("openai", "gpt-4o"),
    ("openrouter", "anthropic/claude-3.5-sonnet"),
    ("claude_cli", "claude-opus-4-6"),
]


async def run() -> None:
    settings = get_settings()
    async with get_session() as s:
        result = await s.exec(select(User).where(User.email == settings.admin_email))
        if result.first():
            print(f"admin {settings.admin_email} already exists")
            return

        admin = User(
            email=settings.admin_email,
            password_hash=hash_password(settings.admin_password),
            role="admin",
        )
        s.add(admin)
        await s.flush()

        for provider, default_model in DEFAULT_PROVIDERS:
            s.add(ProviderCredential(
                user_id=admin.id,
                provider=provider,
                default_model=default_model,
                enabled=False,
            ))

        await s.commit()
        print(f"seeded admin {settings.admin_email}")


if __name__ == "__main__":
    asyncio.run(run())
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/seed.py
git commit -m "backend: admin seed with disabled provider credentials"
```

---

## Fase 3 — Auth + Settings APIs

### Task 3.1: Auth schemas + router

**Files:**
- Create: `backend/app/schemas/__init__.py`, `backend/app/schemas/auth.py`, `backend/app/routers/__init__.py`, `backend/app/routers/auth.py`, `backend/app/deps.py`

- [ ] **Step 1: `backend/app/schemas/__init__.py`** (vazio)

```python
```

- [ ] **Step 2: `backend/app/schemas/auth.py`**

```python
from uuid import UUID
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class Me(BaseModel):
    id: UUID
    email: EmailStr
    role: str
```

- [ ] **Step 3: `backend/app/deps.py`**

```python
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
```

- [ ] **Step 4: `backend/app/routers/__init__.py`** (vazio)

```python
```

- [ ] **Step 5: `backend/app/routers/auth.py`**

```python
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
```

- [ ] **Step 6: Teste de integração (precisa do compose rodando ou de um postgres de teste). Criar fixture.**

Create `backend/tests/integration/conftest.py`:

```python
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from app import models  # noqa
from app.config import get_settings
from app.main import create_app


@pytest_asyncio.fixture
async def client():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    await engine.dispose()

    from app.seed import run as seed
    await seed()

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
```

Create `backend/tests/integration/test_auth.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_login_ok(client):
    r = await client.post("/api/auth/login", json={
        "email": "admin@edilson.dev",
        "password": "ksjao10so!",
    })
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body and "refresh_token" in body


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    r = await client.post("/api/auth/login", json={
        "email": "admin@edilson.dev",
        "password": "nope",
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_bearer(client):
    login = (await client.post("/api/auth/login", json={
        "email": "admin@edilson.dev", "password": "ksjao10so!",
    })).json()
    r = await client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {login['access_token']}"
    })
    assert r.status_code == 200
    assert r.json()["email"] == "admin@edilson.dev"
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/deps.py backend/app/schemas backend/app/routers backend/tests/integration
git commit -m "backend: auth router (login/refresh/me) with JWT + integration tests"
```

---

### Task 3.2: Settings router (provider credentials CRUD)

**Files:**
- Create: `backend/app/schemas/settings.py`, `backend/app/routers/settings.py`

- [ ] **Step 1: `backend/app/schemas/settings.py`**

```python
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
```

- [ ] **Step 2: `backend/app/routers/settings.py`**

```python
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
```

- [ ] **Step 3: Teste de integração**

Create `backend/tests/integration/test_settings.py`:

```python
import pytest


async def _token(client) -> str:
    r = await client.post("/api/auth/login", json={
        "email": "admin@edilson.dev", "password": "ksjao10so!",
    })
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_list_providers_seeded(client):
    t = await _token(client)
    r = await client.get("/api/settings/providers", headers={"Authorization": f"Bearer {t}"})
    assert r.status_code == 200
    providers = {p["provider"] for p in r.json()}
    assert providers == {"anthropic", "openai", "openrouter", "claude_cli"}


@pytest.mark.asyncio
async def test_upsert_anthropic_api_key(client):
    t = await _token(client)
    r = await client.put(
        "/api/settings/providers/anthropic",
        headers={"Authorization": f"Bearer {t}"},
        json={"api_key": "sk-ant-test", "default_model": "claude-opus-4-6", "enabled": True},
    )
    assert r.status_code == 200
    assert r.json()["has_api_key"] is True
    assert r.json()["enabled"] is True
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/settings.py backend/app/routers/settings.py backend/tests/integration/test_settings.py
git commit -m "backend: settings router (provider credentials CRUD) + tests"
```

---

## Fase 4 — Services: storage, ffprobe, whisper runner, benchmark

### Task 4.1: `storage.py` + `ffprobe.py`

**Files:**
- Create: `backend/app/services/__init__.py`, `backend/app/services/storage.py`, `backend/app/services/ffprobe.py`

- [ ] **Step 1: `backend/app/services/__init__.py`** (vazio)

```python
```

- [ ] **Step 2: `backend/app/services/storage.py`**

```python
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
```

- [ ] **Step 3: `backend/app/services/ffprobe.py`**

```python
import asyncio
import json
from pathlib import Path


async def get_duration_seconds(path: Path) -> int:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {stderr.decode()}")
    data = json.loads(stdout)
    return int(float(data["format"]["duration"]))
```

- [ ] **Step 4: Teste unitário de slugify**

Create `backend/tests/unit/test_storage.py`:

```python
from app.services.storage import slugify, is_supported, is_video


def test_slugify_removes_accents_and_limits_words():
    assert slugify("Revisão de Arquitetura da API Nova v2") == "revisao-de-arquitetura-da-api"


def test_slugify_empty_fallback():
    assert slugify("") == "reuniao"


def test_is_supported():
    assert is_supported("foo.mp4")
    assert is_supported("foo.WAV")
    assert not is_supported("foo.txt")


def test_is_video():
    assert is_video("x.mp4")
    assert not is_video("x.wav")
```

- [ ] **Step 5: Rodar**

```bash
cd backend && pytest tests/unit/test_storage.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/storage.py backend/app/services/ffprobe.py backend/tests/unit/test_storage.py
git commit -m "backend: storage paths/slug + ffprobe duration wrapper"
```

---

### Task 4.2: `benchmark.py` + `whisper_runner.py`

**Files:**
- Create: `backend/app/services/benchmark.py`, `backend/app/services/whisper_runner.py`

- [ ] **Step 1: `backend/app/services/benchmark.py`**

```python
import socket
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import WhisperBenchmark


DEFAULT_FACTORS: dict[str, float] = {
    "tiny": 0.08,
    "base": 0.15,
    "small": 0.30,
    "medium": 0.60,
    "large-v3": 1.20,
}

SUPPORTED_MODELS = list(DEFAULT_FACTORS.keys())


async def estimate_seconds(session: AsyncSession, model: str, audio_duration_s: int) -> int:
    if model not in DEFAULT_FACTORS:
        raise ValueError(f"unknown model {model}")
    host = socket.gethostname()
    result = await session.exec(text("""
        SELECT avg(wall_time_s::float / NULLIF(audio_duration_s, 0))
        FROM (
            SELECT wall_time_s, audio_duration_s
            FROM whisper_benchmarks
            WHERE whisper_model = :m AND hostname = :h
            ORDER BY created_at DESC
            LIMIT 10
        ) t
    """).bindparams(m=model, h=host))
    avg = result.scalar()
    factor = float(avg) if avg is not None else DEFAULT_FACTORS[model]
    return max(1, int(audio_duration_s * factor))


async def record(session: AsyncSession, model: str, audio_duration_s: int, wall_time_s: int) -> None:
    session.add(WhisperBenchmark(
        whisper_model=model,
        audio_duration_s=audio_duration_s,
        wall_time_s=wall_time_s,
        hostname=socket.gethostname(),
    ))
    await session.commit()
```

- [ ] **Step 2: `backend/app/services/whisper_runner.py`**

```python
import json
import time
from pathlib import Path
from typing import Callable


class WhisperRunner:
    """Wrapper síncrono ao redor de `openai-whisper`. Deve ser chamado de um executor."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            import whisper
            self._model = whisper.load_model(self.model_name)
        return self._model

    def transcribe(
        self,
        audio_path: Path,
        output_dir: Path,
        progress_cb: Callable[[float, str], None] | None = None,
    ) -> dict:
        import whisper
        from whisper.utils import get_writer

        model = self._load()
        started = time.time()

        result = model.transcribe(
            str(audio_path), language="pt", verbose=False,
        )

        # Emissão de progresso após cada 10% dos segmentos. O whisper não expõe
        # callback nativo — interpolamos pelo end time do último segmento.
        if progress_cb and result.get("segments"):
            total = result["segments"][-1]["end"] or 1.0
            # callback único com 100% (execução síncrona acabou)
            progress_cb(1.0, f"{len(result['segments'])} segmentos em {int(total)}s de audio")

        output_dir.mkdir(parents=True, exist_ok=True)
        writer = get_writer("vtt", str(output_dir))
        writer(result, "transcricao.wav", {
            "max_line_width": None,
            "max_line_count": None,
            "highlight_words": False,
        })

        (output_dir / "reuniao_transcript.txt").write_text(result["text"], encoding="utf-8")

        segs = [
            {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
            for s in result["segments"]
        ]
        (output_dir / "reuniao_segments.json").write_text(
            json.dumps(segs, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        wall_time = int(time.time() - started)
        return {
            "wall_time_s": wall_time,
            "audio_duration_s": int(result["segments"][-1]["end"]) if result["segments"] else 0,
            "text": result["text"],
            "segments": segs,
            "vtt_path": output_dir / "transcricao.vtt",
        }
```

> **Nota para o executor:** O writer do Whisper gera o `.vtt` com o mesmo basename do input (`transcricao.wav` → `transcricao.vtt`). A função retorna esse path.

- [ ] **Step 3: Teste unitário de benchmark (sem whisper real)**

Create `backend/tests/integration/test_benchmark.py`:

```python
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
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/benchmark.py backend/app/services/whisper_runner.py backend/tests/integration/test_benchmark.py
git commit -m "backend: whisper runner (wrapper) + benchmark ETA calibration"
```

---

### Task 4.3: Whisper router (ETA endpoint)

**Files:**
- Create: `backend/app/routers/whisper.py`

- [ ] **Step 1: `backend/app/routers/whisper.py`**

```python
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import session_dependency
from app.deps import current_user
from app.models import User
from app.services.benchmark import SUPPORTED_MODELS, estimate_seconds

router = APIRouter(prefix="/api/whisper", tags=["whisper"])


class ModelOption(BaseModel):
    name: str
    eta_seconds: int
    is_default: bool


@router.get("/models", response_model=list[ModelOption])
async def list_models(
    duration_s: int = Query(gt=0),
    _: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> list[ModelOption]:
    out: list[ModelOption] = []
    for name in SUPPORTED_MODELS:
        eta = await estimate_seconds(session, name, duration_s)
        out.append(ModelOption(name=name, eta_seconds=eta, is_default=(name == "medium")))
    return out
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/whisper.py
git commit -m "backend: whisper router with per-model ETA endpoint"
```

---

## Fase 5 — Providers de análise

### Task 5.1: Interface + prompts + schema comum

**Files:**
- Create: `backend/app/services/analysis/__init__.py`, `backend/app/services/analysis/base.py`, `backend/app/services/analysis/prompts.py`, `backend/app/services/analysis/schemas.py`

- [ ] **Step 1: `backend/app/services/analysis/__init__.py`** (vazio)

```python
```

- [ ] **Step 2: `backend/app/services/analysis/schemas.py`**

```python
from pydantic import BaseModel, Field


class Participant(BaseModel):
    name: str
    role: str | None = None
    type: str | None = None  # condutor|executor|apoio


class Topic(BaseModel):
    title: str
    summary: str
    relevance_pct: int
    quote: str | None = None
    quote_ts: str | None = None  # [MM:SS]


class Decision(BaseModel):
    text: str
    context: str | None = None
    quote_ts: str | None = None


class Finding(BaseModel):
    text: str
    detail: str | None = None


class Action(BaseModel):
    title: str
    owner: str | None = None
    deadline: str | None = None
    priority: str | None = None  # alta|media|baixa
    status: str | None = None


class Risk(BaseModel):
    text: str
    probability: int = Field(ge=1, le=10)
    impact: int = Field(ge=1, le=10)


class TimelineEvent(BaseModel):
    range: str  # MM:SS – MM:SS
    title: str
    tone: str  # positive|neutral|concern|constructive
    summary: str


class Entity(BaseModel):
    name: str
    kind: str  # pessoa|sistema|orgao|tech|ferramenta


class Keyword(BaseModel):
    word: str
    weight: int


class AnalysisResult(BaseModel):
    slug: str
    title: str
    meeting_date: str | None = None
    duration: str  # MM:SS
    summary: str
    participants: list[Participant] = []
    topics: list[Topic] = []
    decisions: list[Decision] = []
    findings: list[Finding] = []
    actions: list[Action] = []
    risks: list[Risk] = []
    timeline: list[TimelineEvent] = []
    entities: list[Entity] = []
    sentiment: str | None = None
    engagement: str | None = None
    keywords: list[Keyword] = []
    insights: list[str] = []
    flow: list[str] = []
```

- [ ] **Step 3: `backend/app/services/analysis/prompts.py`**

```python
SYSTEM_PROMPT = """Voce e um analisador profissional de reunioes corporativas. A partir de uma transcricao em portugues (PT-BR) sem separacao de locutores, extraia uma analise estruturada e completa.

Regras inegociaveis:
- Nunca inventar dados que nao estejam na transcricao. Se algo nao foi abordado, omitir a secao ou deixar vazio.
- Citar trechos literais entre aspas com timestamp [MM:SS] quando relevante.
- Participantes devem ser inferidos por contexto (Whisper nao separa locutores).
- Slug em kebab-case, lowercase, sem acentos, 3-5 palavras.
- Nunca usar emojis.
- Tudo em portugues brasileiro.

Responda SOMENTE com um JSON valido seguindo o schema fornecido. Sem texto antes ou depois."""


def user_prompt(transcript: str, segments_json: str) -> str:
    return f"""Abaixo esta a transcricao e os segmentos com timestamps da reuniao.

## TRANSCRICAO
{transcript}

## SEGMENTOS (JSON com start/end em segundos)
{segments_json}

Extraia: slug, title, meeting_date, duration (MM:SS), summary (3-5 frases), participants, topics (com relevance_pct), decisions, findings, actions, risks (probability e impact 1-10), timeline (com tone positive|neutral|concern|constructive), entities, sentiment, engagement, keywords (15-25), insights, flow.

Retorne apenas o JSON."""
```

- [ ] **Step 4: `backend/app/services/analysis/base.py`**

```python
from typing import Protocol
from app.services.analysis.schemas import AnalysisResult


class AnalysisProvider(Protocol):
    name: str

    async def analyze(
        self,
        transcript: str,
        segments_json: str,
        model: str,
        api_key: str | None,
    ) -> AnalysisResult: ...
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/analysis
git commit -m "backend: analysis provider interface + prompts + result schema"
```

---

### Task 5.2: Anthropic provider

**Files:**
- Create: `backend/app/services/analysis/anthropic_provider.py`

- [ ] **Step 1: Código**

```python
import json
from anthropic import AsyncAnthropic
from app.services.analysis.base import AnalysisProvider
from app.services.analysis.prompts import SYSTEM_PROMPT, user_prompt
from app.services.analysis.schemas import AnalysisResult


class AnthropicProvider:
    name = "anthropic"

    async def analyze(
        self,
        transcript: str,
        segments_json: str,
        model: str,
        api_key: str | None,
    ) -> AnalysisResult:
        if not api_key:
            raise ValueError("anthropic provider requires api_key")
        client = AsyncAnthropic(api_key=api_key)
        msg = await client.messages.create(
            model=model,
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt(transcript, segments_json)}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        payload = _extract_json(text)
        return AnalysisResult.model_validate(payload)


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON in response: {text[:200]}")
    return json.loads(text[start : end + 1])
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/analysis/anthropic_provider.py
git commit -m "backend: anthropic analysis provider"
```

---

### Task 5.3: OpenAI provider

**Files:**
- Create: `backend/app/services/analysis/openai_provider.py`

- [ ] **Step 1: Código**

```python
from openai import AsyncOpenAI
from app.services.analysis.prompts import SYSTEM_PROMPT, user_prompt
from app.services.analysis.schemas import AnalysisResult


class OpenAIProvider:
    name = "openai"

    async def analyze(
        self,
        transcript: str,
        segments_json: str,
        model: str,
        api_key: str | None,
    ) -> AnalysisResult:
        if not api_key:
            raise ValueError("openai provider requires api_key")
        client = AsyncOpenAI(api_key=api_key)
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt(transcript, segments_json)},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw = resp.choices[0].message.content or "{}"
        return AnalysisResult.model_validate_json(raw)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/analysis/openai_provider.py
git commit -m "backend: openai analysis provider (json_object response format)"
```

---

### Task 5.4: OpenRouter provider

**Files:**
- Create: `backend/app/services/analysis/openrouter_provider.py`

- [ ] **Step 1: Código**

```python
from openai import AsyncOpenAI
from app.services.analysis.prompts import SYSTEM_PROMPT, user_prompt
from app.services.analysis.schemas import AnalysisResult
import json


class OpenRouterProvider:
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"

    async def analyze(
        self,
        transcript: str,
        segments_json: str,
        model: str,
        api_key: str | None,
    ) -> AnalysisResult:
        if not api_key:
            raise ValueError("openrouter provider requires api_key")
        client = AsyncOpenAI(api_key=api_key, base_url=self.base_url)
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt(transcript, segments_json)},
            ],
            temperature=0.2,
        )
        raw = resp.choices[0].message.content or "{}"
        # OpenRouter nao garante JSON puro em todos os modelos; extrair bloco
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"no JSON in openrouter response: {raw[:200]}")
        return AnalysisResult.model_validate(json.loads(raw[start : end + 1]))
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/analysis/openrouter_provider.py
git commit -m "backend: openrouter provider (via openai SDK with custom base_url)"
```

---

### Task 5.5: Claude CLI provider

**Files:**
- Create: `backend/app/services/analysis/claude_cli_provider.py`

- [ ] **Step 1: Código**

```python
import asyncio
import json
from app.services.analysis.prompts import SYSTEM_PROMPT, user_prompt
from app.services.analysis.schemas import AnalysisResult


class ClaudeCliProvider:
    name = "claude_cli"

    async def analyze(
        self,
        transcript: str,
        segments_json: str,
        model: str,
        api_key: str | None,
    ) -> AnalysisResult:
        full_prompt = SYSTEM_PROMPT + "\n\n" + user_prompt(transcript, segments_json)
        proc = await asyncio.create_subprocess_exec(
            "claude", "-p", full_prompt,
            "--model", model,
            "--output-format", "json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"claude cli failed: {stderr.decode()[:500]}")

        envelope = json.loads(stdout)
        # `claude -p --output-format json` devolve {result: "...", ...}
        result_text = envelope.get("result", "")
        start = result_text.find("{")
        end = result_text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"no JSON in claude cli result: {result_text[:200]}")
        return AnalysisResult.model_validate(json.loads(result_text[start : end + 1]))
```

- [ ] **Step 2: Factory para escolher provider**

Create or append to `backend/app/services/analysis/__init__.py`:

```python
from app.services.analysis.anthropic_provider import AnthropicProvider
from app.services.analysis.claude_cli_provider import ClaudeCliProvider
from app.services.analysis.openai_provider import OpenAIProvider
from app.services.analysis.openrouter_provider import OpenRouterProvider
from app.services.analysis.base import AnalysisProvider


_REGISTRY: dict[str, type] = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "openrouter": OpenRouterProvider,
    "claude_cli": ClaudeCliProvider,
}


def get_provider(name: str) -> AnalysisProvider:
    cls = _REGISTRY.get(name)
    if not cls:
        raise ValueError(f"unknown provider {name}")
    return cls()  # type: ignore[return-value]


__all__ = ["get_provider", "AnalysisProvider"]
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/analysis/claude_cli_provider.py backend/app/services/analysis/__init__.py
git commit -m "backend: claude CLI provider via subprocess + provider factory"
```

---

## Fase 6 — Renderers (markdown + dashboard)

### Task 6.1: Markdown renderer

**Files:**
- Create: `backend/app/services/renderer/__init__.py`, `backend/app/services/renderer/markdown.py`

- [ ] **Step 1: `backend/app/services/renderer/__init__.py`** (vazio)

```python
```

- [ ] **Step 2: `backend/app/services/renderer/markdown.py`**

```python
from app.services.analysis.schemas import AnalysisResult


def render_markdown(a: AnalysisResult) -> str:
    lines: list[str] = []
    lines.append(f"# {a.title}")
    lines.append("")
    lines.append(f"**Data**: {a.meeting_date or 'Nao identificada'}  ")
    lines.append(f"**Duracao**: {a.duration}  ")
    if a.participants:
        lines.append(f"**Participantes**: {', '.join(p.name for p in a.participants)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Resumo Executivo")
    lines.append("")
    lines.append(a.summary)
    lines.append("")

    if a.participants:
        lines.append("## Participantes")
        lines.append("")
        lines.append("| Nome | Papel | Tipo |")
        lines.append("|------|-------|------|")
        for p in a.participants:
            lines.append(f"| {p.name} | {p.role or '-'} | {p.type or '-'} |")
        lines.append("")
        lines.append("> Nota: Whisper nao separa locutores. Atribuicao inferida por contexto.")
        lines.append("")

    if a.topics:
        lines.append("## Topicos Discutidos")
        lines.append("")
        for t in a.topics:
            lines.append(f"### {t.title} ({t.relevance_pct}%)")
            lines.append("")
            lines.append(t.summary)
            if t.quote:
                ts = f" — [{t.quote_ts}]" if t.quote_ts else ""
                lines.append("")
                lines.append(f'> "{t.quote}"{ts}')
            lines.append("")

    if a.decisions:
        lines.append("## Decisoes Tomadas")
        lines.append("")
        for i, d in enumerate(a.decisions, 1):
            ts = f" [{d.quote_ts}]" if d.quote_ts else ""
            extra = f" — {d.context}" if d.context else ""
            lines.append(f"{i}. **{d.text}**{ts}{extra}")
        lines.append("")

    if a.findings:
        lines.append("## Findings")
        lines.append("")
        for i, f in enumerate(a.findings, 1):
            extra = f" — {f.detail}" if f.detail else ""
            lines.append(f"{i}. **{f.text}**{extra}")
        lines.append("")

    if a.actions:
        lines.append("## Acoes e Proximos Passos")
        lines.append("")
        lines.append("| Acao | Responsavel | Prazo | Prioridade | Status |")
        lines.append("|------|-------------|-------|------------|--------|")
        for ac in a.actions:
            lines.append(
                f"| {ac.title} | {ac.owner or '-'} | {ac.deadline or '-'} | "
                f"{ac.priority or '-'} | {ac.status or '-'} |"
            )
        lines.append("")

    if a.risks:
        lines.append("## Riscos Identificados")
        lines.append("")
        lines.append("| Risco | Probabilidade | Impacto |")
        lines.append("|-------|---------------|---------|")
        for r in a.risks:
            lines.append(f"| {r.text} | {r.probability}/10 | {r.impact}/10 |")
        lines.append("")

    if a.timeline:
        lines.append("## Timeline de Eventos")
        lines.append("")
        for ev in a.timeline:
            lines.append(f"- **{ev.range}** ({ev.tone}) — {ev.title}: {ev.summary}")
        lines.append("")

    if a.entities:
        lines.append("## Entidades Mencionadas")
        lines.append("")
        by_kind: dict[str, list[str]] = {}
        for e in a.entities:
            by_kind.setdefault(e.kind, []).append(e.name)
        for kind, names in by_kind.items():
            lines.append(f"- **{kind.capitalize()}**: {', '.join(names)}")
        lines.append("")

    if a.sentiment or a.engagement:
        lines.append("## Sentimento e Dinamica")
        lines.append("")
        if a.sentiment:
            lines.append(f"- Sentimento geral: {a.sentiment}")
        if a.engagement:
            lines.append(f"- Engajamento: {a.engagement}")
        lines.append("")

    if a.insights:
        lines.append("## Insights")
        lines.append("")
        for ins in a.insights:
            lines.append(f"- {ins}")
        lines.append("")

    if a.flow:
        lines.append("## Fluxo / Processo")
        lines.append("")
        for i, step in enumerate(a.flow, 1):
            lines.append(f"{i}. {step}")
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 3: Teste**

Create `backend/tests/unit/test_markdown_renderer.py`:

```python
from app.services.analysis.schemas import AnalysisResult, Topic, Decision
from app.services.renderer.markdown import render_markdown


def test_minimal_render():
    a = AnalysisResult(
        slug="x", title="Reuniao X", duration="12:34",
        summary="Discussao sobre api.",
    )
    md = render_markdown(a)
    assert "# Reuniao X" in md
    assert "Resumo Executivo" in md


def test_render_skips_empty_sections():
    a = AnalysisResult(slug="x", title="T", duration="01:00", summary="s")
    md = render_markdown(a)
    assert "## Decisoes" not in md
    assert "## Timeline" not in md


def test_render_topic_with_quote():
    a = AnalysisResult(
        slug="x", title="T", duration="01:00", summary="s",
        topics=[Topic(title="API", summary="rest vs grpc", relevance_pct=80,
                      quote="precisamos decidir", quote_ts="03:45")]
    )
    md = render_markdown(a)
    assert "### API (80%)" in md
    assert '"precisamos decidir"' in md
    assert "[03:45]" in md
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/renderer/__init__.py backend/app/services/renderer/markdown.py backend/tests/unit/test_markdown_renderer.py
git commit -m "backend: markdown renderer with section skipping + tests"
```

---

### Task 6.2: Dashboard HTML renderer (zero JS para dados)

**Files:**
- Create: `backend/app/services/renderer/dashboard.py`

Este renderer deve seguir **estritamente** as regras do §10 do spec. Nada de Chart.js, nada de JS para dados.

- [ ] **Step 1: `backend/app/services/renderer/dashboard.py`**

```python
from html import escape
from app.services.analysis.schemas import AnalysisResult


CSS = """
:root {
  color-scheme: light;
  --primary: #4f46e5;
  --primary-dark: #312e81;
  --purple: #7c3aed;
  --bg: #f8fafc;
  --surface: #ffffff;
  --text: #0f172a;
  --muted: #64748b;
  --border: #e2e8f0;
  --decisao: #16a34a;
  --finding: #d97706;
  --problema: #dc2626;
  --info: #2563eb;
  --construtivo: #7c3aed;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.5; }
.header { background: linear-gradient(135deg, #312e81, #4f46e5, #7c3aed);
  color: #fff; padding: 48px 32px; }
.header h1 { margin: 0 0 8px; font-size: 28px; }
.header .meta { opacity: 0.85; font-size: 14px; }
main { max-width: 1100px; margin: 0 auto; padding: 32px; }
section { background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 24px; margin-bottom: 24px; }
section h2 { margin: 0 0 16px; font-size: 20px; }
.meta-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
.meta-card { padding: 16px; border: 1px solid var(--border); border-radius: 8px; background: #fafbff; }
.meta-card .label { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
.meta-card .value { font-size: 22px; font-weight: 600; margin-top: 4px; }
.bar { height: 8px; background: #eef2ff; border-radius: 4px; overflow: hidden; }
.bar > span { display: block; height: 100%; background: var(--primary); }
.topic { margin-bottom: 16px; }
.topic .title { display: flex; justify-content: space-between; font-weight: 600; }
.topic .summary { color: var(--muted); margin: 4px 0 8px; }
.donut { width: 160px; height: 160px; border-radius: 50%; margin: 0 auto; }
.donut-label { text-align: center; margin-top: 8px; font-size: 14px; color: var(--muted); }
.insight-card { padding: 16px; border-left: 4px solid var(--primary); background: #fafbff;
  margin-bottom: 12px; border-radius: 0 8px 8px 0; }
.insight-card.decisao { border-left-color: var(--decisao); background: #f0fdf4; }
.insight-card.finding { border-left-color: var(--finding); background: #fffbeb; }
.insight-card.problema { border-left-color: var(--problema); background: #fef2f2; }
.insight-card.acao { border-left-color: var(--info); background: #eff6ff; }
.timeline-item { display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--border); }
.timeline-item:last-child { border-bottom: none; }
.timeline-item .range { font-family: ui-monospace, monospace; color: var(--muted);
  min-width: 120px; font-size: 13px; }
.timeline-item.positive { border-left: 3px solid var(--decisao); padding-left: 12px; }
.timeline-item.neutral { border-left: 3px solid var(--muted); padding-left: 12px; }
.timeline-item.concern { border-left: 3px solid var(--problema); padding-left: 12px; }
.timeline-item.constructive { border-left: 3px solid var(--construtivo); padding-left: 12px; }
.tag { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px;
  font-weight: 500; margin: 2px; background: #eef2ff; color: var(--primary-dark); }
.tag-sistema { background: #dbeafe; color: #1d4ed8; }
.tag-orgao { background: #fae8ff; color: #86198f; }
.tag-tech { background: #dcfce7; color: #166534; }
.tag-ferramenta { background: #fef3c7; color: #92400e; }
.tag-pessoa { background: #fee2e2; color: #991b1b; }
.actions-table { width: 100%; border-collapse: collapse; }
.actions-table th, .actions-table td { text-align: left; padding: 10px;
  border-bottom: 1px solid var(--border); font-size: 14px; }
.actions-table th { background: #f1f5f9; }
.risk-matrix { display: grid; grid-template-columns: repeat(10, 1fr); gap: 2px;
  aspect-ratio: 1; max-width: 400px; margin: 0 auto; }
.risk-cell { background: #f1f5f9; border-radius: 2px; position: relative; }
.risk-dot { position: absolute; width: 14px; height: 14px; background: var(--problema);
  border-radius: 50%; top: 50%; left: 50%; transform: translate(-50%, -50%);
  border: 2px solid #fff; }
.transcript { font-family: ui-monospace, monospace; font-size: 13px;
  background: #f8fafc; padding: 16px; border-radius: 8px; max-height: 600px;
  overflow-y: auto; white-space: pre-wrap; }
.search-input { width: 100%; padding: 12px; border: 1px solid var(--border);
  border-radius: 8px; font-size: 14px; margin-bottom: 12px;
  background: #ffffff; color: #0f172a; }
footer { text-align: center; padding: 32px; color: var(--muted); font-size: 12px; }
"""


def _donut_conic(sentiment: str | None) -> str:
    # Representação visual simples do sentimento em conic-gradient.
    if not sentiment:
        return "background: conic-gradient(#e2e8f0 0 100%);"
    s = sentiment.lower()
    if "positiv" in s:
        return "background: conic-gradient(#16a34a 0 75%, #e2e8f0 75% 100%);"
    if "negativ" in s or "preoc" in s:
        return "background: conic-gradient(#dc2626 0 40%, #e2e8f0 40% 100%);"
    return "background: conic-gradient(#4f46e5 0 55%, #e2e8f0 55% 100%);"


def _kind_class(kind: str) -> str:
    mapping = {
        "sistema": "tag-sistema", "orgao": "tag-orgao", "tech": "tag-tech",
        "ferramenta": "tag-ferramenta", "pessoa": "tag-pessoa",
    }
    return mapping.get(kind, "")


def render_dashboard(a: AnalysisResult, transcript_text: str) -> str:
    meta_cards = [
        ("Duracao", a.duration),
        ("Data", a.meeting_date or "Nao identificada"),
        ("Participantes", str(len(a.participants))),
        ("Decisoes", str(len(a.decisions))),
        ("Acoes", str(len(a.actions))),
        ("Riscos", str(len(a.risks))),
    ]

    sections: list[str] = []

    sections.append(f"""
    <section>
      <h2>Visao Geral</h2>
      <div class="meta-cards">
        {''.join(f'<div class="meta-card"><div class="label">{escape(l)}</div><div class="value">{escape(v)}</div></div>' for l, v in meta_cards)}
      </div>
      <p style="margin-top: 20px; color: var(--muted);">{escape(a.summary)}</p>
    </section>
    """)

    if a.sentiment or a.engagement:
        style = _donut_conic(a.sentiment)
        sections.append(f"""
        <section>
          <h2>Sentimento e Dinamica</h2>
          <div class="donut" style="{style}"></div>
          <div class="donut-label">{escape(a.sentiment or '')}</div>
          {f'<p style="text-align:center;color:var(--muted);">Engajamento: {escape(a.engagement)}</p>' if a.engagement else ''}
        </section>
        """)

    if a.participants:
        chips = "".join(
            f'<span class="tag tag-pessoa">{escape(p.name)}'
            f'{f" ({escape(p.role)})" if p.role else ""}</span>'
            for p in a.participants
        )
        sections.append(f"""
        <section>
          <h2>Participantes</h2>
          {chips}
          <p style="color:var(--muted);font-size:13px;margin-top:12px;">Whisper nao separa locutores. Atribuicao inferida por contexto.</p>
        </section>
        """)

    if a.topics:
        items = "".join(
            f'<div class="topic">'
            f'<div class="title"><span>{escape(t.title)}</span><span>{t.relevance_pct}%</span></div>'
            f'<div class="summary">{escape(t.summary)}</div>'
            f'<div class="bar"><span style="width:{t.relevance_pct}%"></span></div>'
            f'</div>'
            for t in a.topics
        )
        sections.append(f'<section><h2>Topicos Discutidos</h2>{items}</section>')

    if a.entities:
        chips = "".join(
            f'<span class="tag {_kind_class(e.kind)}">{escape(e.name)}</span>'
            for e in a.entities
        )
        sections.append(f'<section><h2>Entidades</h2>{chips}</section>')

    if a.flow:
        steps = "".join(f"<li>{escape(s)}</li>" for s in a.flow)
        sections.append(f'<section><h2>Fluxo / Processo</h2><ol>{steps}</ol></section>')

    if a.timeline:
        items = "".join(
            f'<div class="timeline-item {escape(ev.tone)}">'
            f'<div class="range">{escape(ev.range)}</div>'
            f'<div><strong>{escape(ev.title)}</strong><br><span style="color:var(--muted);font-size:13px;">{escape(ev.summary)}</span></div>'
            f'</div>'
            for ev in a.timeline
        )
        sections.append(f'<section><h2>Timeline</h2>{items}</section>')

    cards: list[str] = []
    for d in a.decisions:
        cards.append(f'<div class="insight-card decisao"><strong>Decisao</strong><br>{escape(d.text)}</div>')
    for f in a.findings:
        cards.append(f'<div class="insight-card finding"><strong>Finding</strong><br>{escape(f.text)}</div>')
    for ins in a.insights:
        cards.append(f'<div class="insight-card"><strong>Insight</strong><br>{escape(ins)}</div>')
    if cards:
        sections.append(f'<section><h2>Insights e Decisoes</h2>{"".join(cards)}</section>')

    if a.risks:
        # Renderiza uma grade 10x10 com pontos nas coordenadas (prob, impact).
        cells = []
        for imp in range(10, 0, -1):
            for prob in range(1, 11):
                dot = next((r for r in a.risks if r.probability == prob and r.impact == imp), None)
                inner = '<div class="risk-dot"></div>' if dot else ""
                cells.append(f'<div class="risk-cell">{inner}</div>')
        grid = "".join(cells)
        sections.append(f"""
        <section>
          <h2>Matriz de Risco (Probabilidade x Impacto)</h2>
          <div class="risk-matrix">{grid}</div>
          <ul style="margin-top:16px;">
            {''.join(f'<li>{escape(r.text)} (P{r.probability}/I{r.impact})</li>' for r in a.risks)}
          </ul>
        </section>
        """)

    if a.actions:
        rows = "".join(
            f'<tr><td>{escape(ac.title)}</td><td>{escape(ac.owner or "-")}</td>'
            f'<td>{escape(ac.deadline or "-")}</td><td>{escape(ac.priority or "-")}</td>'
            f'<td>{escape(ac.status or "-")}</td></tr>'
            for ac in a.actions
        )
        sections.append(f"""
        <section>
          <h2>Acoes e Proximos Passos</h2>
          <table class="actions-table">
            <thead><tr><th>Acao</th><th>Responsavel</th><th>Prazo</th><th>Prioridade</th><th>Status</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </section>
        """)

    sections.append(f"""
    <section>
      <h2>Transcricao</h2>
      <input type="text" class="search-input" placeholder="Buscar na transcricao (enhancement JS)" id="q">
      <div class="transcript" id="t">{escape(transcript_text)}</div>
    </section>
    """)

    enhancement_js = """
    <script>
      (function() {
        var q = document.getElementById('q');
        var t = document.getElementById('t');
        if (!q || !t) return;
        var original = t.textContent;
        q.addEventListener('input', function() {
          var term = q.value.trim();
          if (!term) { t.textContent = original; return; }
          var re = new RegExp(term.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&'), 'gi');
          var rendered = original.replace(re, function(m) {
            return '<<<MARK>>>' + m + '<<<ENDMARK>>>';
          });
          t.innerHTML = rendered
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/&lt;&lt;&lt;MARK&gt;&gt;&gt;/g, '<mark>')
            .replace(/&lt;&lt;&lt;ENDMARK&gt;&gt;&gt;/g, '</mark>');
        });
      })();
    </script>
    """

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light">
<title>{escape(a.title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="header">
  <h1>{escape(a.title)}</h1>
  <div class="meta">{escape(a.meeting_date or '')} · {escape(a.duration)}</div>
</div>
<main>
{''.join(sections)}
</main>
<footer>Gerado por ata.ai · Nao inventa dados, cita trechos literais</footer>
{enhancement_js}
</body>
</html>
"""
    return html
```

- [ ] **Step 2: Teste**

Create `backend/tests/unit/test_dashboard_renderer.py`:

```python
from app.services.analysis.schemas import AnalysisResult, Topic, Risk
from app.services.renderer.dashboard import render_dashboard


def test_dashboard_contains_title_and_meta_tags():
    a = AnalysisResult(slug="x", title="Minha Reuniao", duration="10:00", summary="s")
    html = render_dashboard(a, "transcricao")
    assert "<title>Minha Reuniao</title>" in html
    assert 'name="color-scheme" content="light"' in html
    assert "chart.js" not in html.lower()
    assert "conic-gradient" in html or "topics" not in html.lower()


def test_dashboard_omits_empty_sections():
    a = AnalysisResult(slug="x", title="T", duration="1:00", summary="s")
    html = render_dashboard(a, "")
    assert "Matriz de Risco" not in html
    assert "Timeline" not in html


def test_dashboard_renders_topic_bar():
    a = AnalysisResult(
        slug="x", title="T", duration="1:00", summary="s",
        topics=[Topic(title="API", summary="x", relevance_pct=80)],
    )
    html = render_dashboard(a, "")
    assert 'width:80%' in html
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/renderer/dashboard.py backend/tests/unit/test_dashboard_renderer.py
git commit -m "backend: dashboard HTML renderer (zero JS for data, follows CLAUDE.md rules)"
```

---

## Fase 7 — Worker pipeline

### Task 7.1: `workers/pipeline.py` — função principal

**Files:**
- Create: `backend/app/workers/__init__.py`, `backend/app/workers/pipeline.py`

- [ ] **Step 1: `backend/app/workers/__init__.py`** (vazio)

```python
```

- [ ] **Step 2: `backend/app/workers/pipeline.py`**

```python
import asyncio
import time
from datetime import datetime
from pathlib import Path
from shutil import copy2
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import get_settings
from app.db import get_session
from app.models import Job, JobEvent, ProviderCredential
from app.security import decrypt_secret
from app.services.analysis import get_provider
from app.services.benchmark import record as record_benchmark
from app.services.ffprobe import get_duration_seconds
from app.services.renderer.dashboard import render_dashboard
from app.services.renderer.markdown import render_markdown
from app.services.storage import analysis_folder, is_video


settings = get_settings()


async def _emit(session: AsyncSession, job_id: UUID, phase: str, pct: int, msg: str, level: str = "info") -> None:
    session.add(JobEvent(job_id=job_id, phase=phase, progress_pct=pct, message=msg, level=level))
    await session.commit()


async def _update_job(session: AsyncSession, job: Job, **fields) -> None:
    for k, v in fields.items():
        setattr(job, k, v)
    session.add(job)
    await session.commit()


async def process_job(ctx, job_id_str: str) -> None:
    job_id = UUID(job_id_str)
    async with get_session() as session:
        job = (await session.exec(select(Job).where(Job.id == job_id))).first()
        if not job:
            return

        await _update_job(session, job, status="running", phase="validating",
                          progress_pct=1, started_at=datetime.utcnow())
        await _emit(session, job_id, "validating", 5, "Validando arquivo")

        try:
            upload = settings.uploads_path / f"{job_id}_{job.input_filename}"
            if not upload.exists():
                raise FileNotFoundError(f"upload missing: {upload}")

            duration_s = await get_duration_seconds(upload)
            await _update_job(session, job, media_duration_s=duration_s, phase="extracting_audio", progress_pct=10)
            await _emit(session, job_id, "extracting_audio", 10, f"Duracao detectada: {duration_s}s")

            wav_path = Path(f"/tmp/{job_id}_audio.wav")
            if is_video(job.input_filename):
                await _run_ffmpeg(upload, wav_path)
                await _emit(session, job_id, "extracting_audio", 15, "Audio extraido")
            else:
                copy2(upload, wav_path)
                await _emit(session, job_id, "extracting_audio", 15, "Audio copiado")

            await _update_job(session, job, phase="transcribing", progress_pct=20)
            await _emit(session, job_id, "transcribing", 20, f"Carregando modelo {job.whisper_model}")

            whisper_started = time.time()
            result = await asyncio.to_thread(_run_whisper, job.whisper_model, wav_path, job_id)
            wall = int(time.time() - whisper_started)

            await record_benchmark(session, job.whisper_model, duration_s, wall)
            await _emit(session, job_id, "transcribing", 70, f"Transcricao concluida em {wall}s")

            await _update_job(session, job, phase="analyzing", progress_pct=72)
            await _emit(session, job_id, "analyzing", 75, f"Analise com {job.llm_provider}")

            cred = (await session.exec(
                select(ProviderCredential).where(
                    ProviderCredential.user_id == job.user_id,
                    ProviderCredential.provider == job.llm_provider,
                )
            )).first()
            api_key = decrypt_secret(cred.api_key_encrypted) if (cred and cred.api_key_encrypted) else None

            provider = get_provider(job.llm_provider)
            analysis = await provider.analyze(
                transcript=result["text"],
                segments_json=_segments_json(result["segments"]),
                model=job.llm_model,
                api_key=api_key,
            )

            await _update_job(session, job, phase="rendering", progress_pct=90)
            await _emit(session, job_id, "rendering", 92, "Gerando artefatos")

            folder = analysis_folder(datetime.utcnow(), analysis.slug)
            folder_name = folder.name

            (folder / "transcricao.vtt").write_bytes(result["vtt_path"].read_bytes())
            (folder / "analise.md").write_text(render_markdown(analysis), encoding="utf-8")
            (folder / "dashboard.html").write_text(render_dashboard(analysis, result["text"]), encoding="utf-8")

            await _update_job(
                session, job, status="done", phase="done",
                progress_pct=100, finished_at=datetime.utcnow(),
                folder_name=folder_name,
            )
            await _emit(session, job_id, "done", 100, "Concluido")

        except Exception as exc:
            await _update_job(
                session, job, status="error", error_message=str(exc)[:2000],
                finished_at=datetime.utcnow(),
            )
            await _emit(session, job_id, job.phase, job.progress_pct, f"Erro: {exc}", level="error")
            raise


async def _run_ffmpeg(src: Path, dst: Path) -> None:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-i", str(src),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", str(dst),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()[:500]}")


def _run_whisper(model_name: str, audio_path: Path, job_id: UUID) -> dict:
    from app.services.whisper_runner import WhisperRunner
    out_dir = Path(f"/tmp/{job_id}_whisper")
    runner = WhisperRunner(model_name)
    return runner.transcribe(audio_path, out_dir)


def _segments_json(segments: list[dict]) -> str:
    import json
    return json.dumps(segments, ensure_ascii=False)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/workers/pipeline.py backend/app/workers/__init__.py
git commit -m "backend: worker pipeline (validate -> extract -> transcribe -> analyze -> render)"
```

---

### Task 7.2: arq worker boot

**Files:**
- Create: `backend/app/workers/main.py`

- [ ] **Step 1: Código**

```python
from arq.connections import RedisSettings
from app.workers.pipeline import process_job


class WorkerSettings:
    """arq worker settings. Requer redis; em produção usamos arq com Postgres via
    `arq-postgres` quando disponível. Como fallback de baixo atrito, este projeto
    usa poll direto de `jobs` onde `status='queued'` — veja implementação abaixo."""
    functions = [process_job]
    redis_settings = RedisSettings()  # nao usado se polling ativo
    max_jobs = 2
    keep_result = 0


# Fallback: polling simples direto na tabela jobs.
# Se preferir `arq` com Redis, adicione redis ao compose e remova este loop.
if __name__ == "__main__":
    import asyncio
    import logging
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlmodel import select
    from app.config import get_settings
    from app.db import get_session
    from app.models import Job

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("worker")

    settings = get_settings()

    async def claim_next() -> str | None:
        async with get_session() as s:
            job = (await s.exec(
                select(Job).where(Job.status == "queued").order_by(Job.created_at).limit(1)
            )).first()
            if not job:
                return None
            job.status = "running"
            s.add(job)
            await s.commit()
            return str(job.id)

    async def main_loop() -> None:
        log.info("worker started — polling jobs table")
        while True:
            job_id = await claim_next()
            if job_id:
                log.info(f"picked up job {job_id}")
                try:
                    await process_job({}, job_id)
                    log.info(f"job {job_id} done")
                except Exception as exc:
                    log.exception(f"job {job_id} failed: {exc}")
            else:
                await asyncio.sleep(2)

    asyncio.run(main_loop())
```

> **Decisão:** trocamos arq+Redis pelo polling direto sobre `jobs` para simplificar (consistente com a escolha §2 do spec de "não rodar Redis"). A tabela `jobs` vira a própria fila. `claim_next()` é atômico via `UPDATE ... RETURNING` numa otimização futura se necessário.

- [ ] **Step 2: Commit**

```bash
git add backend/app/workers/main.py
git commit -m "backend: worker main loop (polls jobs table instead of redis queue)"
```

---

## Fase 8 — Routers jobs/events/artifacts + FastAPI main

### Task 8.1: Jobs router (upload, list, get, delete)

**Files:**
- Create: `backend/app/schemas/jobs.py`, `backend/app/routers/jobs.py`

- [ ] **Step 1: `backend/app/schemas/jobs.py`**

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class JobRead(BaseModel):
    id: UUID
    status: str
    phase: str
    progress_pct: int
    eta_seconds: int | None
    input_filename: str
    input_size_bytes: int
    media_duration_s: int | None
    whisper_model: str
    llm_provider: str
    llm_model: str
    folder_name: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JobCreated(BaseModel):
    id: UUID
```

- [ ] **Step 2: `backend/app/routers/jobs.py`**

```python
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.config import get_settings
from app.db import session_dependency
from app.deps import current_user
from app.models import Job, JobEvent, User
from app.schemas.jobs import JobCreated, JobRead
from app.services.storage import is_supported, upload_path

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
settings = get_settings()


@router.post("", response_model=JobCreated, status_code=status.HTTP_201_CREATED)
async def create_job(
    file: UploadFile = File(...),
    whisper_model: str = Form(...),
    llm_provider: str = Form(...),
    llm_model: str = Form(...),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> JobCreated:
    if not is_supported(file.filename or ""):
        raise HTTPException(400, "unsupported file type")

    job = Job(
        user_id=user.id,
        input_filename=file.filename or "upload.bin",
        input_size_bytes=0,
        whisper_model=whisper_model,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )
    session.add(job)
    await session.flush()

    dst = upload_path(job.id, job.input_filename)
    size = 0
    with dst.open("wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_mb * 1024 * 1024:
                dst.unlink(missing_ok=True)
                raise HTTPException(413, "file too large")
            f.write(chunk)

    job.input_size_bytes = size
    session.add(JobEvent(job_id=job.id, phase="validating", progress_pct=0, message="Upload recebido"))
    await session.commit()

    return JobCreated(id=job.id)


@router.get("", response_model=list[JobRead])
async def list_jobs(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> list[JobRead]:
    rows = (await session.exec(
        select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc()).limit(100)
    )).all()
    return [JobRead.model_validate(r.model_dump()) for r in rows]


@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> JobRead:
    job = (await session.exec(
        select(Job).where(Job.id == job_id, Job.user_id == user.id)
    )).first()
    if not job:
        raise HTTPException(404, "job not found")
    return JobRead.model_validate(job.model_dump())


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> None:
    job = (await session.exec(
        select(Job).where(Job.id == job_id, Job.user_id == user.id)
    )).first()
    if not job:
        return
    # arquivos físicos
    up = upload_path(job.id, job.input_filename)
    if up.exists():
        up.unlink()
    if job.folder_name:
        from shutil import rmtree
        target = settings.analyses_path / job.folder_name
        if target.exists():
            rmtree(target)
    await session.delete(job)
    await session.commit()
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/jobs.py backend/app/routers/jobs.py
git commit -m "backend: jobs router (multipart upload, list, get, delete)"
```

---

### Task 8.2: Events router (SSE via LISTEN/NOTIFY)

**Files:**
- Create: `backend/app/routers/events.py`

- [ ] **Step 1: Código**

```python
import asyncio
import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import psycopg
from app.config import get_settings
from app.db import session_dependency
from app.deps import current_user
from app.models import Job, User

router = APIRouter(prefix="/api/jobs", tags=["events"])
settings = get_settings()


def _psycopg_dsn() -> str:
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    return url


async def _listen_for_job(job_id: UUID):
    """Connect to postgres, LISTEN job_event, yield matching payloads as SSE lines."""
    async with await psycopg.AsyncConnection.connect(_psycopg_dsn(), autocommit=True) as conn:
        async with conn.cursor() as cur:
            await cur.execute("LISTEN job_event;")
        gen = conn.notifies()
        async for note in gen:
            try:
                payload = json.loads(note.payload)
            except Exception:
                continue
            if payload.get("job_id") != str(job_id):
                continue
            yield f"data: {json.dumps(payload)}\n\n"
            if payload.get("phase") == "done" or payload.get("level") == "error":
                break


@router.get("/{job_id}/events")
async def job_events(
    job_id: UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> StreamingResponse:
    job = (await session.exec(
        select(Job).where(Job.id == job_id, Job.user_id == user.id)
    )).first()
    if not job:
        raise HTTPException(404, "job not found")

    async def stream():
        # evento inicial com estado atual do job
        initial = {
            "job_id": str(job_id),
            "phase": job.phase,
            "progress_pct": job.progress_pct,
            "message": "snapshot",
            "level": "info",
        }
        yield f"data: {json.dumps(initial)}\n\n"

        # se já está terminal, encerra
        if job.status in {"done", "error", "canceled"}:
            return

        async for line in _listen_for_job(job_id):
            yield line

    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })
```

> **Nota de autenticação do SSE:** `EventSource` do navegador não manda headers. O frontend deve usar `fetch` com `eventsource-polyfill` **ou** enviar o token via query string (`?token=...`). Para simplificar, o frontend vai usar `@microsoft/fetch-event-source` que aceita headers customizados.

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/events.py
git commit -m "backend: SSE events router via psycopg LISTEN/NOTIFY"
```

---

### Task 8.3: Artifacts router

**Files:**
- Create: `backend/app/routers/artifacts.py`

- [ ] **Step 1: Código**

```python
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.config import get_settings
from app.db import session_dependency
from app.deps import current_user
from app.models import Job, User

router = APIRouter(prefix="/api/jobs", tags=["artifacts"])
settings = get_settings()


_ALLOWED = {
    "transcricao.vtt": "text/vtt",
    "analise.md": "text/markdown",
    "dashboard.html": "text/html",
}


@router.get("/{job_id}/artifacts/{name}")
async def get_artifact(
    job_id: UUID,
    name: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(session_dependency),
) -> FileResponse:
    if name not in _ALLOWED:
        raise HTTPException(404, "unknown artifact")
    job = (await session.exec(
        select(Job).where(Job.id == job_id, Job.user_id == user.id)
    )).first()
    if not job or not job.folder_name:
        raise HTTPException(404, "not found")
    path = settings.analyses_path / job.folder_name / name
    if not path.exists():
        raise HTTPException(404, "file missing")
    return FileResponse(path, media_type=_ALLOWED[name], filename=name if name != "dashboard.html" else None)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/artifacts.py
git commit -m "backend: artifacts router (vtt/md/html download and inline serve)"
```

---

### Task 8.4: FastAPI `main.py` — wire everything

**Files:**
- Create: `backend/app/main.py`

- [ ] **Step 1: Código**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import artifacts, auth, events, jobs, settings as settings_router, whisper


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="ata.ai", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(settings_router.router)
    app.include_router(whisper.router)
    app.include_router(jobs.router)
    app.include_router(events.router)
    app.include_router(artifacts.router)

    @app.get("/health")
    async def health():
        return {"ok": True}

    return app


app = create_app()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/main.py
git commit -m "backend: FastAPI entrypoint wiring all routers + CORS"
```

---

### Task 8.5: Boot smoke test

- [ ] **Step 1: Gerar FERNET_KEY e JWT_SECRET**

```bash
python -c "from cryptography.fernet import Fernet; print('FERNET_KEY=' + Fernet.generate_key().decode())"
openssl rand -hex 32 | awk '{print "JWT_SECRET="$1}'
```

Copie os valores para `.env` (não versione).

- [ ] **Step 2: Subir infra**

```bash
cp .env.example .env  # depois editar FERNET_KEY e JWT_SECRET
docker compose up postgres -d
docker compose up api --build
```

- [ ] **Step 3: Verificar**

```bash
curl http://localhost:8000/health
```

Expected: `{"ok":true}`

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@edilson.dev","password":"ksjao10so!"}'
```

Expected: JSON com `access_token` e `refresh_token`.

- [ ] **Step 4: Commit marker**

```bash
git tag backend-smoke-ok
```

---

## Fase 9 — Frontend scaffold + auth

### Task 9.1: Next.js + Tailwind + tsconfig + Dockerfile

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/next.config.mjs`, `frontend/tailwind.config.ts`, `frontend/postcss.config.js`, `frontend/Dockerfile`, `frontend/.dockerignore`

- [ ] **Step 1: `frontend/package.json`**

```json
{
  "name": "ata-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "@microsoft/fetch-event-source": "2.0.1",
    "zod": "3.23.8",
    "clsx": "2.1.1"
  },
  "devDependencies": {
    "@types/node": "20.14.11",
    "@types/react": "18.3.3",
    "@types/react-dom": "18.3.0",
    "typescript": "5.5.4",
    "tailwindcss": "3.4.7",
    "postcss": "8.4.40",
    "autoprefixer": "10.4.19",
    "eslint": "8.57.0",
    "eslint-config-next": "14.2.5"
  }
}
```

- [ ] **Step 2: `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: `frontend/next.config.mjs`**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
```

- [ ] **Step 4: `frontend/tailwind.config.ts`**

```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4f46e5',
          dark: '#312e81',
          light: '#7c3aed',
        },
      },
      backgroundImage: {
        'brand-gradient': 'linear-gradient(135deg, #312e81, #4f46e5, #7c3aed)',
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 5: `frontend/postcss.config.js`**

```javascript
module.exports = {
  plugins: { tailwindcss: {}, autoprefixer: {} },
};
```

- [ ] **Step 6: `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]
```

- [ ] **Step 7: `frontend/.dockerignore`**

```
node_modules
.next
```

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/next.config.mjs frontend/tailwind.config.ts frontend/postcss.config.js frontend/Dockerfile frontend/.dockerignore
git commit -m "frontend: scaffold next.js 14 + tailwind + dockerfile"
```

---

### Task 9.2: Root layout + globals.css + API client

**Files:**
- Create: `frontend/src/app/layout.tsx`, `frontend/src/app/globals.css`, `frontend/src/lib/api.ts`, `frontend/src/lib/auth.ts`

- [ ] **Step 1: `frontend/src/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  color-scheme: light;
}

body {
  background: #f8fafc;
  color: #0f172a;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
```

- [ ] **Step 2: `frontend/src/app/layout.tsx`**

```tsx
import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'ata.ai',
  description: 'Analise automatizada de reunioes',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 3: `frontend/src/lib/auth.ts`**

```typescript
'use client';

type Tokens = { access_token: string; refresh_token: string };

const STORAGE_KEY = 'ata_tokens';

export function setTokens(t: Tokens): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
  }
}

export function getTokens(): Tokens | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw ? (JSON.parse(raw) as Tokens) : null;
}

export function clearTokens(): void {
  if (typeof window !== 'undefined') localStorage.removeItem(STORAGE_KEY);
}

export function getAccessToken(): string | null {
  return getTokens()?.access_token ?? null;
}
```

- [ ] **Step 4: `frontend/src/lib/api.ts`**

```typescript
'use client';

import { clearTokens, getAccessToken, getTokens, setTokens } from './auth';

const BASE = '';  // rewrites do next.config

type FetchOpts = RequestInit & { skipAuth?: boolean };

async function refreshAccess(): Promise<string | null> {
  const tokens = getTokens();
  if (!tokens) return null;
  const r = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: tokens.refresh_token }),
  });
  if (!r.ok) { clearTokens(); return null; }
  const fresh = await r.json();
  setTokens(fresh);
  return fresh.access_token;
}

export async function api<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  const doFetch = async (token: string | null) => {
    const headers = new Headers(opts.headers);
    if (token && !opts.skipAuth) headers.set('Authorization', `Bearer ${token}`);
    if (opts.body && !headers.has('Content-Type') && !(opts.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }
    return fetch(`${BASE}${path}`, { ...opts, headers });
  };

  let token = getAccessToken();
  let r = await doFetch(token);
  if (r.status === 401 && !opts.skipAuth) {
    token = await refreshAccess();
    if (token) r = await doFetch(token);
  }
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status} ${text}`);
  }
  if (r.status === 204) return undefined as T;
  return r.json() as Promise<T>;
}

export async function apiForm<T>(path: string, form: FormData): Promise<T> {
  return api<T>(path, { method: 'POST', body: form });
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/layout.tsx frontend/src/app/globals.css frontend/src/lib
git commit -m "frontend: root layout, globals, api client with refresh flow"
```

---

### Task 9.3: Login page + middleware

**Files:**
- Create: `frontend/src/app/(auth)/login/page.tsx`, `frontend/middleware.ts`

- [ ] **Step 1: `frontend/src/app/(auth)/login/page.tsx`**

```tsx
'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { api } from '@/lib/api';
import { setTokens } from '@/lib/auth';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null); setLoading(true);
    try {
      const tokens = await api<{access_token: string; refresh_token: string}>(
        '/api/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email, password }),
          skipAuth: true,
        }
      );
      setTokens(tokens);
      router.push('/');
    } catch (e: unknown) {
      setErr('credenciais invalidas');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-gradient p-6">
      <form onSubmit={submit} className="w-full max-w-sm bg-white rounded-2xl shadow-xl p-8 space-y-4">
        <h1 className="text-2xl font-bold text-primary-dark">ata.ai</h1>
        <p className="text-sm text-slate-500">Entre para analisar suas reunioes</p>

        <div>
          <label className="block text-sm font-medium mb-1">Email</label>
          <input
            type="email" required value={email} onChange={e => setEmail(e.target.value)}
            className="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Senha</label>
          <input
            type="password" required value={password} onChange={e => setPassword(e.target.value)}
            className="w-full border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        {err && <p className="text-red-600 text-sm">{err}</p>}
        <button disabled={loading}
          className="w-full bg-primary text-white font-medium rounded-lg py-2 hover:bg-primary-dark transition disabled:opacity-50">
          {loading ? 'Entrando...' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: `frontend/middleware.ts`** (mínimo — a proteção real está nos fetchers do cliente)

```typescript
import { NextResponse, type NextRequest } from 'next/server';

export function middleware(_req: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: [],
};
```

> **Nota:** como tokens ficam em `localStorage`, a proteção SSR via middleware não é direta. Cada página do grupo `(app)` redireciona para `/login` no `useEffect` se não houver token.

- [ ] **Step 3: Commit**

```bash
git add "frontend/src/app/(auth)/login/page.tsx" frontend/middleware.ts
git commit -m "frontend: login page + middleware stub"
```

---

### Task 9.4: App layout (autenticado) + home (lista)

**Files:**
- Create: `frontend/src/app/(app)/layout.tsx`, `frontend/src/app/(app)/page.tsx`

- [ ] **Step 1: `frontend/src/app/(app)/layout.tsx`**

```tsx
'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { clearTokens, getAccessToken } from '@/lib/auth';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace('/login');
    } else {
      setReady(true);
    }
  }, [router]);

  if (!ready) return null;

  return (
    <div className="min-h-screen">
      <header className="bg-brand-gradient text-white">
        <div className="max-w-6xl mx-auto px-6 py-5 flex items-center justify-between">
          <Link href="/" className="text-xl font-bold">ata.ai</Link>
          <nav className="flex gap-6 text-sm">
            <Link href="/">Analises</Link>
            <Link href="/upload">Nova analise</Link>
            <Link href="/settings">Configuracoes</Link>
            <button onClick={() => { clearTokens(); router.replace('/login'); }}>Sair</button>
          </nav>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
    </div>
  );
}
```

- [ ] **Step 2: `frontend/src/app/(app)/page.tsx`**

```tsx
'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type Job = {
  id: string;
  status: string;
  phase: string;
  progress_pct: number;
  input_filename: string;
  media_duration_s: number | null;
  whisper_model: string;
  llm_provider: string;
  created_at: string;
};

function statusBadge(status: string) {
  const map: Record<string, string> = {
    queued: 'bg-slate-100 text-slate-700',
    running: 'bg-blue-100 text-blue-700',
    done: 'bg-green-100 text-green-700',
    error: 'bg-red-100 text-red-700',
    canceled: 'bg-yellow-100 text-yellow-700',
  };
  return `px-2 py-0.5 rounded text-xs font-medium ${map[status] || ''}`;
}

export default function HomePage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<Job[]>('/api/jobs').then(setJobs).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-slate-500">Carregando...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Analises</h1>
        <Link href="/upload" className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium">
          Nova analise
        </Link>
      </div>

      {jobs.length === 0 ? (
        <div className="text-center py-16 text-slate-500">
          <p>Nenhuma analise ainda.</p>
          <Link href="/upload" className="text-primary underline">Fazer a primeira</Link>
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="text-left px-4 py-3">Arquivo</th>
                <th className="text-left px-4 py-3">Duracao</th>
                <th className="text-left px-4 py-3">Modelo</th>
                <th className="text-left px-4 py-3">Provider</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3">Progresso</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(j => (
                <tr key={j.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link href={`/jobs/${j.id}`} className="text-primary hover:underline">
                      {j.input_filename}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{j.media_duration_s ? `${Math.floor(j.media_duration_s/60)}:${(j.media_duration_s%60).toString().padStart(2,'0')}` : '-'}</td>
                  <td className="px-4 py-3">{j.whisper_model}</td>
                  <td className="px-4 py-3">{j.llm_provider}</td>
                  <td className="px-4 py-3"><span className={statusBadge(j.status)}>{j.status}</span></td>
                  <td className="px-4 py-3">{j.progress_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add "frontend/src/app/(app)"
git commit -m "frontend: app layout with header + jobs list home page"
```

---

## Fase 10 — Upload, progresso, settings

### Task 10.1: Upload page (com ETA por modelo)

**Files:**
- Create: `frontend/src/app/(app)/upload/page.tsx`

- [ ] **Step 1: Código**

```tsx
'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { api, apiForm } from '@/lib/api';

type Provider = { id: string; provider: string; default_model: string; enabled: boolean; has_api_key: boolean };
type ModelOption = { name: string; eta_seconds: number; is_default: boolean };

function fmtEta(sec: number): string {
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return s ? `${m}m${s}s` : `${m}m`;
}

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [whisperModel, setWhisperModel] = useState('medium');
  const [providers, setProviders] = useState<Provider[]>([]);
  const [llmProvider, setLlmProvider] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    api<Provider[]>('/api/settings/providers').then(all => {
      const enabled = all.filter(p => p.enabled);
      setProviders(enabled);
      if (enabled[0]) setLlmProvider(enabled[0].provider);
    });
  }, []);

  async function onFile(f: File) {
    setFile(f); setDuration(null); setModels([]);
    // extrai duração no cliente usando HTMLMediaElement
    const url = URL.createObjectURL(f);
    const el = document.createElement('video');
    el.preload = 'metadata';
    el.src = url;
    el.onloadedmetadata = async () => {
      URL.revokeObjectURL(url);
      const d = Math.floor(el.duration);
      setDuration(d);
      const opts = await api<ModelOption[]>(`/api/whisper/models?duration_s=${d}`);
      setModels(opts);
      const def = opts.find(o => o.is_default);
      if (def) setWhisperModel(def.name);
    };
  }

  async function submit() {
    if (!file || !llmProvider) return;
    const provider = providers.find(p => p.provider === llmProvider);
    if (!provider) return;
    setBusy(true); setErr(null);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('whisper_model', whisperModel);
      form.append('llm_provider', llmProvider);
      form.append('llm_model', provider.default_model);
      const { id } = await apiForm<{id: string}>('/api/jobs', form);
      router.push(`/jobs/${id}`);
    } catch (e) {
      setErr(String(e));
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Nova analise</h1>

      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-6">
        <div>
          <label className="block text-sm font-medium mb-2">Arquivo (audio ou video)</label>
          <input
            type="file"
            accept=".mp4,.mov,.webm,.avi,.mkv,.wav,.mp3,.m4a,.ogg,.flac"
            onChange={e => e.target.files?.[0] && onFile(e.target.files[0])}
            className="block w-full text-sm"
          />
          {file && duration !== null && (
            <p className="text-xs text-slate-500 mt-2">
              {file.name} · {(file.size / 1024 / 1024).toFixed(1)} MB · {Math.floor(duration / 60)}:{(duration % 60).toString().padStart(2, '0')}
            </p>
          )}
        </div>

        {models.length > 0 && (
          <div>
            <label className="block text-sm font-medium mb-2">Modelo Whisper</label>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
              {models.map(m => (
                <button
                  key={m.name}
                  type="button"
                  onClick={() => setWhisperModel(m.name)}
                  className={`p-3 rounded-lg border text-sm text-left ${
                    whisperModel === m.name
                      ? 'border-primary bg-primary/5'
                      : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="font-medium">{m.name}</div>
                  <div className="text-xs text-slate-500 mt-1">~{fmtEta(m.eta_seconds)}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {providers.length > 0 && (
          <div>
            <label className="block text-sm font-medium mb-2">Provider de analise LLM</label>
            <select
              value={llmProvider ?? ''}
              onChange={e => setLlmProvider(e.target.value)}
              className="border border-slate-200 rounded-lg px-3 py-2"
            >
              {providers.map(p => (
                <option key={p.provider} value={p.provider}>
                  {p.provider} ({p.default_model})
                </option>
              ))}
            </select>
          </div>
        )}
        {providers.length === 0 && (
          <p className="text-sm text-red-600">Nenhum provider habilitado. Va em Configuracoes.</p>
        )}

        {err && <p className="text-red-600 text-sm">{err}</p>}

        <button
          onClick={submit}
          disabled={!file || !llmProvider || busy}
          className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
        >
          {busy ? 'Enviando...' : 'Processar'}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add "frontend/src/app/(app)/upload"
git commit -m "frontend: upload page with client-side duration + whisper ETA picker"
```

---

### Task 10.2: Job detail page (SSE + iframe dashboard)

**Files:**
- Create: `frontend/src/app/(app)/jobs/[id]/page.tsx`

- [ ] **Step 1: Código**

```tsx
'use client';

import { fetchEventSource } from '@microsoft/fetch-event-source';
import { useEffect, useRef, useState } from 'react';
import { api } from '@/lib/api';
import { getAccessToken } from '@/lib/auth';

type Job = {
  id: string;
  status: string;
  phase: string;
  progress_pct: number;
  input_filename: string;
  folder_name: string | null;
  error_message: string | null;
};

type Event = {
  job_id: string;
  phase: string;
  progress_pct: number;
  message: string;
  level: 'info' | 'warn' | 'error';
};

const PHASE_LABEL: Record<string, string> = {
  validating: 'Validando',
  extracting_audio: 'Extraindo audio',
  transcribing: 'Transcrevendo',
  analyzing: 'Analisando com LLM',
  rendering: 'Gerando artefatos',
  done: 'Concluido',
};

export default function JobPage({ params }: { params: { id: string } }) {
  const [job, setJob] = useState<Job | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<Job>(`/api/jobs/${params.id}`).then(setJob);

    const abort = new AbortController();
    const token = getAccessToken();
    fetchEventSource(`/api/jobs/${params.id}/events`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: abort.signal,
      onmessage(ev) {
        try {
          const data = JSON.parse(ev.data) as Event;
          setEvents(prev => [...prev, data]);
          setJob(prev => prev ? { ...prev, phase: data.phase, progress_pct: data.progress_pct } : prev);
          if (data.phase === 'done' || data.level === 'error') {
            api<Job>(`/api/jobs/${params.id}`).then(setJob);
          }
        } catch {}
      },
      onerror(err) { console.error(err); throw err; },
    }).catch(() => {});

    return () => abort.abort();
  }, [params.id]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [events]);

  if (!job) return <p className="text-slate-500">Carregando...</p>;

  const isDone = job.status === 'done';
  const isError = job.status === 'error';

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">{job.input_filename}</h1>
      <p className="text-sm text-slate-500 mb-6">
        {PHASE_LABEL[job.phase] || job.phase} — {job.progress_pct}%
      </p>

      <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
        <div className="h-3 bg-slate-100 rounded-full overflow-hidden mb-4">
          <div
            className={`h-full ${isError ? 'bg-red-500' : 'bg-primary'} transition-all`}
            style={{ width: `${job.progress_pct}%` }}
          />
        </div>

        {isError && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg text-sm">
            <strong>Erro:</strong> {job.error_message}
          </div>
        )}

        <div ref={logRef} className="mt-4 h-48 overflow-y-auto bg-slate-50 rounded-lg p-3 text-xs font-mono">
          {events.map((e, i) => (
            <div key={i} className={e.level === 'error' ? 'text-red-600' : 'text-slate-700'}>
              [{e.progress_pct}%] {e.phase}: {e.message}
            </div>
          ))}
        </div>
      </div>

      {isDone && job.folder_name && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
          <div className="flex gap-3">
            <a href={`/api/jobs/${job.id}/artifacts/transcricao.vtt`}
               className="text-sm text-primary underline">Baixar transcricao.vtt</a>
            <a href={`/api/jobs/${job.id}/artifacts/analise.md`}
               className="text-sm text-primary underline">Baixar analise.md</a>
            <a href={`/api/jobs/${job.id}/artifacts/dashboard.html`}
               target="_blank" rel="noreferrer"
               className="text-sm text-primary underline">Abrir dashboard</a>
          </div>
          <iframe
            src={`/api/jobs/${job.id}/artifacts/dashboard.html`}
            className="w-full h-[80vh] border border-slate-200 rounded-lg"
          />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add "frontend/src/app/(app)/jobs"
git commit -m "frontend: job detail page with SSE progress + dashboard iframe"
```

---

### Task 10.3: Settings page

**Files:**
- Create: `frontend/src/app/(app)/settings/page.tsx`

- [ ] **Step 1: Código**

```tsx
'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type Provider = {
  id: string;
  provider: string;
  default_model: string;
  enabled: boolean;
  has_api_key: boolean;
};

const LABELS: Record<string, string> = {
  anthropic: 'Anthropic API',
  openai: 'OpenAI',
  openrouter: 'OpenRouter',
  claude_cli: 'Claude CLI (terminal local)',
};

export default function SettingsPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    api<Provider[]>('/api/settings/providers').then(setProviders);
  }, []);

  async function save(p: Provider, apiKey: string | null) {
    setMsg(null);
    const body: Record<string, unknown> = {
      default_model: p.default_model,
      enabled: p.enabled,
    };
    if (apiKey !== null && p.provider !== 'claude_cli') body.api_key = apiKey;
    const updated = await api<Provider>(`/api/settings/providers/${p.provider}`, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
    setProviders(prev => prev.map(x => x.provider === updated.provider ? updated : x));
    setMsg(`${LABELS[p.provider]} atualizado`);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Configuracoes</h1>

      {msg && <p className="text-green-600 text-sm mb-4">{msg}</p>}

      <div className="space-y-4">
        {providers.map(p => (
          <ProviderCard key={p.provider} provider={p} onSave={save} />
        ))}
      </div>
    </div>
  );
}

function ProviderCard({ provider, onSave }: {
  provider: Provider;
  onSave: (p: Provider, apiKey: string | null) => Promise<void>;
}) {
  const [enabled, setEnabled] = useState(provider.enabled);
  const [model, setModel] = useState(provider.default_model);
  const [apiKey, setApiKey] = useState('');
  const [saving, setSaving] = useState(false);

  async function submit() {
    setSaving(true);
    try {
      await onSave(
        { ...provider, enabled, default_model: model },
        apiKey.trim() ? apiKey : null,
      );
      setApiKey('');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-medium">{LABELS[provider.provider] || provider.provider}</h3>
          {provider.has_api_key && <p className="text-xs text-green-600">API key configurada</p>}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />
          Ativado
        </label>
      </div>

      <div className="grid md:grid-cols-2 gap-3 mb-4">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Modelo default</label>
          <input
            value={model}
            onChange={e => setModel(e.target.value)}
            className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        {provider.provider !== 'claude_cli' && (
          <div>
            <label className="block text-xs text-slate-500 mb-1">API key (deixe vazio para manter)</label>
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder={provider.has_api_key ? '••••••••' : ''}
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
            />
          </div>
        )}
      </div>

      <button onClick={submit} disabled={saving}
        className="bg-primary text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50">
        {saving ? 'Salvando...' : 'Salvar'}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add "frontend/src/app/(app)/settings"
git commit -m "frontend: settings page with per-provider credential cards"
```

---

## Fase 11 — E2E validation + handoff

### Task 11.1: E2E manual no Docker

- [ ] **Step 1: Build e subida full**

```bash
docker compose down -v
docker compose build
docker compose up
```

Aguarde todos os healthchecks.

- [ ] **Step 2: Seed confirmado**

Logs do `api` devem mostrar `seeded admin admin@edilson.dev`.

- [ ] **Step 3: Login + configurar provider**

Abrir `http://localhost:3000` → login → `/settings` → habilitar um provider e inserir API key.

- [ ] **Step 4: Upload de reunião real**

Usar o `.mp4` referenciado em `analise_11-04-2026_15-38-30_magistra-boletim-disciplinas/` ou outro. Selecionar modelo `small` (rápido para validar).

- [ ] **Step 5: Validar progresso em tempo real**

A página do job deve mostrar barra subindo e log atualizando. Nenhum polling visível nos devtools (só o stream SSE aberto).

- [ ] **Step 6: Validar resultado**

Iframe do dashboard deve renderizar exatamente no padrão do slash command (paleta indigo, estrutura de seções, zero JS para dados). Download dos 3 artefatos funcional.

- [ ] **Step 7: Reprocessar trocando provider**

Ir em settings, habilitar OpenAI com uma key real, fazer upload de novo arquivo usando OpenAI, confirmar que funciona.

- [ ] **Step 8: Matar o worker no meio de um job**

```bash
docker compose kill worker
```

O job deve ficar com `status='running'` indefinidamente (limitação conhecida — cobrir em task futura). Por ora basta reiniciar o worker:

```bash
docker compose up worker -d
```

- [ ] **Step 9: Tag final**

```bash
git tag v0.1.0-system-web
git push origin main --tags
```

---

### Task 11.2: README pós-sistema

**Files:**
- Create: `README.md`

- [ ] **Step 1: Criar README curto com instruções de `docker compose up`**

```markdown
# ata.ai

Sistema web para analisar reunioes (video/audio) gerando transcricao, analise estruturada e dashboard HTML.

## Como subir

```bash
cp .env.example .env
# gere FERNET_KEY e JWT_SECRET e coloque no .env
docker compose up --build
```

Acesse `http://localhost:3000` com `admin@edilson.dev` / senha definida no `.env`.

## Slash command (uso direto no Claude Code)

O comando original `/analisar-reuniao` continua disponivel em `.claude/commands/` para quem quiser rodar sem subir o sistema web.

## Design

- [Spec do sistema web](docs/superpowers/specs/2026-04-11-sistema-web-ata-ai-design.md)
- [Plano de implementacao](docs/superpowers/plans/2026-04-11-sistema-web-ata-ai.md)
```

- [ ] **Step 2: Commit + push**

```bash
git add README.md
git commit -m "docs: add README with docker compose instructions"
git push origin main
```

---

## Cobertura do spec

| Seção do spec | Tasks que cobrem |
|---|---|
| §2 Stack | 1.1, 9.1 |
| §3 Estrutura | 0.1 |
| §4 Banco (users, provider_credentials, jobs, job_events, whisper_benchmarks, trigger NOTIFY) | 2.1, 2.2 |
| §5 Pipeline do worker (6 fases com %) | 7.1 |
| §6.1 Anthropic | 5.2 |
| §6.2 OpenAI | 5.3 |
| §6.3 OpenRouter | 5.4 |
| §6.4 Claude CLI | 5.5 |
| §7 API (auth, settings, whisper, jobs, events, artifacts) | 3.1, 3.2, 4.3, 8.1, 8.2, 8.3 |
| §7.1 ETA | 4.2, 4.3 |
| §8 Docker compose | 0.2, 1.1, 9.1 |
| §9 Frontend (login, home, upload, job detail, settings) | 9.3, 9.4, 10.1, 10.2, 10.3 |
| §10 Regras do renderer (sem JS para dados) | 6.2 |
| §12 Aceite | 11.1 |

Nenhuma seção do spec ficou sem task associada.
