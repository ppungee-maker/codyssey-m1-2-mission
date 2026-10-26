"""AI 챗봇 API — POST /api/chat. 흐름은 services/chat.py 에 있다(라우터는 HTTP 변환만)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from core.config import settings
from schemas import ChatRequest, ChatResponse
from services.chat import ConversationFull, ConversationNotFound, LLMUnavailable, reply

router = APIRouter(prefix="/api/chat", tags=["chat"])
log = logging.getLogger(__name__)


@router.post(
    "",
    response_model=ChatResponse,
    responses={
        404: {"description": "없는 대화"},
        409: {"description": "대화가 너무 길어짐 — 새 대화로"},
        502: {"description": "AI 응답 실패"},
    },
)
def chat(payload: ChatRequest) -> ChatResponse:
    try:
        conv_id, answer, used = reply(payload.message, payload.conversation_id)
    except ConversationNotFound:
        raise HTTPException(404, f"대화를 찾을 수 없습니다: {payload.conversation_id}") from None
    except ConversationFull:
        raise HTTPException(409, "대화가 너무 길어졌어요. 「새 대화」로 이어서 물어봐 주세요.") from None
    except LLMUnavailable as exc:
        log.warning("LLM 호출 실패: %s", exc)  # 원인은 서버 로그에만 — 키·내부 메시지를 화면에 안 낸다
        raise HTTPException(502, "AI 응답을 받지 못했습니다. 잠시 후 다시 시도해 주세요.") from None
    return ChatResponse(
        conversation_id=conv_id,
        answer=answer,
        provider="openai" if settings.use_real_ai else "mock",
        tools_used=used,
    )
