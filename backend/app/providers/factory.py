from __future__ import annotations

from app.config import settings
from app.providers.base import AIProvider
from app.providers.gemini import GeminiProvider
from app.providers.mock import MockAIProvider


def get_ai_provider() -> AIProvider:
    if settings.ai_provider == "gemini":
        return GeminiProvider()
    return MockAIProvider()
