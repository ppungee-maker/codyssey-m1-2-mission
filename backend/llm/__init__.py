"""LLM 선택 — OPENAI_API_KEY 가 있으면 OpenAI, 없으면 mock.

키를 넣었는데 OpenAI 를 못 쓰면 서버가 뜨지 않는다(mock 으로 바꿔 타지 않는다) — 배포에서
「GPT 답이 이상하다」가 사실은 mock 이었던 일을 막는다.
"""

from core.config import settings

from .base import LLMProvider
from .mock import MockLLMProvider


def build_provider() -> LLMProvider:
    if not settings.use_real_ai:
        return MockLLMProvider()
    from .openai_provider import OpenAILLMProvider  # openai 패키지가 없으면 여기서 ImportError

    return OpenAILLMProvider(settings.openai_api_key, settings.openai_model)


provider: LLMProvider = build_provider()
