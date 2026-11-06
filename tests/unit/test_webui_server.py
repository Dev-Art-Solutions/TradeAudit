"""
Smoke tests for the FastAPI web UI backend - covers the empty-account /
no-MT5 paths every real first-run hits, plus basic strategy CRUD.
"""
from pathlib import Path
import base64

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


def test_security_headers_and_origin_validation(client):
    res = client.get("/api/state")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["referrer-policy"] == "no-referrer"
    assert res.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in res.headers["content-security-policy"]
    assert len(res.headers["x-request-id"]) == 32

    rejected = client.post(
        "/api/settings",
        headers={"Origin": "https://malicious.example"},
        json={"login": 1},
    )
    assert rejected.status_code == 403


def test_health_reports_runtime_dependencies(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {
        "status": "ok",
        "version": "0.1.0-test",
        "database": "ok",
        "mt5": "DISCONNECTED",
    }


def test_unhandled_error_is_redacted_and_correlated(test_settings, test_db_manager):
    ctx = AppContext(settings=test_settings, db_manager=test_db_manager)
    app = create_app(ctx, api_token=API_TOKEN)

    @app.get("/api/test-crash")
    def test_crash():
        raise RuntimeError("sensitive implementation detail")

    crash_client = TestClient(app, headers={"X-TradeAudit-Token": API_TOKEN})
    res = crash_client.get("/api/test-crash")
    assert res.status_code == 500
    assert res.json()["detail"] == "Unexpected application error."
    assert "sensitive implementation detail" not in res.text
    assert res.json()["request_id"] == res.headers["x-request-id"]


def test_payload_validation_and_log_bounds(client):
    assert client.post("/api/settings", json={"login": -1}).status_code == 422
    assert client.post("/api/settings", json={"timeout_ms": 10}).status_code == 422
    assert client.post("/api/strategies", json={"name": ""}).status_code == 422
    assert client.get("/api/logs/recent?lines=0").status_code == 422
    assert client.get("/api/logs/recent?lines=2001").status_code == 422


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
    assert dashboard.json()["data_quality"]["grade"] == "N/A"
    assert len(dashboard.json()["audit_snapshot"]["dataset_sha256"]) == 64


def test_audit_snapshot_is_privacy_safe_and_versioned(client):
    res = client.get("/api/audit-snapshot")
    assert res.status_code == 200
    body = res.json()
    assert body["schema_version"] == 1
    assert len(body["dataset_sha256"]) == 64
    assert "account_id" not in res.text.lower()
    assert "position_id" not in res.text.lower()


def test_sync_without_saved_settings_returns_400(client):
    res = client.post("/api/sync", json={})
    assert res.status_code == 400


def test_sync_establishes_safety_backup_before_mutating_history(client):
    from tradeaudit.domain.models import SyncResult

    client.post("/api/settings", json={"login": 777, "server": "Test-Server"})
    ctx = client.app.state.tradeaudit_context
    events = []
    original_protection = ctx.backup_service.ensure_recent_backup

    def protect(**kwargs):
        events.append("backup")
        return original_protection(**kwargs)

    def synchronize(**kwargs):
        events.append("sync")
        return SyncResult(account_id=777, success=True, message="Done")

    ctx.backup_service.ensure_recent_backup = protect
    ctx.sync_service.sync_account_history = synchronize

    res = client.post("/api/sync", json={})

    assert res.status_code == 200
    assert events == ["backup", "sync"]
    assert "pre_sync" in res.json()["backup_protection"]["filename"]
    assert ctx.backup_service.list_backups()


def test_sync_is_canceled_when_safety_backup_fails(client):
    client.post("/api/settings", json={"login": 777, "server": "Test-Server"})
    ctx = client.app.state.tradeaudit_context
    ctx.backup_service.ensure_recent_backup = lambda **kwargs: (_ for _ in ()).throw(OSError("disk full"))

    res = client.post("/api/sync", json={})

    assert res.status_code == 503
    assert "synchronization was canceled" in res.json()["detail"]


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


def test_diagnostics_are_operational_and_privacy_safe(client):
    res = client.get("/api/diagnostics")
    assert res.status_code == 200
    body = res.json()
    assert body["overall"] in {"ready", "degraded", "attention"}
    assert {check["key"] for check in body["checks"]} == {"database", "storage", "disk", "backup", "mt5"}
    serialized = res.text.lower()
    assert "password" not in serialized
    assert "account_id" not in serialized


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


def test_screenshot_upload_rejects_non_png_content(client, existing_trade_id):
    payload = base64.b64encode(b"not a png").decode("ascii")
    res = client.post(
        f"/api/trades/{existing_trade_id}/screenshot",
        json={"image_base64": "data:image/png;base64," + payload},
    )
    assert res.status_code == 400


def test_live_journal_without_account(client):
    res = client.get("/api/live-journal/positions").json()
    assert res["status"] == "Configure MT5 settings first"
    assert res["positions"] == []


def test_assign_strategy_and_emotion_and_csv_export(client, existing_trade_id):
    strat = client.post("/api/strategies", json={"name": "TrendFollowing"}).json()
    strat_id = strat["id"]

    assign_res = client.post(f"/api/trades/{existing_trade_id}/assign-strategy", json={"strategy_id": strat_id})
    assert assign_res.status_code == 200
    assert assign_res.json()["ok"] is True
    assert assign_res.json()["trade"]["strategy_id"] == strat_id

    emotion_res = client.post(f"/api/trades/{existing_trade_id}/emotion", json={
        "emotion_tag": "CALM",
        "behavior_notes": "Well planned trade."
    })
    assert emotion_res.status_code == 200
    assert emotion_res.json()["ok"] is True

    behavior_res = client.post("/api/behavior/analyze")
    assert behavior_res.status_code == 200
    assert "flags" in behavior_res.json()

    csv_res = client.get("/api/trades/export-csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    assert "EURUSD" in csv_res.text


def test_report_endpoint_returns_markdown_with_evidence_and_data_quality(client, existing_trade_id):
    res = client.get("/api/report")
    assert res.status_code == 200
    body = res.json()
    assert "markdown" in body
    markdown = body["markdown"]
    assert "dataset_sha256:" in markdown
    assert "data_quality_score:" in markdown
    assert "Audit Data Quality" in markdown
    assert "Evidence Fingerprint" in markdown


def test_manual_backup_and_backups_list(client):
    initial = client.get("/api/backups")
    assert initial.status_code == 200
    assert isinstance(initial.json(), list)

    created = client.post("/api/backup")
    assert created.status_code == 200
    data = created.json()
    assert "filename" in data
    assert "path" in data

    after = client.get("/api/backups")
    assert after.status_code == 200
    backups = after.json()
    assert len(backups) >= 1
    assert backups[0]["filename"] == data["filename"]
    assert "size_bytes" in backups[0]
    assert "created_at" in backups[0]


def test_to_jsonable_path_serialization():
    from tradeaudit.webui.serialization import to_jsonable
    p = Path("some/arbitrary/path.sqlite")
    assert to_jsonable(p) == str(p)
