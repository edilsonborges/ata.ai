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
