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
    def chat(self, system_prompt, history, user_message, **_):
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
        def chat(self, system_prompt, history, user_message, **_):
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


def test_long_answer_can_be_loaded_again(client, monkeypatch):
    """AI 답은 요청 상한(8000자)보다 길 수 있다 — 불러오기가 500 이 나면 안 된다."""

    class Wordy:
        def chat(self, system_prompt, history, user_message, **_):
            return "가" * 10_000

    monkeypatch.setattr("services.chat.provider", Wordy())
    conv_id = client.post("/api/chat", json={"message": "길게"}).json()["conversation_id"]
    r = client.get(f"/api/conversations/{conv_id}")
    assert r.status_code == 200
    assert len(r.json()["messages"][1]["content"]) == 10_000


def test_full_conversation_is_409_and_unchanged(client, monkeypatch):
    from schemas import CONVERSATION_MAX_BYTES

    # 7000자 × 3바이트 × 42 + 5000자 × 3바이트 = 897,000 — 한도 바로 아래로 만든다
    big = [{"role": "user", "content": "가" * 7000}] * 42 + [{"role": "user", "content": "가" * 5000}]
    assert CONVERSATION_MAX_BYTES - 6000 < 42 * 21000 + 15000 <= CONVERSATION_MAX_BYTES
    conv_id = client.post("/api/conversations", json={"messages": big}).json()["id"]
    before = len(client.get(f"/api/conversations/{conv_id}").json()["messages"])

    called = []

    class Spy:
        def chat(self, system_prompt, history, user_message, **_):
            called.append(1)
            return "ok"

    monkeypatch.setattr("services.chat.provider", Spy())
    r = client.post("/api/chat", json={"message": "하나 더", "conversation_id": conv_id})
    assert r.status_code == 409
    assert not called  # AI 를 부르기 전에 막는다
    assert len(client.get(f"/api/conversations/{conv_id}").json()["messages"]) == before


def test_store_error_is_not_reported_as_ai_failure(client, monkeypatch):
    import pytest

    def broken():
        raise RuntimeError("firestore down")

    monkeypatch.setattr("services.chat.store.list_data", broken)
    with pytest.raises(RuntimeError, match="firestore down"):
        client.post("/api/chat", json={"message": "평균은?"})


def test_many_short_messages_count_toward_the_limit(client, monkeypatch):
    """짧은 메시지 수천 개 — 본문 합은 작아도 Firestore 문서는 메시지마다 구조 몫이 붙는다."""
    from repositories import store
    from schemas import CONVERSATION_MAX_BYTES, MESSAGE_OVERHEAD_BYTES

    n = CONVERSATION_MAX_BYTES // MESSAGE_OVERHEAD_BYTES  # 본문은 n 바이트뿐
    conv = store.add_conversation("짧은 말 많이", [{"role": "user", "content": "a"}] * n)
    r = client.post("/api/chat", json={"message": "또", "conversation_id": conv["id"]})
    assert r.status_code == 409


def test_tool_answers_a_specific_date(client):
    """요약에 없는 「그날 값」 — mock 도 GPT 처럼 query_data 를 불러 답한다."""
    r = client.post("/api/chat", json={"message": "2026-09-02 값은 얼마였어?"}).json()
    assert r["tools_used"] == [
        {"name": "query_data", "arguments": {"date_from": "2026-09-02", "date_to": "2026-09-02"}}
    ]
    assert "224.41" in r["answer"]


def test_tool_recent_days_summary(client):
    r = client.post("/api/chat", json={"message": "최근 30일 평균 알려줘"}).json()
    assert r["tools_used"][0] == {"name": "get_summary", "arguments": {"days": 30}}
    assert "최근 30일 22건" in r["answer"]


def test_no_tool_for_plain_question(client):
    assert client.post("/api/chat", json={"message": "요즘 추세가 어때?"}).json()["tools_used"] == []


def test_openai_provider_runs_tool_loop(monkeypatch):
    """OpenAI 응답을 흉내 내서, 도구 요청 → 실행 → 결과를 다시 보내 최종 답을 받는 왕복을 본다."""
    from types import SimpleNamespace as NS

    from llm.openai_provider import MAX_TOOL_ROUNDS, OpenAILLMProvider

    sent = []

    def fake_create(**kw):
        sent.append(kw)
        if len(sent) == 1:
            call = NS(id="c1", function=NS(name="query_data", arguments='{"date_from":"2026-09-02","date_to":"2026-09-02"}'))
            return NS(choices=[NS(message=NS(content=None, tool_calls=[call]))])
        return NS(choices=[NS(message=NS(content="224.41 입니다", tool_calls=None))])

    p = OpenAILLMProvider("sk-test")
    monkeypatch.setattr(p._client.chat.completions, "create", fake_create)
    calls = []
    answer = p.chat("sys", [], "그날 값?", tools=[{"type": "function"}], run_tool=lambda n, a: calls.append((n, a)) or {"rows": [1]})
    assert answer == "224.41 입니다"
    assert calls == [("query_data", {"date_from": "2026-09-02", "date_to": "2026-09-02"})]
    assert sent[1]["messages"][-1] == {"role": "tool", "tool_call_id": "c1", "content": '{"rows": [1]}'}
    assert MAX_TOOL_ROUNDS >= 1


def test_openai_provider_last_round_forbids_tools(monkeypatch):
    from types import SimpleNamespace as NS

    from llm.openai_provider import MAX_TOOL_ROUNDS, OpenAILLMProvider

    sent = []

    def always_tool(**kw):
        sent.append(kw)
        if kw.get("tool_choice") == "none":
            return NS(choices=[NS(message=NS(content="끝", tool_calls=None))])
        call = NS(id=f"c{len(sent)}", function=NS(name="get_summary", arguments="{}"))
        return NS(choices=[NS(message=NS(content=None, tool_calls=[call]))])

    p = OpenAILLMProvider("sk-test")
    monkeypatch.setattr(p._client.chat.completions, "create", always_tool)
    assert p.chat("sys", [], "?", tools=[{"type": "function"}], run_tool=lambda n, a: {}) == "끝"
    assert len(sent) == MAX_TOOL_ROUNDS + 1 and sent[-1]["tool_choice"] == "none"


def test_non_object_tool_arguments_do_not_break_chat(client, monkeypatch):
    class OddArgs:
        def chat(self, system_prompt, history, user_message, tools=None, run_tool=None):
            result = run_tool("query_data", [])  # GPT 가 인자를 배열로 보낸 경우
            return f"결과: {result}"

    monkeypatch.setattr("services.chat.provider", OddArgs())
    r = client.post("/api/chat", json={"message": "?"})
    assert r.status_code == 200
    assert r.json()["tools_used"] == [] and "JSON 객체" in r.json()["answer"]
