def test_chat_answer_reflects_summary(client):
    """컨텍스트 주입 확인 — 요약의 추세 값이 답변에 들어가야 한다."""
    trend = client.get("/api/data/summary").json()["trend"]
    r = client.post("/api/chat", json={"message": "요즘 추세가 어때?"})
    assert r.status_code == 200
    assert f"'{trend}'" in r.json()["answer"]


def test_chat_sees_new_data(client):
    """데이터를 바꾸면 다음 답변의 건수도 바뀐다 — 요약을 요청마다 새로 계산한다는 증거."""
    count = client.get("/api/data/summary").json()["count"]
    client.post("/api/data", json={"date": "2026-10-01", "value": 1.0})
    answer = client.post("/api/chat", json={"message": "데이터 몇 개야?"}).json()["answer"]
    assert f"{count + 1}건" in answer


def test_chat_saves_and_continues_conversation(client):
    first = client.post("/api/chat", json={"message": "평균은?"}).json()
    conv_id = first["conversation_id"]
    second = client.post("/api/chat", json={"message": "추세는?", "conversation_id": conv_id})
    assert second.json()["conversation_id"] == conv_id

    conv = client.get(f"/api/conversations/{conv_id}").json()
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant", "user", "assistant"]


def test_chat_unknown_conversation_is_404(client):
    r = client.post("/api/chat", json={"message": "안녕", "conversation_id": "nope"})
    assert r.status_code == 404


def test_chat_blank_message_is_422(client):
    assert client.post("/api/chat", json={"message": "   "}).status_code == 422
