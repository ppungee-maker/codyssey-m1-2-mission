"""실제 Firestore 저장소 — `FIREBASE_CREDENTIALS_JSON`(서비스 계정 키 JSON 문자열)이
환경변수로 설정됐을 때만 선택된다. 자격증명이 없으면
`repositories/__init__.py` 가 `MemoryStore` 를 고르고 이 파일은 import 되지 않는다.

컬렉션 구조:
  data           문서 1개 = DataPoint 1건 (date, value, memo, created_at)
  conversations  문서 1개 = 대화 1건 (title, messages: list[{role, content}], created_at, updated_at)
"""

from __future__ import annotations

import json
from datetime import date as date_type
from datetime import datetime, timezone

from .base import Store

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError as exc:  # pragma: no cover - 로컬 개발 기본 경로에선 도달 안 함
    raise ImportError(
        "firebase-admin이 설치되어 있지 않습니다: pip install firebase-admin"
    ) from exc


def _init_client(credentials_json: str, project_id: str | None):
    if not firebase_admin._apps:
        try:
            info = json.loads(credentials_json)
        except json.JSONDecodeError as exc:
            # 값은 비밀이라 메시지에 싣지 않는다 — 위치만
            raise RuntimeError(
                "FIREBASE_CREDENTIALS_JSON 이 JSON 이 아닙니다 — 서비스 계정 키 파일 **내용**을 "
                f"한 줄로 넣어야 합니다(파일 경로 아님). 문제 위치: {exc.lineno}행 {exc.colno}열"
            ) from None
        cred = credentials.Certificate(info)
        firebase_admin.initialize_app(cred, {"projectId": project_id} if project_id else None)
    return firestore.client()


class FirestoreStore(Store):
    def __init__(self, credentials_json: str, project_id: str | None = None) -> None:
        self._db = _init_client(credentials_json, project_id)
        self._data_col = self._db.collection("data")
        self._conv_col = self._db.collection("conversations")

    # --- data ---
    def add_data(self, date: date_type, value: float, memo: str | None) -> dict:
        doc_ref = self._data_col.document()
        row = {
            "date": date.isoformat(), "value": value, "memo": memo,
            "created_at": datetime.now(timezone.utc),
        }
        doc_ref.set(row)
        return {"id": doc_ref.id, **row}

    _BATCH_LIMIT = 500  # Firestore 일괄쓰기(batch) 한 번에 담을 수 있는 최대 작업 수

    def bulk_add_data(self, rows: list[tuple[date_type, float, str | None]]) -> int:
        """Firestore batch로 묶어 커밋한다 — 502건을 add_data로 한 줄씩 왕복하면
        콜드스타트 직후 첫 기동이 그만큼 느려진다(네트워크 왕복 502번 vs 2번)."""
        count = 0
        for i in range(0, len(rows), self._BATCH_LIMIT):
            chunk = rows[i : i + self._BATCH_LIMIT]
            batch = self._db.batch()
            for date, value, memo in chunk:
                batch.set(
                    self._data_col.document(),
                    {
                        "date": date.isoformat(), "value": value, "memo": memo,
                        "created_at": datetime.now(timezone.utc),
                    },
                )
            batch.commit()
            count += len(chunk)
        return count

    def list_data(self) -> list[dict]:
        docs = self._data_col.order_by("date").stream()
        return [{"id": d.id, **d.to_dict()} for d in docs]

    def get_data(self, data_id: str) -> dict | None:
        doc = self._data_col.document(data_id).get()
        return {"id": doc.id, **doc.to_dict()} if doc.exists else None

    def update_data(self, data_id: str, **fields) -> dict | None:
        doc_ref = self._data_col.document(data_id)
        if not doc_ref.get().exists:
            return None
        updates = {k: (v.isoformat() if isinstance(v, date_type) else v) for k, v in fields.items()}
        doc_ref.update(updates)
        doc = doc_ref.get()
        return {"id": doc.id, **doc.to_dict()}

    def delete_data(self, data_id: str) -> bool:
        doc_ref = self._data_col.document(data_id)
        if not doc_ref.get().exists:
            return False
        doc_ref.delete()
        return True

    # --- conversations ---
    def add_conversation(self, title: str, messages: list[dict]) -> dict:
        doc_ref = self._conv_col.document()
        now = datetime.now(timezone.utc)
        row = {"title": title, "messages": messages, "created_at": now, "updated_at": now}
        doc_ref.set(row)
        return {"id": doc_ref.id, **row}

    def list_conversations(self) -> list[dict]:
        docs = self._conv_col.order_by("updated_at", direction="DESCENDING").stream()
        return [{"id": d.id, **d.to_dict()} for d in docs]

    def get_conversation(self, conv_id: str) -> dict | None:
        doc = self._conv_col.document(conv_id).get()
        return {"id": doc.id, **doc.to_dict()} if doc.exists else None

    def append_messages(self, conv_id: str, messages: list[dict]) -> dict | None:
        doc_ref = self._conv_col.document(conv_id)
        doc = doc_ref.get()
        if not doc.exists:
            return None
        existing = doc.to_dict()
        updated_messages = [*existing.get("messages", []), *messages]
        now = datetime.now(timezone.utc)
        doc_ref.update({"messages": updated_messages, "updated_at": now})
        doc = doc_ref.get()
        return {"id": doc.id, **doc.to_dict()}

    def delete_conversation(self, conv_id: str) -> bool:
        doc_ref = self._conv_col.document(conv_id)
        if not doc_ref.get().exists:
            return False
        doc_ref.delete()
        return True
