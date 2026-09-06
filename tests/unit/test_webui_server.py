"""
Smoke tests for the FastAPI web UI backend - covers the empty-account /
no-MT5 paths every real first-run hits, plus basic strategy CRUD.
"""
from pathlib import Path

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


@pytest.fixture
def existing_trade_id(test_settings, test_db_manager):
    """Journal notes/annotations have a real FK to trades - seed one to reference."""
    from datetime import datetime, timezone
    from tradeaudit.domain.models import Trade
    from tradeaudit.infrastructure.repositories.trade_repository import TradeRepository

    repo = TradeRepository(test_db_manager)
    saved = repo.save_trades(1, [Trade(
        account_id=1, position_id=1, symbol="EURUSD", direction="BUY",
        open_time=datetime(2026, 1, 1, tzinfo=timezone.utc), status="CLOSED",
    )])
    return saved[0].id


def test_journal_note_round_trip(client, existing_trade_id):
    default_note = client.get(f"/api/trades/{existing_trade_id}/journal").json()
    assert default_note["trade_id"] == existing_trade_id
    assert default_note["rating"] == "A"

    saved = client.post(f"/api/trades/{existing_trade_id}/journal", json={
        "setup_name": "Breakout retest",
        "rating": "B",
        "pre_trade_thesis": "Expecting continuation above resistance.",
        "post_trade_review": "Entered late.",
        "lessons_learned": "Wait for confirmation candle.",
        "mistakes_identified": ["FOMO_ENTRY"],
        "checklist_data": {"Checked HTF trend": True},
    }).json()
    assert saved["rating"] == "B"
    assert saved["mistakes_identified"] == ["FOMO_ENTRY"]

    reloaded = client.get(f"/api/trades/{existing_trade_id}/journal").json()
    assert reloaded["pre_trade_thesis"] == "Expecting continuation above resistance."


def test_annotation_crud(client, existing_trade_id):
    created = client.post(f"/api/trades/{existing_trade_id}/annotations", json={
        "timeframe": "M15",
        "annotation_type": "TREND_LINE",
        "p1_time": "2026-01-01T10:00:00+00:00",
        "p1_price": 1.1000,
        "p2_time": "2026-01-01T11:00:00+00:00",
        "p2_price": 1.1050,
        "color": "#58a6ff",
    }).json()
    assert created["id"] is not None

    listed = client.get(f"/api/trades/{existing_trade_id}/annotations").json()
    assert any(a["id"] == created["id"] for a in listed)

    deleted = client.delete(f"/api/annotations/{created['id']}").json()
    assert deleted["ok"] is True


def test_annotation_rejects_unknown_type(client, existing_trade_id):
    res = client.post(f"/api/trades/{existing_trade_id}/annotations", json={"annotation_type": "NOT_A_REAL_TYPE"})
    assert res.status_code == 400


def test_screenshot_upload_saves_file_and_attaches_to_journal(client, existing_trade_id):
    tiny_png_base64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    res = client.post(f"/api/trades/{existing_trade_id}/screenshot", json={"image_base64": "data:image/png;base64," + tiny_png_base64})
    assert res.status_code == 200
    body = res.json()
    assert Path(body["path"]).exists()
    assert body["path"] in body["note"]["screenshot_paths"]
    Path(body["path"]).unlink(missing_ok=True)


def test_live_journal_without_account(client):
    res = client.get("/api/live-journal/positions").json()
    assert res["status"] == "Configure MT5 settings first"
    assert res["positions"] == []
