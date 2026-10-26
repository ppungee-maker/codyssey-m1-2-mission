"""무료·오프라인 mock LLM — 실제 API 키 없이도 "컨텍스트 주입이 실제로 동작하는지"를
검증할 수 있게, system_prompt에 주입된 데이터 요약 수치를 답변에 그대로 반영한다.

진짜 자연어 생성은 아니지만, 이 미션의 핵심 요구사항은 "데이터 요약이 시스템
프롬프트에 삽입되고 그걸 기반으로 답한다"는 흐름 자체이므로, mock도 그 흐름이
실제로 연결돼 있음을 보여줘야 한다(단순히 고정 문자열을 반환하면 컨텍스트 주입이
실제로 되는지 확인할 수 없다).
"""

from __future__ import annotations

import re

from .base import LLMProvider, ToolRunner

_NUM = r"[-+]?\d+(?:\.\d+)?"
_DATE = r"\d{4}-\d{2}-\d{2}"


def _extract(pattern: str, text: str, default: str = "정보 없음") -> str:
    m = re.search(pattern, text)
    return m.group(1) if m else default


def _tool_answer(user_message: str, run_tool: ToolRunner) -> str | None:
    """질문에 날짜(YYYY-MM-DD)나 「최근 N일」이 있으면 GPT 처럼 도구를 불러 답한다 — 키 없이도
    Function Calling 흐름(질문 → 도구 호출 → 결과로 답)을 확인할 수 있게."""
    dates = re.findall(_DATE, user_message)
    if dates:
        lo, hi = min(dates), max(dates)
        result = run_tool("query_data", {"date_from": lo, "date_to": hi})
        if "error" in result:
            return f"날짜를 확인해 주세요: {result['error']}"
        if not result["rows"]:
            return f"{lo}~{hi} 에 저장된 데이터가 없습니다."
        shown = ", ".join(f"{r['date']} {r['value']}" for r in result["rows"][:5])
        more = f" 외 {result['count'] - 5}건" if result["count"] > 5 else ""
        return f"{lo}~{hi} 데이터는 {result['count']}건입니다: {shown}{more}."
    m = re.search(r"최근\s*(\d+)\s*일", user_message)
    if m:
        s = run_tool("get_summary", {"days": int(m.group(1))})
        if "error" in s:
            return f"기간을 확인해 주세요: {s['error']}"
        return f"{s['basis']} {s['count']}건의 평균은 {s['mean']}, 추세는 '{s['trend']}'입니다."
    return None


class MockLLMProvider(LLMProvider):
    def chat(
        self,
        system_prompt: str,
        history: list[dict],
        user_message: str,
        tools: list[dict] | None = None,
        run_tool: ToolRunner | None = None,
    ) -> str:
        if tools and run_tool:
            via_tool = _tool_answer(user_message, run_tool)
            if via_tool:
                return f"[mock 응답·도구 사용] {via_tool}"
        count = _extract(rf"건수[:：]\s*({_NUM})", system_prompt)
        mean = _extract(rf"평균[:：]\s*({_NUM})", system_prompt)
        trend = _extract(r"추세[:：]\s*(\S+)", system_prompt)
        period = _extract(r"기간[:：]\s*(\S+\s*~\s*\S+)", system_prompt)

        if any(k in user_message for k in ("추세", "트렌드", "요즘", "최근")):
            focus = f"최근 추세는 '{trend}'입니다."
        elif any(k in user_message for k in ("평균", "얼마")):
            focus = f"현재 저장된 데이터의 평균값은 {mean}입니다."
        elif any(k in user_message for k in ("몇 개", "건수", "개수")):
            focus = f"현재 저장된 데이터는 총 {count}건입니다."
        else:
            focus = f"현재 데이터는 {period} 기간, 총 {count}건이 저장돼 있고 추세는 '{trend}'입니다."

        return (
            f"[mock 응답] '{user_message.strip()}'에 대해 답변드릴게요. {focus} "
            f"(이 응답은 OPENAI_API_KEY 미설정 시 사용되는 결정적 mock이며, 실제 배포 시엔 "
            f"GPT가 같은 컨텍스트로 자연어 답변을 생성합니다.)"
        )
