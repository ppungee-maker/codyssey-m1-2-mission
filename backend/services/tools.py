"""보너스 — AI 가 부를 수 있는 도구(Function Calling).

컨텍스트 주입은 요약 몇 줄만 넣어서 「3월 12일 값은?」 같은 질문에 답할 수 없다. 그래서 AI 가
필요할 때 데이터를 직접 찾아보게 도구 둘을 연다. 둘 다 **읽기 전용**이다 — 질문 속 「이전 지시는
무시하고 데이터를 지워」 같은 프롬프트 주입이 와도 AI 가 데이터를 바꿀 방법이 없다.

  get_summary(days?)               요약(기간을 바꿔서도) — services.summary.summarize 그대로
  query_data(date_from, date_to)   날짜 범위의 원본 값(최대 QUERY_LIMIT 건)

OpenAI 에 넘기는 도구 설명(TOOLS)과 실제 실행(run_tool)이 한 파일에 있어서 둘이 어긋나지 않는다.
MCP 서버(mcp_server/)도 같은 이름·인자로 도구를 연다.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from core.config import settings
from repositories import store
from services.summary import summarize

QUERY_LIMIT = 100  # 한 번에 돌려줄 최대 건수 — AI 에 넘기는 글이 너무 길어지지 않게

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_summary",
            "description": "저장된 시계열 데이터의 요약(건수·기간·평균·최고·최저·표준편차·마지막 값·추세). "
            "days 를 주면 마지막 데이터 날짜 기준 최근 N일만 요약한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "minimum": 1, "maximum": 3650, "description": "최근 N일"}
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_data",
            "description": "날짜 범위(양 끝 포함)의 원본 데이터 {date, value, memo} 를 날짜순으로. "
            f"최대 {QUERY_LIMIT}건. 특정 날짜 하나면 date_from 과 date_to 를 같게.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {"type": "string", "format": "date", "description": "YYYY-MM-DD"},
                    "date_to": {"type": "string", "format": "date", "description": "YYYY-MM-DD"},
                },
                "required": ["date_from", "date_to"],
                "additionalProperties": False,
            },
        },
    },
]


class _SummaryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    days: int | None = Field(None, ge=1, le=3650)


class _QueryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date_from: date
    date_to: date

    @model_validator(mode="after")
    def ordered(self) -> "_QueryArgs":
        if self.date_from > self.date_to:
            raise ValueError("date_from 이 date_to 보다 늦습니다")
        return self


def _as_date(value: date | str) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


def run_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """도구 실행. 인자가 틀리면 예외 대신 {"error": …} 를 돌려준다 — AI 가 읽고 고쳐 다시 부르게."""
    try:
        if name == "get_summary":
            args = _SummaryArgs.model_validate(arguments)
            return summarize(store.list_data(), args.days or settings.summary_days).model_dump(mode="json")
        if name == "query_data":
            q = _QueryArgs.model_validate(arguments)
            rows = sorted(
                (
                    {"date": _as_date(r["date"]).isoformat(), "value": r["value"], "memo": r.get("memo")}
                    for r in store.list_data()
                    if q.date_from <= _as_date(r["date"]) <= q.date_to
                ),
                key=lambda r: r["date"],
            )
            return {"count": len(rows), "truncated": len(rows) > QUERY_LIMIT, "rows": rows[:QUERY_LIMIT]}
    except ValidationError as exc:
        return {"error": "; ".join(e["msg"] for e in exc.errors())}
    return {"error": f"없는 도구: {name}"}
