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
