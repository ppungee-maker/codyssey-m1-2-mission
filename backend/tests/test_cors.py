from core.config import Settings


def _preflight(client, origin):
    return client.options(
        "/api/data",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )


def test_local_frontend_is_allowed(client):
    r = _preflight(client, "http://127.0.0.1:5500")
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:5500"
    assert "access-control-allow-credentials" not in r.headers


def test_other_origin_is_blocked(client):
    r = _preflight(client, "https://evil.example")
    assert "access-control-allow-origin" not in r.headers


def test_origins_env_trims_trailing_slash(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.vercel.app/, https://b.vercel.app")
    assert Settings.load().cors_origins == ["https://a.vercel.app", "https://b.vercel.app"]


def test_seed_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("SEED_ON_STARTUP", "false")
    assert Settings.load().seed_on_startup is False

