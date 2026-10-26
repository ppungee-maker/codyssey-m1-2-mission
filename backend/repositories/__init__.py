"""저장소 선택 — FIREBASE_CREDENTIALS_JSON 이 있으면 Firestore, 없으면 메모리.

키를 넣었는데 Firestore 를 못 열면 **서버가 뜨지 않는다**(메모리로 바꿔 타지 않는다).
바꿔 타면 배포 서버가 재시작할 때마다 데이터가 조용히 사라지는데, 화면은 정상처럼 보여서
아무도 모른다. 원인을 담아 바로 실패하는 편이 낫다.
"""

from core.config import settings

from .base import Store
from .memory import MemoryStore


def build_store() -> Store:
    if not settings.use_real_storage:
        return MemoryStore()
    from .firestore import FirestoreStore  # firebase-admin 이 없으면 여기서 ImportError

    return FirestoreStore(settings.firebase_credentials_json, settings.firebase_project_id)


store: Store = build_store()
