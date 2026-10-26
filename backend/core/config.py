"""환경변수 기반 설정 — 키를 코드에 직접 쓰지 않는다(요구사항 4: 서비스 계정 키 env 관리).

storage/ai 백엔드 선택도 여기서 결정한다:
  - FIREBASE_CREDENTIALS_JSON 이 있으면 Firestore, 없으면 in-memory store(로컬 개발 기본값)
  - OPENAI_API_KEY 가 있으면 실제 OpenAI, 없으면 mock LLM(로컬 개발 기본값)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# backend/.env 를 읽는다. 이미 있는 환경변수(Render 대시보드 값)는 덮어쓰지 않는다.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


# CORS_ORIGINS 를 비우면 로컬 개발 주소만 허용한다(전에는 전체 허용 *).
LOCAL_ORIGINS = ("http://localhost:5500", "http://127.0.0.1:5500")


@dataclass
class Settings:
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    firebase_credentials_json: str | None = None
    firebase_project_id: str | None = None
    cors_origins: list[str] = field(default_factory=lambda: list(LOCAL_ORIGINS))
    summary_days: int | None = None  # 요약 기본 범위(최근 N일). None = 전체
    seed_on_startup: bool = True  # 저장소가 비어 있으면 시작할 때 시드 CSV 를 넣는다

    @classmethod
    def load(cls) -> "Settings":
        # 끝의 「/」는 떼어 낸다 — 브라우저가 보내는 Origin 엔 슬래시가 없어서, 붙여 넣으면 CORS 가 막힌다
        origins_raw = os.environ.get("CORS_ORIGINS") or ",".join(LOCAL_ORIGINS)
        origins = [o.strip().rstrip("/") for o in origins_raw.split(",") if o.strip()]
        return cls(
            openai_api_key=os.environ.get("OPENAI_API_KEY") or None,
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            firebase_credentials_json=os.environ.get("FIREBASE_CREDENTIALS_JSON") or None,
            firebase_project_id=os.environ.get("FIREBASE_PROJECT_ID") or None,
            cors_origins=origins,
            seed_on_startup=os.environ.get("SEED_ON_STARTUP", "true").lower() != "false",
            summary_days=int(os.environ["SUMMARY_DAYS"]) if os.environ.get("SUMMARY_DAYS") else None,
        )

    @property
    def use_real_ai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def use_real_storage(self) -> bool:
        return bool(self.firebase_credentials_json)


settings = Settings.load()
