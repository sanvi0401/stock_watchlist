from tests.conftest import auth_headers, client


def test_watchlist_crud_and_duplicate_stock():
    h = auth_headers()
    created = client.post("/watchlists", json={"name": "Tech Stocks", "symbols": ["NVDA", "AAPL"]}, headers=h)
    assert created.status_code == 201
    wid = created.json()["id"]
    assert "identity_token" not in created.json()
    listed = client.get("/watchlists", headers=h)
    assert any(w["id"] == wid for w in listed.json())
    add = client.post(f"/watchlists/{wid}/stocks", json={"symbol": "tsla"}, headers=h)
    assert add.status_code == 200
    assert client.post(f"/watchlists/{wid}/stocks", json={"symbol": "TSLA"}, headers=h).status_code == 409
    assert client.post(f"/watchlists/{wid}/stocks", json={"symbol": "ZZZZZ"}, headers=h).status_code == 404
    rm = client.delete(f"/watchlists/{wid}/stocks/TSLA", headers=h)
    assert rm.status_code == 200
    assert client.delete(f"/watchlists/{wid}/stocks/TSLA", headers=h).status_code == 404
    renamed = client.patch(f"/watchlists/{wid}", json={"name": "Core Tech"}, headers=h)
    assert renamed.json()["name"] == "Core Tech"
    assert client.delete(f"/watchlists/{wid}", headers=h).status_code == 204
    assert client.get(f"/watchlists/{wid}", headers=h).status_code == 404


def test_watchlists_are_isolated_between_users():
    a, b = auth_headers(), auth_headers()
    wid = client.post("/watchlists", json={"name": "Mine", "symbols": ["NVDA"]}, headers=a).json()["id"]
    assert client.get(f"/watchlists/{wid}", headers=b).status_code == 404
    assert client.delete(f"/watchlists/{wid}", headers=b).status_code == 404
    assert client.post(f"/watchlists/{wid}/stocks", json={"symbol": "AAPL"}, headers=b).status_code == 404


def test_add_stock_by_company_name():
    h = auth_headers()
    wid = client.post("/watchlists", json={"name": "Names", "symbols": ["NVDA"]}, headers=h).json()["id"]
    added = client.post(f"/watchlists/{wid}/stocks", json={"symbol": "google"}, headers=h)
    assert added.status_code == 200
    assert "GOOGL" in [s["symbol"] for s in added.json()["stocks"]]


def test_create_dedupes_and_skips_unknown_symbols():
    h = auth_headers()
    created = client.post(
        "/watchlists", json={"name": "Messy", "symbols": ["nvda", "NVDA", "NOPE123", " aapl "]}, headers=h
    )
    assert created.status_code == 201
    assert sorted(s["symbol"] for s in created.json()["stocks"]) == ["AAPL", "NVDA"]


def test_watchlist_capacity_limit(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "max_symbols_per_watchlist", 2)
    h = auth_headers()
    wid = client.post("/watchlists", json={"name": "Small", "symbols": ["NVDA", "AAPL"]}, headers=h).json()["id"]
    full = client.post(f"/watchlists/{wid}/stocks", json={"symbol": "TSLA"}, headers=h)
    assert full.status_code == 400
    assert full.json()["code"] == "watchlist_full"


def test_search_resolves_company_name():
    h = auth_headers()
    found = client.get("/stocks/search", params={"q": "google"}, headers=h)
    assert found.status_code == 200
    assert found.json()[0]["symbol"] == "GOOGL"
