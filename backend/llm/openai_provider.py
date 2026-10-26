"""실제 OpenAI API를 쓰는 프로바이더 — OPENAI_API_KEY가 있을 때만 선택적으로 로드된다."""

from __future__ import annotations

import json

from .base import LLMProvider, ToolRunner

MAX_TOOL_ROUNDS = 3  # 도구 호출 왕복 상한 — AI 가 도구만 계속 부르며 끝나지 않는 일을 막는다

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover - 키 없는 기본 실행 경로에선 도달 안 함
    raise ImportError("openai 패키지가 설치되어 있지 않습니다: pip install openai") from exc


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        # 무료 서버(Render)에서 요청이 매달리지 않게 시간 제한을 둔다 — 넘으면 /api/chat 이 502.
        self._client = OpenAI(api_key=api_key, timeout=30, max_retries=1)
        self._model = model

    def chat(
        self,
        system_prompt: str,
        history: list[dict],
        user_message: str,
        tools: list[dict] | None = None,
        run_tool: ToolRunner | None = None,
    ) -> str:
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        messages += [{"role": h["role"], "content": h["content"]} for h in history]
        messages.append({"role": "user", "content": user_message})
        use_tools = bool(tools and run_tool)

        for round_ in range(MAX_TOOL_ROUNDS + 1):
            extra = {}
            if use_tools:
                # 마지막 왕복에서는 도구를 못 부르게 해서 반드시 글로 답하게 한다
                extra = {"tools": tools, "tool_choice": "none" if round_ == MAX_TOOL_ROUNDS else "auto"}
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.4,
                # 답 길이 상한 — 비용을 묶고, 대화 문서(Firestore 1MiB)가 답 하나로 커지지 않게
                max_completion_tokens=1000,
                **extra,
            )
            msg = resp.choices[0].message
            if not (use_tools and msg.tool_calls):
                return msg.content or ""
            # 1) AI 가 부르겠다고 한 도구 목록을 대화에 남기고 2) 하나씩 실행해 결과를 돌려준다
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": [
                        {
                            "id": c.id,
                            "type": "function",
                            "function": {"name": c.function.name, "arguments": c.function.arguments},
                        }
                        for c in msg.tool_calls
                    ],
                }
            )
            for c in msg.tool_calls:
                try:
                    args = json.loads(c.function.arguments or "{}")
                except json.JSONDecodeError:
                    result = {"error": "인자가 JSON 이 아닙니다"}
                else:
                    result = run_tool(c.function.name, args) if run_tool else {"error": "도구 없음"}
                messages.append(
                    {"role": "tool", "tool_call_id": c.id, "content": json.dumps(result, ensure_ascii=False)}
                )
        return ""  # 도달하지 않는다 — 마지막 왕복은 tool_choice=none
