from app.main import app
from tests.conftest import auth_headers, client


def test_protected_without_token():
    r = client.get("/dashboard")
    assert r.status_code == 401


def test_search_and_history_and_settings():
    h = auth_headers()
    client.post("/watchlists", json={"name": "Tech", "symbols": ["NVDA", "TSLA"]}, headers=h)
    client.get("/dashboard", headers=h)
    search = client.get("/stocks/search", params={"q": "nvd"}, headers=h)
    assert search.status_code == 200
    assert any(x["symbol"] == "NVDA" for x in search.json())
    detail = client.get("/stocks/NVDA", headers=h)
    assert detail.status_code == 200
    assert "explanation" in detail.json()
    hist = client.get("/changes/history", headers=h)
    assert hist.status_code == 200
    settings = client.get("/settings", headers=h)
    assert settings.status_code == 200
    patched = client.patch("/settings", json={"sensitivity": "sensitive"}, headers=h)
    assert patched.json()["sensitivity"] == "sensitive"
