from datetime import date

from services.summary import summarize


def _rows(values, start=date(2026, 1, 1)):
    return [
        {"date": date.fromordinal(start.toordinal() + i), "value": v} for i, v in enumerate(values)
    ]


def test_empty():
    s = summarize([])
    assert s.count == 0 and s.trend == "데이터 부족"


def test_order_does_not_matter():
    rows = _rows([10, 10, 10, 10, 10, 20, 20, 20])
    assert summarize(rows) == summarize(list(reversed(rows)))
    assert summarize(rows).trend == "증가"
    assert summarize(rows).latest == 20


def test_firestore_string_dates():
    rows = [{"date": "2026-01-02", "value": 2}, {"date": "2026-01-01", "value": 1}]
    s = summarize(rows)
    assert s.date_from == date(2026, 1, 1) and s.latest == 2


def test_recent_days_counts_back_from_last_data_date():
    rows = _rows(range(100))  # 2026-01-01 ~ 2026-04-10
    s = summarize(rows, days=30)
    assert s.count == 30 and s.basis == "최근 30일"
    assert s.date_to == date(2026, 4, 10) and s.date_from == date(2026, 3, 12)


def test_flat_and_falling():
    assert summarize(_rows([10] * 10)).trend == "유지"
    assert summarize(_rows([20] * 8 + [10] * 2)).trend == "감소"


def test_too_few_points():
    assert summarize(_rows([1, 2, 3])).trend == "데이터 부족"


def test_summary_endpoint_days_param(client):
    assert client.get("/api/data/summary?days=30").json()["basis"] == "최근 30일"
    assert client.get("/api/data/summary?days=0").status_code == 422
