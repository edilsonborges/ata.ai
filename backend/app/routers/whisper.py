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
