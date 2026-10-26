import pytest

from schemas import MEMO_MAX, MESSAGE_MAX


@pytest.mark.parametrize(
    "body",
    [
        {"date": "2026-10-01", "value": 1, "unknown": "x"},  # 모르는 필드
        {"date": "2026-10-01", "value": 1, "memo": "가" * (MEMO_MAX + 1)},  # 메모 길이
        {"date": "20260-10-01", "value": 1},  # 날짜 범위
        {"date": "1800-01-01", "value": 1},
        {"date": "2026-10-01"},  # 값 빠짐
    ],
)
def test_create_rejects(client, body):
    assert client.post("/api/data", json=body).status_code == 422


def test_create_rejects_nan(client):
    # JSON 표준엔 없지만 파이썬 json 은 NaN 을 읽는다 — 평균이 NaN 이 되지 않게 막는다.
    r = client.post(
        "/api/data",
        content=b'{"date": "2026-10-01", "value": NaN}',
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 422


def test_memo_is_trimmed(client):
    row = client.post("/api/data", json={"date": "2026-10-01", "value": 1, "memo": "  메모  "}).json()
    assert row["memo"] == "메모"


def test_update_needs_a_field(client):
    data_id = client.get("/api/data").json()[0]["id"]
    assert client.put(f"/api/data/{data_id}", json={}).status_code == 422


def test_chat_message_length_limit(client):
    r = client.post("/api/chat", json={"message": "가" * (MESSAGE_MAX + 1)})
    assert r.status_code == 422


def test_chat_rejects_unknown_field(client):
    assert client.post("/api/chat", json={"message": "안녕", "role": "system"}).status_code == 422


def test_422_lists_field_and_message(client):
    detail = client.post("/api/data", json={"date": "2026-10-01"}).json()["detail"]
    assert detail[0]["loc"][-1] == "value" and detail[0]["msg"]
    assert "input" not in detail[0]


def test_update_can_clear_memo_but_keeps_unsent_fields(client):
    row = client.post("/api/data", json={"date": "2026-10-01", "value": 5, "memo": "지울 메모"}).json()
    r = client.put(f"/api/data/{row['id']}", json={"memo": None})
    assert r.status_code == 200
    assert r.json()["memo"] is None and r.json()["value"] == 5


def test_update_rejects_null_date_or_value(client):
    data_id = client.get("/api/data").json()[0]["id"]
    assert client.put(f"/api/data/{data_id}", json={"value": None}).status_code == 422
    assert client.put(f"/api/data/{data_id}", json={"date": None}).status_code == 422


@pytest.mark.parametrize("bad_id", ["a.b", "d1;drop", "x" * 65, "%24where", "가나다", "__name__"])
def test_ids_outside_pattern_never_reach_the_store(client, monkeypatch, bad_id):
    """문서 id 는 영문·숫자·_- 만 — 저장소(Firestore 문서 경로)에 닿기 전에 422."""
    from repositories import store

    touched = []
    monkeypatch.setattr(store, "delete_data", lambda i: touched.append(i) or False)
    monkeypatch.setattr(store, "get_conversation", lambda i: touched.append(i))
    assert client.delete(f"/api/data/{bad_id}").status_code == 422
    assert client.get(f"/api/conversations/{bad_id}").status_code == 422
    assert client.post("/api/chat", json={"message": "?", "conversation_id": bad_id}).status_code == 422
    assert touched == []
