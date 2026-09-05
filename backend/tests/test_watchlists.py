from tests.conftest import auth_headers, client


def test_watchlist_crud_and_duplicate_stock():
    h = auth_headers()
    created = client.post("/watchlists", json={"name": "Tech Stocks", "symbols": ["NVDA", "AAPL"]}, headers=h)
    assert created.status_code == 201
    wid = created.json()["id"]
    listed = client.get("/watchlists", headers=h)
    assert listed.status_code == 200
    assert any(w["id"] == wid for w in listed.json())
    add = client.post(f"/watchlists/{wid}/stocks", json={"symbol": "TSLA"}, headers=h)
    assert add.status_code == 200
    dup = client.post(f"/watchlists/{wid}/stocks", json={"symbol": "TSLA"}, headers=h)
    assert dup.status_code == 409
    missing = client.post(f"/watchlists/{wid}/stocks", json={"symbol": "ZZZZZ"}, headers=h)
    assert missing.status_code == 404
    rm = client.delete(f"/watchlists/{wid}/stocks/TSLA", headers=h)
    assert rm.status_code == 200
    renamed = client.patch(f"/watchlists/{wid}", json={"name": "Core Tech"}, headers=h)
    assert renamed.json()["name"] == "Core Tech"
    gone = client.delete(f"/watchlists/{wid}", headers=h)
    assert gone.status_code == 204


def test_add_stock_by_company_name():
    h = auth_headers()
    created = client.post("/watchlists", json={"name": "Names", "symbols": ["NVDA"]}, headers=h)
    wid = created.json()["id"]
    added = client.post(f"/watchlists/{wid}/stocks", json={"symbol": "google"}, headers=h)
    assert added.status_code == 200
    symbols = [s["symbol"] for s in added.json()["stocks"]]
    assert "GOOGL" in symbols


def test_search_resolves_company_name():
    h = auth_headers()
    found = client.get("/stocks/search", params={"q": "google"}, headers=h)
    assert found.status_code == 200
    assert any(hit["symbol"] == "GOOGL" for hit in found.json())
