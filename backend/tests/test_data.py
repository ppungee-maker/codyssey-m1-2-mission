def test_health(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["storage"].startswith("memory")


def test_seed_has_at_least_100_rows(client):
    rows = client.get("/api/data").json()
    assert len(rows) >= 100
    assert [r["date"] for r in rows] == sorted(r["date"] for r in rows)


def test_summary_fields(client):
    s = client.get("/api/data/summary").json()
    assert s["count"] == len(client.get("/api/data").json())
    assert s["date_from"] <= s["date_to"]
    assert s["min"] <= s["mean"] <= s["max"]
    assert s["trend"] in ("증가", "감소", "유지")


def test_data_crud_roundtrip(client):
    before = client.get("/api/data/summary").json()["count"]

    r = client.post("/api/data", json={"date": "2026-10-01", "value": 123.0, "memo": "테스트"})
    assert r.status_code == 201
    row = r.json()
    assert client.get("/api/data/summary").json()["count"] == before + 1

    r = client.put(f"/api/data/{row['id']}", json={"value": 456.0})
    assert r.status_code == 200
    assert r.json()["value"] == 456.0
    assert r.json()["memo"] == "테스트"  # 안 보낸 필드는 그대로

    assert client.delete(f"/api/data/{row['id']}").status_code == 204
    assert client.get("/api/data/summary").json()["count"] == before


def test_data_missing_id_is_404(client):
    assert client.put("/api/data/nope", json={"value": 1}).status_code == 404
    assert client.delete("/api/data/nope").status_code == 404


def test_data_rejects_bad_input(client):
    assert client.post("/api/data", json={"date": "어제", "value": 1}).status_code == 422
    assert client.post("/api/data", json={"date": "2026-10-01", "value": "많이"}).status_code == 422
