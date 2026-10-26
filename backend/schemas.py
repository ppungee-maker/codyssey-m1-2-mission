"""Pydantic 요청/응답 스키마 — 요청 검증은 전부 여기서 한다(라우터에 들어오기 전에 422).

입력을 그대로 저장·LLM 에 넘길 때의 위험에 대한 최소 대응:
  - 모르는 필드는 거부(extra="forbid") — 오타·엉뚱한 필드가 DB 에 섞이지 않게.
  - 길이 상한 — 거대한 메모·질문으로 저장소·LLM 비용이 터지지 않게.
  - 값은 유한한 숫자만(NaN·무한대 거부) — 평균·추세 계산이 깨지지 않게.
  - 날짜는 1900~2100 — 오타(20260-01-01 같은)로 그래프·기간이 망가지지 않게.
화면에 그릴 때의 위험(스크립트 삽입)은 프론트가 textContent 로 막는다.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MEMO_MAX = 200
MESSAGE_MAX = 2000
TITLE_MAX = 100

DateField = Annotated[date_type, Field(ge=date_type(1900, 1, 1), le=date_type(2100, 12, 31))]
ValueField = Annotated[float, Field(allow_inf_nan=False)]
MemoField = Annotated[str | None, Field(max_length=MEMO_MAX)]


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DataPointCreate(_Request):
    date: DateField
    value: ValueField
    memo: MemoField = None


class DataPointUpdate(_Request):
    """보낸 필드만 바꾼다. 아무것도 안 보내면 422."""

    date: DateField | None = None
    value: ValueField | None = None
    memo: MemoField = None

    @model_validator(mode="after")
    def at_least_one(self) -> "DataPointUpdate":
        if self.date is None and self.value is None and self.memo is None:
            raise ValueError("바꿀 필드(date·value·memo)를 하나 이상 보내야 합니다")
        return self


class DataPoint(BaseModel):
    id: str
    date: date_type
    value: float
    memo: str | None = None
    created_at: datetime


class DataSummary(BaseModel):
    count: int
    basis: str = "전체"  # 요약에 쓴 범위 — "전체" | "최근 N일"
    date_from: date_type | None = None
    date_to: date_type | None = None
    mean: float | None = None
    max: float | None = None
    min: float | None = None
    stdev: float | None = None  # 표준편차 — 값이 얼마나 출렁이는지
    latest: float | None = None  # 마지막 날짜의 값
    trend: str  # "증가" | "감소" | "유지" | "데이터 부족"
    trend_detail: str


class MessageIn(_Request):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=MESSAGE_MAX * 4)  # 답변은 질문보다 길 수 있다


class ChatRequest(_Request):
    message: str = Field(max_length=MESSAGE_MAX)
    conversation_id: str | None = Field(None, max_length=100)

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message는 빈 문자열일 수 없습니다")
        return v


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    provider: str  # "mock" | "openai" — 응답이 어느 경로로 생성됐는지 투명하게 노출


class ConversationCreate(_Request):
    title: str | None = Field(None, max_length=TITLE_MAX)
    messages: list[MessageIn] = Field(default_factory=list, max_length=200)


class Conversation(BaseModel):
    id: str
    title: str
    messages: list[MessageIn]
    created_at: datetime
    updated_at: datetime


class ConversationSummary(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime
