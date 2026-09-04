from tests.conftest import auth_headers, client


def test_protected_without_token():
    assert client.get("/dashboard").status_code == 401


def test_full_flow_search_detail_history_settings():
    h = auth_headers()
    created = client.post("/watchlists", json={"name": "Tech", "symbols": ["NVDA", "TSLA"]}, headers=h)
    assert created.status_code == 201
    dash = client.get("/dashboard", headers=h)
    assert dash.status_code == 200
    body = dash.json()
    assert body["stocks_tracked"] == 2
    assert body["market_state"] in {"OPEN", "CLOSED", "PRE_MARKET"}
    # Mock provider seeds a 14h-old baseline, so the first Overview already has deltas.
    all_items = body["needs_attention_items"] + body["meaningful_items"] + body["stable_items"]
    assert all(i["since_last_check_percent"] is not None for i in all_items)

    search = client.get("/stocks/search", params={"q": "nvd"}, headers=h)
    assert search.status_code == 200
    assert any(x["symbol"] == "NVDA" for x in search.json())

    detail = client.get("/stocks/NVDA", headers=h)
    assert detail.status_code == 200
    assert detail.json()["explanation"]
    assert len(detail.json()["sparkline"]) > 0
    assert client.get("/stocks/ZZZZZZ", headers=h).status_code == 404

    hist = client.get("/changes/history", headers=h)
    assert hist.status_code == 200
    assert "items" in hist.json()

    settings = client.get("/settings", headers=h)
    assert settings.status_code == 200
    patched = client.patch("/settings", json={"sensitivity": "sensitive"}, headers=h)
    assert patched.json()["sensitivity"] == "sensitive"
    assert client.get("/settings", headers=h).json()["sensitivity"] == "sensitive"
    cards = client.patch(
        "/settings",
        json={"sensitivity": "conservative", "lookback_mode": "previous_close", "high_significance_only": True},
        headers=h,
    )
    assert cards.json()["lookback_mode"] == "previous_close"
    assert cards.json()["high_significance_only"] is True
    assert client.patch("/settings", json={"sensitivity": "loud"}, headers=h).status_code == 422
    assert client.patch("/settings", json={"timezone": "Mars/Olympus"}, headers=h).status_code == 400
    assert client.patch("/settings", json={"timezone": "Asia/Kolkata"}, headers=h).json()["timezone"] == "Asia/Kolkata"


def test_dashboard_refresh_is_idempotent_and_ledger_not_duplicated():
    h = auth_headers()
    client.post("/watchlists", json={"name": "Core", "symbols": ["NVDA"]}, headers=h)
    first = client.get("/dashboard", headers=h).json()
    second = client.get("/dashboard", headers=h).json()
    a = (first["needs_attention_items"] + first["meaningful_items"] + first["stable_items"])[0]
    b = (second["needs_attention_items"] + second["meaningful_items"] + second["stable_items"])[0]
    assert a["since_last_check_percent"] == b["since_last_check_percent"]
    assert first["new_visit"] is True and second["new_visit"] is False
    history = client.get("/changes/history", headers=h).json()["items"]
    assert len([i for i in history if i["symbol"] == "NVDA"]) <= 1
    notes = client.get("/notifications", headers=h).json()
    assert len([n for n in notes if n["title"].startswith("NVDA")]) <= 1


def test_checkpoint_marks_everything_seen():
    h = auth_headers()
    client.post("/watchlists", json={"name": "Core", "symbols": ["NVDA", "TSLA"]}, headers=h)
    r = client.post("/dashboard/checkpoint", headers=h)
    assert r.status_code == 200 and r.json()["symbols"] == 2
    dash = client.get("/dashboard", headers=h).json()
    items = dash["needs_attention_items"] + dash["meaningful_items"] + dash["stable_items"]
    assert all(i["since_last_check_percent"] == 0 for i in items)
    assert dash["needs_attention"] == 0


def test_history_pagination():
    h = auth_headers()
    r = client.get("/changes/history", params={"limit": 1}, headers=h)
    assert r.status_code == 200
    assert client.get("/changes/history", params={"limit": 0}, headers=h).status_code == 422


def test_empty_dashboard():
    h = auth_headers()
    dash = client.get("/dashboard", headers=h).json()
    assert dash["stocks_tracked"] == 0
    assert dash["first_time"] is False
