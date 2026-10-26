"""seed_nvda_daily.csv(M1-1에서 쓴 NVDA 2년 일봉 502건)를 (date, value, memo) 형태로
불러와 저장소(store)에 채운다. 앱이 처음부터 "관심 있는 시계열 데이터 100건 이상"을
갖고 있어야 한다는 요구사항을 충족하기 위한 초기 적재 스크립트.

실행:
    python seed.py
"""

from __future__ import annotations

import csv
from datetime import date as date_type
from pathlib import Path

from repositories.base import Store

CSV_PATH = Path(__file__).resolve().parent / "data" / "seed_nvda_daily.csv"


def seed_from_csv(store: Store) -> int:
    """CSV를 읽어 store에 채운다(비어있는지 확인은 호출자 몫).

    main.py의 lifespan은 연결 확인(store.list_data())과 시딩 여부 판단을 먼저 하고
    나서 이 함수를 부르므로, 여기서 또 list_data()를 불러 왕복을 늘리지 않는다.
    """
    rows = []
    with CSV_PATH.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                (
                    date_type.fromisoformat(row["date"]),
                    float(row["close"]),
                    "NVDA 종가 (Yahoo Finance, M1-1 데이터 재사용)",
                )
            )
    return store.bulk_add_data(rows)


def seed_if_empty(store: Store) -> int:
    """store가 비어있을 때만 CSV로 시딩한다. 채운 건수를 반환(0이면 스킵됨).

    `python seed.py`로 직접 실행할 때 쓰는 자가완결형 버전 — main.py의 lifespan은
    연결 확인을 이미 하므로 이 함수 대신 list_data()+seed_from_csv()를 따로 쓴다.
    """
    if store.list_data():
        return 0
    return seed_from_csv(store)


def main() -> None:
    from repositories import store  # 지연 import — 앱 시작 시점의 store를 그대로 씀

    count = seed_if_empty(store)
    if count:
        print(f"[완료] {count}건 시딩 완료")
    else:
        print("[안내] 이미 데이터가 있어 시딩을 건너뜁니다(중복 적재 방지).")


if __name__ == "__main__":
    main()
