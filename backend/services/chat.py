"""챗봇 — 컨텍스트 주입(요약 → 시스템 프롬프트) + 대화 저장.

흐름(요구 7):
  1. 데이터 요약을 새로 계산한다(services.summary) — 방금 추가한 데이터도 바로 반영된다.
  2. 요약을 시스템 프롬프트에 넣는다.
  3. LLM 을 부른다(이전 대화는 최근 HISTORY_TURNS 턴만 — 대화가 길어져도 요청 크기가 일정).
  4. **답을 받은 뒤에** 사용자 질문과 답을 한 번에 저장한다. LLM 이 실패하면 아무것도 저장하지
     않는다 — 답 없는 질문만 남은 대화나 빈 대화가 목록에 쌓이지 않게.
"""

from __future__ import annotations

from core.config import settings
from llm import provider
from repositories import store
from services.summary import summarize

HISTORY_TURNS = 10  # 한 턴 = 질문 + 답 2개 메시지
TITLE_LENGTH = 30

SYSTEM_PROMPT_TEMPLATE = """당신은 사용자의 개인 데이터를 이해하고 답하는 AI 비서입니다.
아래는 사용자가 저장한 시계열 데이터의 요약입니다 — 이 정보를 참고해 답변하세요.

[데이터 요약 — {basis}]
건수: {count}
기간: {date_from} ~ {date_to}
평균: {mean}
최고: {max}
최저: {min}
표준편차: {stdev}
마지막 값: {latest}
추세: {trend} ({trend_detail})

사용자가 데이터와 무관한 질문을 하면 일반적인 비서로서 답하되, 데이터 관련 질문에는
반드시 위 요약 수치를 근거로 답하세요. 요약에 없는 수치는 지어내지 말고 모른다고 하세요.
"""


class ConversationNotFound(LookupError):
    pass


class LLMUnavailable(RuntimeError):
    pass


def build_system_prompt() -> str:
    s = summarize(store.list_data(), settings.summary_days)

    def show(v):
        return "-" if v is None else v

    return SYSTEM_PROMPT_TEMPLATE.format(
        basis=s.basis,
        count=s.count,
        date_from=show(s.date_from),
        date_to=show(s.date_to),
        mean=show(s.mean),
        max=show(s.max),
        min=show(s.min),
        stdev=show(s.stdev),
        latest=show(s.latest),
        trend=s.trend,
        trend_detail=s.trend_detail,
    )


def reply(message: str, conversation_id: str | None) -> tuple[str, str]:
    """(conversation_id, answer). 없는 대화면 ConversationNotFound, LLM 실패면 LLMUnavailable."""
    history: list[dict] = []
    if conversation_id:
        conv = store.get_conversation(conversation_id)
        if conv is None:
            raise ConversationNotFound(conversation_id)
        history = conv["messages"][-HISTORY_TURNS * 2 :]

    try:
        answer = provider.chat(build_system_prompt(), history, message)
    except Exception as exc:  # 어떤 LLM 오류든 사용자에겐 「다시 시도」 한 가지라 하나로 묶는다
        raise LLMUnavailable(str(exc)) from exc

    turn = [{"role": "user", "content": message}, {"role": "assistant", "content": answer}]
    if conversation_id:
        store.append_messages(conversation_id, turn)
        return conversation_id, answer
    conv = store.add_conversation(message.strip()[:TITLE_LENGTH], turn)
    return conv["id"], answer
