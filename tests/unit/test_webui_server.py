"""
Smoke tests for the FastAPI web UI backend - covers the empty-account /
no-MT5 paths every real first-run hits, plus basic strategy CRUD.
"""
import pytest
from fastapi.testclient import TestClient

from tradeaudit.webui.context import AppContext
from tradeaudit.webui.server import create_app


@pytest.fixture
def client(test_settings, test_db_manager):
    ctx = AppContext(settings=test_settings, db_manager=test_db_manager)
    app = create_app(ctx)
    return TestClient(app)


def test_index_serves_spa_shell(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "TradeAudit" in res.text


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


def test_live_journal_without_account(client):
    res = client.get("/api/live-journal/positions").json()
    assert res["status"] == "Configure MT5 settings first"
    assert res["positions"] == []
