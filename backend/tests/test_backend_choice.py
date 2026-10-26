import pytest

import llm
import repositories
from core.config import settings


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
