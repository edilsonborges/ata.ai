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
