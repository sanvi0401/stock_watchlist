from app.market.mock import MockMarketDataProvider
from app.market.service import _validate
from tests.conftest import auth_headers, client


def test_malformed_quote_rejected():
    q = MockMarketDataProvider().get_quote("NVDA")
    q.price = 0
    assert _validate(q) is None


def test_partial_dashboard_survives_unknown_symbol():
    h = auth_headers()
    created = client.post(
        "/watchlists", json={"name": "Mixed", "symbols": ["NVDA", "AAPL"]}, headers=h
    )
    assert created.status_code == 201
    dash = client.get("/dashboard", headers=h)
    assert dash.status_code == 200
    body = dash.json()
    assert "needs_attention_items" in body
    assert body["stocks_tracked"] >= 2
