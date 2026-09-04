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
