"""
Smoke tests for the FastAPI web UI backend - covers the empty-account /
no-MT5 paths every real first-run hits, plus basic strategy CRUD.
"""
import pytest
from fastapi.testclient import TestClient

from tradeaudit.webui.context import AppContext
from tradeaudit.webui.server import create_app


API_TOKEN = "test-token-fixed-for-assertions"


@pytest.fixture
def client(test_settings, test_db_manager):
    ctx = AppContext(settings=test_settings, db_manager=test_db_manager)
    app = create_app(ctx, api_token=API_TOKEN)
    return TestClient(app, headers={"X-TradeAudit-Token": API_TOKEN})


def test_index_serves_spa_shell(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "TradeAudit" in res.text


def test_index_embeds_the_api_token_for_the_frontend_to_read(client):
    res = client.get("/")
    assert f'window.__TA_TOKEN__="{API_TOKEN}"' in res.text


def test_api_rejects_requests_without_the_token(test_settings, test_db_manager):
    ctx = AppContext(settings=test_settings, db_manager=test_db_manager)
    app = create_app(ctx, api_token=API_TOKEN)
    unauthenticated_client = TestClient(app)  # no token header at all

    assert unauthenticated_client.get("/api/state").status_code == 401
    assert unauthenticated_client.post("/api/sync", json={}).status_code == 401

    wrong_token_client = TestClient(app, headers={"X-TradeAudit-Token": "wrong"})
    assert wrong_token_client.get("/api/state").status_code == 401

    # The page itself and its static assets must stay reachable without the
    # token - the frontend has to be able to load the page to obtain it.
    assert unauthenticated_client.get("/").status_code == 200
    assert unauthenticated_client.get("/assets/app.js").status_code == 200


def test_state_with_no_account_configured(client):
    res = client.get("/api/state")
    assert res.status_code == 200
    body = res.json()
    assert body["connection_state"] == "DISCONNECTED"
    assert body["account"] is None
    assert body["settings"] is None


def test_trades_and_dashboard_empty_before_any_sync(client):
    trades = client.get("/api/trades")
    assert trades.status_code == 200
    assert trades.json() == []

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["metrics"]["total_trades"] == 0


def test_sync_without_saved_settings_returns_400(client):
    res = client.post("/api/sync", json={})
    assert res.status_code == 400


def test_connect_with_unreachable_account_returns_400(client):
    # Whether MetaTrader5 is installed in the test environment or not, a bogus
    # account/server must surface as a clean 400 with a message, never a crash.
    res = client.post("/api/connect", json={
        "mt5_path": "", "login": 12345, "server": "Demo-Server",
        "timeout_ms": 5000, "password": "x"
    })
    assert res.status_code == 400
    assert res.json()["detail"]


def test_settings_round_trip(client):
    save = client.post("/api/settings", json={
        "mt5_path": r"C:\MT5\terminal64.exe", "login": 999, "server": "Test-Server", "timeout_ms": 30000
    })
    assert save.status_code == 200

    state = client.get("/api/state").json()
    assert state["settings"]["login"] == 999
    assert state["settings"]["server"] == "Test-Server"


def test_strategy_crud(client):
    create = client.post("/api/strategies", json={"name": "Breakout", "description": "A strategy"})
    assert create.status_code == 200
    strategy_id = create.json()["id"]

    listed = client.get("/api/strategies").json()
    assert any(s["id"] == strategy_id for s in listed)

    updated = client.put(f"/api/strategies/{strategy_id}", json={"name": "Breakout v2", "description": "Updated"})
    assert updated.json()["name"] == "Breakout v2"

    deleted = client.delete(f"/api/strategies/{strategy_id}")
    assert deleted.json()["ok"] is True


def test_breakdown_and_strategy_vs_trader_empty(client):
    assert client.get("/api/breakdown").status_code == 200
    svt = client.get("/api/strategy-vs-trader").json()
    assert svt["quality_verdict"] == "NO_TRADES"


def test_recent_logs_endpoint_returns_a_list(client):
    # Whether or not a log file exists yet for this settings instance, the
    # endpoint must always respond with a path and a list, never error.
    res = client.get("/api/logs/recent")
    assert res.status_code == 200
    body = res.json()
    assert "path" in body
    assert isinstance(body["lines"], list)


def test_live_journal_without_account(client):
    res = client.get("/api/live-journal/positions").json()
    assert res["status"] == "Configure MT5 settings first"
    assert res["positions"] == []
