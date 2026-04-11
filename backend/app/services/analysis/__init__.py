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
