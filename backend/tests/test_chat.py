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


class _Boom:
    def chat(self, system_prompt, history, user_message):
        raise RuntimeError("upstream 500 sk-secret")


def test_llm_failure_is_502_and_saves_nothing(client, monkeypatch):
    monkeypatch.setattr("services.chat.provider", _Boom())
    before = client.get("/api/conversations").json()
    r = client.post("/api/chat", json={"message": "평균은?"})
    assert r.status_code == 502
    assert "sk-secret" not in r.text  # 내부 오류 문구를 화면에 내지 않는다
    assert client.get("/api/conversations").json() == before


def test_llm_failure_keeps_existing_conversation_unchanged(client, monkeypatch):
    conv_id = client.post("/api/chat", json={"message": "평균은?"}).json()["conversation_id"]
    monkeypatch.setattr("services.chat.provider", _Boom())
    assert client.post("/api/chat", json={"message": "또?", "conversation_id": conv_id}).status_code == 502
    assert len(client.get(f"/api/conversations/{conv_id}").json()["messages"]) == 2


def test_history_sent_to_llm_is_capped(client, monkeypatch):
    from services.chat import HISTORY_TURNS

    seen = []

    class Spy:
        def chat(self, system_prompt, history, user_message):
            seen.append(len(history))
            return "ok"

    monkeypatch.setattr("services.chat.provider", Spy())
    conv_id = client.post("/api/chat", json={"message": "0"}).json()["conversation_id"]
    for i in range(HISTORY_TURNS + 3):
        client.post("/api/chat", json={"message": str(i), "conversation_id": conv_id})
    assert max(seen) == HISTORY_TURNS * 2
    assert len(client.get(f"/api/conversations/{conv_id}").json()["messages"]) == (HISTORY_TURNS + 4) * 2


def test_system_prompt_contains_summary():
    from services.chat import build_system_prompt

    prompt = build_system_prompt()
    assert "건수:" in prompt and "추세:" in prompt and "표준편차:" in prompt
