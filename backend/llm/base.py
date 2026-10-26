"""LLM 프로바이더 인터페이스 — mock/openai 구현체가 이 계약을 따른다."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

ToolRunner = Callable[[str, dict[str, Any]], dict[str, Any]]


class LLMProvider(ABC):
    @abstractmethod
    def chat(
        self,
        system_prompt: str,
        history: list[dict],
        user_message: str,
        tools: list[dict] | None = None,
        run_tool: ToolRunner | None = None,
    ) -> str:
        """system_prompt + 과거 대화(history) + 새 사용자 메시지 -> 답변 텍스트.

        tools(OpenAI 도구 설명)와 run_tool(이름·인자 → 결과)이 오면, 답하는 도중 필요한 도구를
        불러 결과를 보고 답한다(Function Calling).
        """
        ...
