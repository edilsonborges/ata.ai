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
