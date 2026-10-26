import pytest
from fastapi.testclient import TestClient

import llm
import repositories
from core.config import settings


def test_bulk_add_data_default_delegates_to_add_data():
    """오버라이드 안 한 저장소(MemoryStore)는 add_data를 순차로만 호출해도 충분하다."""
    from datetime import date as date_type

    store = repositories.MemoryStore()
    rows = [(date_type(2026, 1, 1), 1.0, "a"), (date_type(2026, 1, 2), 2.0, "b")]

    count = store.bulk_add_data(rows)

    assert count == 2
    assert len(store.list_data()) == 2


def test_lifespan_checks_connection_even_when_seed_on_startup_is_false(monkeypatch):
    """SEED_ON_STARTUP=false라도 시작할 때 저장소에 실제로 접속해봐야 한다 —
    FirestoreStore 생성자는 네트워크 호출을 안 해서, list_data() 같은 실제 요청
    전까지는 틀린 자격증명도 "성공"처럼 보인다(repositories/__init__.py 약속)."""
    from main import app
    from repositories import store as app_store

    monkeypatch.setattr(settings, "seed_on_startup", False)
    monkeypatch.setattr(
        app_store, "list_data", lambda: (_ for _ in ()).throw(RuntimeError("접속 실패"))
    )

    with pytest.raises(RuntimeError, match="접속 실패"):
        with TestClient(app):
            pass


def test_bad_firestore_key_fails_loudly(monkeypatch):
    monkeypatch.setattr(settings, "firebase_credentials_json", "/path/to/key.json")
    with pytest.raises(RuntimeError, match="JSON 이 아닙니다") as err:
        repositories.build_store()
    assert "/path/to/key.json" not in str(err.value)  # 비밀 값은 메시지에 안 싣는다


def test_missing_openai_package_fails_loudly(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setitem(__import__("sys").modules, "llm.openai_provider", None)
    with pytest.raises(ImportError):
        llm.build_provider()


def test_no_keys_means_memory_and_mock(monkeypatch):
    monkeypatch.setattr(settings, "firebase_credentials_json", None)
    monkeypatch.setattr(settings, "openai_api_key", None)
    assert type(repositories.build_store()).__name__ == "MemoryStore"
    assert type(llm.build_provider()).__name__ == "MockLLMProvider"
