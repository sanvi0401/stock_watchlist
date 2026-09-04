from tests.conftest import auth_headers, client


def test_health_reports_operational_facts():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["provider"] == "mock-terminal"
    assert body["cache"] in {"redis", "memory"}
    assert body["persistence"] in {"durable", "ephemeral"}
    assert body["market_state"] in {"OPEN", "CLOSED", "PRE_MARKET"}


def test_me_requires_auth():
    assert client.get("/auth/me").status_code == 401
    me = client.get("/auth/me", headers=auth_headers())
    assert me.status_code == 200
    assert "email" in me.json()
