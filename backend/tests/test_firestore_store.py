"""FirestoreStore.bulk_add_data의 배치 쪼개기 — 진짜 firebase_admin 없이 단위 테스트."""

from datetime import date

from repositories.firestore import FirestoreStore


class _FakeBatch:
    def __init__(self, sink: list[list]) -> None:
        self._sink = sink
        self._sets: list = []

    def set(self, ref, data) -> None:
        self._sets.append((ref, data))

    def commit(self) -> None:
        self._sink.append(self._sets)


class _FakeCollection:
    def document(self):
        return object()


class _FakeDb:
    def __init__(self) -> None:
        self.commits: list[list] = []

    def batch(self) -> _FakeBatch:
        return _FakeBatch(self.commits)


def _bare_store() -> FirestoreStore:
    """__init__(진짜 자격증명 파싱)을 건너뛰고 _db/_data_col만 가짜로 꽂은 인스턴스."""
    store = FirestoreStore.__new__(FirestoreStore)
    store._db = _FakeDb()
    store._data_col = _FakeCollection()
    return store


def test_bulk_add_data_splits_into_batches_of_limit():
    store = _bare_store()
    rows = [(date(2026, 1, 1), float(i), None) for i in range(1200)]  # 500+500+200

    count = store.bulk_add_data(rows)

    assert count == 1200
    assert [len(batch) for batch in store._db.commits] == [500, 500, 200]


def test_bulk_add_data_single_batch_when_under_limit():
    store = _bare_store()
    rows = [(date(2026, 1, 1), 1.0, "메모")]

    count = store.bulk_add_data(rows)

    assert count == 1
    assert len(store._db.commits) == 1
    assert store._db.commits[0][0][1]["memo"] == "메모"


def test_bulk_add_data_handles_empty_rows():
    store = _bare_store()
    assert store.bulk_add_data([]) == 0
    assert store._db.commits == []
