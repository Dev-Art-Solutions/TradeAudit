"""
Browser-driven regression tests for the web UI, using a real Chromium instance
(pytest-playwright's `page` fixture) against a real uvicorn server. These catch
the class of bug unit tests can't: broken JS wiring, missing hashchange
handling, a form that silently fails to submit, etc. - several of which were
found and fixed by hand during development before this suite existed.
"""
from datetime import datetime, timezone

import pytest


def test_empty_dashboard_shows_onboarding_banner(page, live_server):
    page.goto(live_server["base_url"] + "/#dashboard")
    page.wait_for_selector(".onboarding-banner", timeout=10000)
    assert page.is_visible("text=Get started with TradeAudit")


def test_sidebar_navigation_updates_all_tabs(page, live_server):
    page.goto(live_server["base_url"] + "/#dashboard")
    page.wait_for_selector("#nav")
    for route, heading in [
        ("trades", "Trades"), ("strategies", "Strategies"),
        ("settings", "MT5 Settings"), ("dashboard", "Dashboard"),
    ]:
        page.click(f'[data-route="{route}"]')
        page.wait_for_timeout(200)
        assert page.text_content("#page-title") == heading


def test_hashchange_navigation_rerenders_the_view(page, live_server):
    """
    Regression test: the SPA used to only re-render on sidebar clicks, not on
    a hash change fired any other way (e.g. page.goto to a different #route
    on an already-loaded page). Without a hashchange listener, this leaves
    the previous view's content on screen under the new page title.
    """
    page.goto(live_server["base_url"] + "/#dashboard")
    page.wait_for_selector("#nav")
    page.goto(live_server["base_url"] + "/#settings")
    page.wait_for_timeout(300)
    assert page.text_content("#page-title") == "MT5 Settings"
    assert page.is_visible("#f-login")


def test_settings_save_round_trip(page, live_server):
    page.goto(live_server["base_url"] + "/#settings")
    page.wait_for_selector("#f-login")
    page.fill("#f-login", "555444")
    page.fill("#f-server", "Example-Server")
    page.click("#btn-save")
    page.wait_for_selector("text=Settings saved successfully")

    page.reload()
    page.wait_for_selector("#f-login")
    assert page.input_value("#f-login") == "555444"
    assert page.input_value("#f-server") == "Example-Server"


def test_connect_without_mt5_shows_clean_error_not_a_crash(page, live_server):
    # If the MetaTrader5 package happens to be installed (e.g. a dev machine
    # that's also used for live-account testing), mt5.initialize() against a
    # bogus server can take well over a minute to time out for real before
    # surfacing as a clean error - this must never crash regardless of how
    # long it takes, so the wait here is deliberately generous.
    page.goto(live_server["base_url"] + "/#settings")
    page.wait_for_selector("#f-login")
    page.fill("#f-login", "12345")
    page.fill("#f-server", "Demo-Server")
    page.fill("#f-password", "x")
    page.click("#btn-connect")
    page.wait_for_selector("#settings-banner.error", timeout=90000)
    assert "Connection failed" in page.text_content("#settings-banner")


def test_sync_without_saved_account_shows_warning(page, live_server):
    page.goto(live_server["base_url"] + "/#trades")
    page.wait_for_selector("#btn-sync")
    page.click("#btn-sync")
    page.wait_for_selector("text=Configure MT5 account settings first", timeout=10000)


def test_browse_button_shows_desktop_only_fallback_in_plain_browser(page, live_server):
    page.goto(live_server["base_url"] + "/#settings")
    page.wait_for_selector("#btn-browse-path")
    page.click("#btn-browse-path")
    page.wait_for_selector("text=only works inside the TradeAudit desktop app")


@pytest.fixture
def seeded_trade(live_server):
    from tradeaudit.domain.models import Trade
    trade = Trade(
        account_id=777, position_id=1, symbol="EURUSD", direction="BUY",
        open_time=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        open_price=1.1000, close_price=1.1050, status="CLOSED", profit=50.0,
    )
    saved = live_server["ctx"].trade_repo.save_trades(777, [trade])
    live_server["ctx"].settings_repo.save_mt5_settings(
        __import__("tradeaudit.domain.models", fromlist=["MT5Settings"]).MT5Settings(login=777, server="Seed-Server")
    )
    return saved[0].id


def test_trade_chart_replay_and_drawing(page, live_server, seeded_trade):
    page.goto(live_server["base_url"] + "/#trade-chart")
    page.wait_for_selector("#tc-trade", timeout=10000)
    page.wait_for_timeout(1000)  # candle fetch (synthetic fallback, no MT5 needed)

    page.click("#tc-reset")
    page.wait_for_timeout(200)
    before = page.text_content("#tc-overlay")
    page.click("#tc-step-fwd")
    page.wait_for_timeout(200)
    after = page.text_content("#tc-overlay")
    assert before != after  # bar count must have advanced

    page.click('[data-draw="TREND_LINE"]')
    canvas = page.locator("#tc-canvas")
    box = canvas.bounding_box()
    page.mouse.click(box["x"] + box["width"] * 0.2, box["y"] + box["height"] * 0.6)
    page.mouse.click(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.3)
    page.wait_for_timeout(500)

    # Reload and confirm the annotation persisted server-side, not just in memory.
    page.reload()
    page.wait_for_selector("#tc-trade", timeout=10000)
    page.wait_for_timeout(1000)
    annotation_count = page.evaluate("TC.annotations.length")
    assert annotation_count >= 1


def test_trade_chart_journal_save(page, live_server, seeded_trade):
    page.goto(live_server["base_url"] + "/#trade-chart")
    page.wait_for_selector("#tj-setup", timeout=10000)
    page.fill("#tj-setup", "Test setup")
    page.select_option("#tj-rating", "B")
    page.click("#tj-save")
    page.wait_for_selector("text=Journal entry saved")
