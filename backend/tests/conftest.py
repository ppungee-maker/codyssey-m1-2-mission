"""테스트는 키 없이 돈다 — 메모리 저장소 + mock LLM.

`.env` 나 셸에 실제 키가 있어도 테스트가 Firestore·OpenAI 를 부르지 않게, 앱을 import 하기
전에 키를 지운다(설정은 import 시점에 한 번 읽힌다).
"""

import os

for key in ("OPENAI_API_KEY", "FIREBASE_CREDENTIALS_JSON", "FIREBASE_PROJECT_ID"):
    os.environ[key] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from repositories import store  # noqa: E402
from seed import seed_if_empty  # noqa: E402


@pytest.fixture()
def client():
    """테스트마다 빈 저장소에 시드 502건을 새로 채운다 — 앞 테스트가 남긴 데이터에 기대지 않게."""
    store.__init__()
    seed_if_empty(store)
    with TestClient(app) as c:
        yield c
