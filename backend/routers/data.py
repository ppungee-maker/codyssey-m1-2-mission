"""데이터 API — CRUD 4개 + summary 1개.

    POST   /api/data
    GET    /api/data
    PUT    /api/data/{id}
    DELETE /api/data/{id}
    GET    /api/data/summary
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from core.config import settings
from repositories import store
from schemas import DataPoint, DataPointCreate, DataPointUpdate, DataSummary, IdPath
from services.summary import summarize

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("", response_model=DataPoint, status_code=201)
def create_data(payload: DataPointCreate) -> DataPoint:
    row = store.add_data(payload.date, payload.value, payload.memo)
    return DataPoint(**row)


@router.get("", response_model=list[DataPoint])
def list_data() -> list[DataPoint]:
    return [DataPoint(**row) for row in store.list_data()]


@router.put("/{data_id}", response_model=DataPoint)
def update_data(data_id: IdPath, payload: DataPointUpdate) -> DataPoint:
    # 보낸 필드만 넘긴다 — 「안 보냄」(그대로)과 「memo: null」(지우기)을 구별하려고
    row = store.update_data(data_id, **payload.model_dump(exclude_unset=True))
    if row is None:
        raise HTTPException(status_code=404, detail=f"데이터를 찾을 수 없습니다: {data_id}")
    return DataPoint(**row)


@router.delete("/{data_id}", status_code=204)
def delete_data(data_id: IdPath) -> None:
    if not store.delete_data(data_id):
        raise HTTPException(status_code=404, detail=f"데이터를 찾을 수 없습니다: {data_id}")


@router.get("/summary", response_model=DataSummary)
def get_summary(
    days: int | None = Query(None, ge=1, le=3650, description="최근 N일만 요약(생략 = 서버 기본값)"),
) -> DataSummary:
    """요약 정보 — 챗봇 컨텍스트 주입(POST /api/chat)도 같은 summarize() 를 쓴다."""
    return summarize(store.list_data(), days or settings.summary_days)
