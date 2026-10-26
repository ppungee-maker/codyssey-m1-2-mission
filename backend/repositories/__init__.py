from core.config import settings
from .base import Store
from .memory import MemoryStore


def build_store() -> Store:
    if settings.use_real_storage:
        try:
            from .firestore import FirestoreStore

            return FirestoreStore(settings.firebase_credentials_json, settings.firebase_project_id)
        except ImportError as exc:
            print(f"[안내] Firestore 연결 실패({exc}) — MemoryStore로 대체합니다.")
    return MemoryStore()


store: Store = build_store()
