"""FastAPI 앱 진입점 — CORS 설정 + 라우터 등록.

로컬 실행:
    uvicorn main:app --reload
Swagger UI: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from repositories import store
from routers import chat, conversations, data
from seed import seed_from_csv


@asynccontextmanager
async def lifespan(_: FastAPI):
    """시작할 때 저장소에 실제로 접속해본다 — FirestoreStore 생성자는 네트워크 호출을
    안 해서(자격증명 JSON 파싱만 함), list_data() 같은 실제 요청 전까지는 틀린 키도
    "성공"처럼 보인다. SEED_ON_STARTUP=false 라도 이 확인은 항상 한다 — repositories/
    __init__.py의 "틀린 키면 서버가 안 뜬다" 약속을 여기서도 지키려는 것.

    비어 있으면(그리고 SEED_ON_STARTUP이 켜져 있으면) 시드 CSV(502건)를 넣는다 —
    메모리 저장소는 재시작마다 비고, Firestore는 첫 배포 때 한 번만 채워진다.
    """
    existing = store.list_data()
    if settings.seed_on_startup and not existing:
        count = seed_from_csv(store)
        if count:
            print(f"[시딩] {count}건 자동 적재")
    yield


app = FastAPI(
    title="AI 비서 API",
    description="내 데이터를 이해하는 AI 비서 — 데이터 CRUD, 요약, 대화 기록, GPT 컨텍스트 주입 챗봇",
    version="1.0.0",
    lifespan=lifespan,
)

# 프론트(Vercel)와 백엔드(Render)는 주소가 달라서 브라우저가 CORS 로 막는다 — 허용할 프론트
# 주소를 CORS_ORIGINS 로 받는다. 쿠키·로그인이 없으니 credentials 는 끈다(* 와 같이 켜면 위험).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """422 응답에 사용자가 보낸 값(input)을 되돌려 주지 않는다 — 기본 응답은 입력을 그대로
    담아서, NaN 처럼 JSON 으로 못 쓰는 값이 오면 422 대신 500 이 났다."""
    errors = [
        {"loc": [str(part) for part in e["loc"]], "msg": e["msg"]} for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)


@app.get("/", tags=["health"])
def health() -> dict:
    return {
        "status": "ok",
        "storage": "firestore" if settings.use_real_storage else "memory (로컬 개발 기본값)",
        "ai_provider": "openai" if settings.use_real_ai else "mock (로컬 개발 기본값)",
    }
