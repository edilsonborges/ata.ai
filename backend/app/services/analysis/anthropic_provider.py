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
