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
