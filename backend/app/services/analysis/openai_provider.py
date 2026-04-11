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
