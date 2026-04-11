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
