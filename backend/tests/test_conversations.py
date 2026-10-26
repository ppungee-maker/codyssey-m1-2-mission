def test_conversation_crud(client):
    r = client.post(
        "/api/conversations",
        json={"title": "직접 저장", "messages": [{"role": "user", "content": "안녕"}]},
    )
    assert r.status_code == 201
    conv_id = r.json()["id"]

    listed = client.get("/api/conversations").json()
    assert any(c["id"] == conv_id and c["message_count"] == 1 for c in listed)

    assert client.get(f"/api/conversations/{conv_id}").json()["title"] == "직접 저장"
    assert client.delete(f"/api/conversations/{conv_id}").status_code == 204
    assert client.get(f"/api/conversations/{conv_id}").status_code == 404


def test_conversation_rejects_unknown_role(client):
    r = client.post("/api/conversations", json={"messages": [{"role": "system", "content": "x"}]})
    assert r.status_code == 422
