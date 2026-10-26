"""데이터 요약 — 화면의 요약 막대(GET /api/data/summary)와 챗봇 시스템 프롬프트가 같은 함수를 쓴다.

요약 기준을 바꾸려면 여기만 고친다:
  - 기간: `days`(최근 N일). 기준점은 「오늘」이 아니라 **데이터의 마지막 날짜**다 — 시드처럼
    과거 데이터만 있을 때 「최근 30일」이 0건이 되지 않게.
  - 추세: `_trend()` 의 구간 비율(최근 20%)과 문턱(±2%).
  - 지표: `DataSummary` 에 필드를 더하고 여기서 채운다.
"""

from __future__ import annotations

from datetime import date, timedelta
from statistics import mean, pstdev

from schemas import DataSummary

TREND_THRESHOLD = 0.02  # 최근 구간 평균이 이전보다 ±2% 넘게 움직여야 증가/감소


def _as_date(value: date | str) -> date:
    # Firestore 는 날짜를 ISO 문자열로 저장한다 — 메모리 저장소는 date 그대로.
    return value if isinstance(value, date) else date.fromisoformat(value)


def _trend(values: list[float]) -> tuple[str, str]:
    """최근 20%(최소 3건) 구간 평균을 그 이전 구간 평균과 비교한다."""
    if len(values) < 4:
        return "데이터 부족", f"추세를 보려면 4건 이상 필요합니다(지금 {len(values)}건)"
    window = max(3, len(values) // 5)
    recent, before = values[-window:], values[:-window]
    recent_avg, before_avg = mean(recent), mean(before)
    delta = recent_avg - before_avg
    if before_avg:
        # 기준이 음수여도 방향이 뒤집히지 않게 절댓값으로 나눈다(-10 → -5 는 증가)
        ratio = delta / abs(before_avg)
        detail = f"최근 {window}건 평균({recent_avg:.2f})이 이전 대비 {ratio * 100:+.1f}%"
    else:
        # 이전 평균이 0 이면 비율을 못 낸다 — 값들의 크기에 견준 차이로 판단한다
        scale = max(abs(v) for v in values) or 1.0
        ratio = delta / scale
        detail = f"최근 {window}건 평균({recent_avg:.2f})이 이전 평균(0)보다 {delta:+.2f}"
    if ratio > TREND_THRESHOLD:
        return "증가", detail
    if ratio < -TREND_THRESHOLD:
        return "감소", detail
    return "유지", detail


def summarize(rows: list[dict], days: int | None = None) -> DataSummary:
    """rows = 저장소의 data 문서들(순서 무관). days 가 있으면 마지막 날짜 기준 최근 N일만."""
    points = sorted((_as_date(r["date"]), float(r["value"])) for r in rows)
    if points and days:
        start = points[-1][0] - timedelta(days=days - 1)
        points = [p for p in points if p[0] >= start]
    basis = f"최근 {days}일" if days else "전체"
    if not points:
        return DataSummary(
            count=0, basis=basis, trend="데이터 부족", trend_detail="저장된 데이터가 없습니다"
        )

    values = [v for _, v in points]
    trend, trend_detail = _trend(values)
    return DataSummary(
        count=len(points),
        basis=basis,
        date_from=points[0][0],
        date_to=points[-1][0],
        mean=round(mean(values), 4),
        max=round(max(values), 4),
        min=round(min(values), 4),
        stdev=round(pstdev(values), 4),
        latest=round(values[-1], 4),
        trend=trend,
        trend_detail=trend_detail,
    )
