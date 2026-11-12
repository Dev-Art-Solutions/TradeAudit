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


def test_seeded_dashboard_has_portfolio_snapshot_and_accessible_nav(page, live_server, seeded_trade):
    page.goto(live_server["base_url"] + "/#dashboard")
    page.wait_for_selector("#dashboard-heading", timeout=10000)
    assert page.text_content("#dashboard-heading") == "Performance at a glance"
    assert page.is_visible(".verdict-card")
    assert page.is_visible(".quality-card")
    assert page.get_attribute('.quality-row:first-child [role="progressbar"]', "aria-valuemax") == "100"
    assert page.is_visible(".evidence-strip")
    assert page.is_enabled("#btn-export-snapshot")
    assert page.is_enabled("#btn-copy-fingerprint")
    assert page.get_attribute('[data-route="dashboard"]', "aria-current") == "page"
    assert page.title() == "Dashboard · TradeAudit"


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


def test_navigation_uses_consistent_svg_icons_and_skip_link(page, live_server):
    page.goto(live_server["base_url"] + "/#dashboard")
    page.wait_for_selector("#nav")
    assert page.locator("#nav .nav-icon").count() == 10
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.matches('.skip-link')")
    page.keyboard.press("Enter")
    assert page.evaluate("document.activeElement.id === 'content'")


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


def test_settings_exposes_runtime_diagnostics(page, live_server):
    page.goto(live_server["base_url"] + "/#settings")
    page.wait_for_selector(".diagnostics-grid", timeout=10000)
    assert page.locator(".diagnostic-check").count() == 5
    assert page.is_enabled("#btn-export-diagnostics")
    assert page.is_visible("#backup-status")
    assert page.is_enabled("#btn-backup")


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
        initial_sl=1.0967, monetary_risk=33.3, realized_r=1.5,
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


def test_trade_chart_zoom_pan_and_shape_tools(page, live_server, seeded_trade):
    page.goto(live_server["base_url"] + "/#trade-chart")
    page.wait_for_selector("#tc-trade", timeout=10000)
    page.wait_for_timeout(1000)

    canvas = page.locator("#tc-canvas")
    box = canvas.bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

    # Wheel-zoom must shrink the visible window below the full revealed range.
    full_count = page.evaluate("TC.candles.length")
    page.mouse.move(cx, cy)
    page.mouse.wheel(0, -300)
    page.wait_for_timeout(200)
    zoomed_size = page.evaluate("TC.viewSize")
    assert zoomed_size is not None and zoomed_size < full_count

    # Drag-pan must move the viewport without reopening a draw click.
    page.mouse.move(cx, cy)
    page.mouse.down()
    page.mouse.move(cx - 150, cy, steps=10)
    page.mouse.up()
    page.wait_for_timeout(200)
    assert page.evaluate("TC.viewStart") > 0

    # Fit resets both.
    page.click("#tc-fit-zoom")
    page.wait_for_timeout(200)
    assert page.evaluate("TC.viewSize") is None
    assert page.evaluate("TC.viewStart") == 0

    # Rectangle zone (two clicks) and an arrow (one click) must both persist.
    page.click('[data-draw="RECTANGLE_ZONE"]')
    page.mouse.click(box["x"] + box["width"] * 0.3, box["y"] + box["height"] * 0.3)
    page.mouse.click(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.6)
    page.wait_for_timeout(300)
    page.click('[data-draw="ARROW_UP"]')
    page.mouse.click(box["x"] + box["width"] * 0.7, box["y"] + box["height"] * 0.4)
    page.wait_for_timeout(300)
    assert page.evaluate("TC.annotations.length") == 2
    assert page.evaluate("TC.annotations.map(a => a.annotation_type)") == ["RECTANGLE_ZONE", "ARROW_UP"]


def test_trade_chart_eraser_deletes_only_the_clicked_annotation(page, live_server, seeded_trade):
    page.goto(live_server["base_url"] + "/#trade-chart")
    page.wait_for_selector("#tc-trade", timeout=10000)
    page.wait_for_timeout(1000)

    canvas = page.locator("#tc-canvas")
    box = canvas.bounding_box()
    ray_point = (box["x"] + box["width"] * 0.2, box["y"] + box["height"] * 0.3)
    arrow_point = (box["x"] + box["width"] * 0.7, box["y"] + box["height"] * 0.6)

    page.click('[data-draw="HORIZONTAL_RAY"]')
    page.mouse.click(*ray_point)
    page.wait_for_timeout(150)
    page.click('[data-draw="ARROW_DOWN"]')
    page.mouse.click(*arrow_point)
    page.wait_for_timeout(150)
    assert page.evaluate("TC.annotations.length") == 2

    # Erasing the arrow must leave the ray in place.
    page.click('[data-draw="ERASER"]')
    page.mouse.click(*arrow_point)
    page.wait_for_timeout(300)
    remaining = page.evaluate("TC.annotations.map(a => a.annotation_type)")
    assert remaining == ["HORIZONTAL_RAY"]

    # A click far from anything must not delete the survivor.
    page.mouse.click(box["x"] + box["width"] * 0.95, box["y"] + box["height"] * 0.95)
    page.wait_for_timeout(200)
    assert page.evaluate("TC.annotations.length") == 1

    # Reload to confirm the delete was persisted, not just removed client-side.
    page.reload()
    page.wait_for_selector("#tc-trade", timeout=10000)
    page.wait_for_timeout(1000)
    assert page.evaluate("TC.annotations.length") == 1


def test_trade_chart_copy_image_to_clipboard(page, live_server, seeded_trade):
    """
    The one remaining Qt-only gap in docs/LEGACY_UI_STATUS.md when this test
    was written: Qt's ChartScreenshotService can copy a QWidget.grab() to the
    OS clipboard, which doesn't apply to a browser <canvas>. This verifies a
    real image actually lands in the clipboard - not just that the button
    didn't throw.
    """
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.goto(live_server["base_url"] + "/#trade-chart")
    page.wait_for_selector("#tc-copy-clipboard", timeout=10000)
    page.wait_for_timeout(1000)

    page.click("#tc-copy-clipboard")
    page.wait_for_timeout(500)

    result = page.evaluate("""
        async () => {
            const items = await navigator.clipboard.read();
            if (!items.length || !items[0].types.includes('image/png')) return { ok: false };
            const blob = await items[0].getType('image/png');
            return { ok: true, size: blob.size };
        }
    """)
    assert result["ok"] is True
    assert result["size"] > 0


def test_trade_chart_journal_save(page, live_server, seeded_trade):
    page.goto(live_server["base_url"] + "/#trade-chart")
    page.wait_for_selector("#tj-setup", timeout=10000)
    page.fill("#tj-setup", "Test setup")
    page.select_option("#tj-rating", "B")
    page.click("#tj-save")
    page.wait_for_selector("text=Journal entry saved")


def test_trade_chart_screenshot_capture_and_gallery(page, live_server, seeded_trade):
    page.goto(live_server["base_url"] + "/#trade-chart")
    page.wait_for_selector("#tc-screenshot", timeout=10000)
    page.wait_for_selector("#tj-screenshot-gallery", state="attached")

    # Initial state
    assert "No screenshots captured yet" in page.text_content("#tj-screenshots")

    # Capture screenshot
    page.click("#tc-screenshot")
    page.wait_for_selector(".screenshot-card", timeout=10000)
    assert page.is_visible(".screenshot-thumb")

    # Open lightbox preview
    page.click(".screenshot-thumb-wrap")
    page.wait_for_selector("#screenshot-lightbox.active", timeout=5000)
    assert page.is_visible("#sl-img")

    # Close lightbox
    page.click("#sl-close")
    page.wait_for_selector("#screenshot-lightbox", state="hidden", timeout=5000)

    # Delete screenshot from gallery
    page.on("dialog", lambda dialog: dialog.accept())
    page.click(".btn-danger-subtle")
    page.wait_for_selector(".screenshot-card", state="detached", timeout=5000)
    assert "No screenshots captured yet" in page.text_content("#tj-screenshots")


def test_reports_view_generation_and_export_controls(page, live_server, seeded_trade):
    page.goto(live_server["base_url"] + "/#reports")
    page.wait_for_selector("#btn-gen-report", timeout=10000)
    page.wait_for_selector("#sel-report-depth")

    assert page.input_value("#sel-report-depth") == "Standard"
    page.select_option("#sel-report-depth", "Summary")

    page.click("#btn-gen-report")
    page.wait_for_selector("#btn-copy-prompt:not([style*='none'])", timeout=10000)
    page.wait_for_selector("#btn-copy-report:not([style*='none'])", timeout=10000)
    page.wait_for_selector("#btn-download-report:not([style*='none'])", timeout=10000)

    report_text = page.text_content("#report-box")
    assert "TradeAudit" in report_text
    assert "Executive Summary" in report_text

    # Formatted view should be visible with rendered headers
    page.wait_for_selector("#report-rendered .report-h1", timeout=5000)
    assert page.is_visible("#report-rendered")

    # Toggle to raw markdown view
    page.click("#btn-view-raw")
    page.wait_for_selector("#report-box:not([style*='none'])", timeout=5000)


def test_quant_view_monte_carlo_cone_and_confidence_intervals(page, live_server, seeded_trade):
    page.goto(live_server["base_url"] + "/#quant")
    page.wait_for_selector("#mc-cone-canvas", timeout=15000)
    assert page.is_visible("#mc-cone-canvas")
    assert page.is_visible("text=Monte Carlo Equity Simulation Envelope")
    assert page.is_visible("text=Bootstrap 95% Confidence Intervals")
    assert page.is_visible(".mc-legend")


def test_breakdowns_view_dimensions_and_hourly_chart(page, live_server, seeded_trade):
    page.goto(live_server["base_url"] + "/#breakdowns")
    page.wait_for_selector("#hourly-bar-canvas", timeout=15000)
    assert page.is_visible("#hourly-bar-canvas")
    assert page.is_visible(".bd-insights-grid")
    assert page.is_visible(".dimension-filter-bar")
    assert page.is_visible("text=By Symbol")
    assert page.is_visible("text=Contextual Trade Sequence")

    # Filter to Sequence & Streaks category
    page.click('[data-bd-cat="sequence"]')
    page.wait_for_selector(".cat-sequence", timeout=5000)
    assert page.is_visible("text=Contextual Trade Sequence")


def test_strategy_vs_trader_matrix_and_scatter_canvas(page, live_server, seeded_trade):
    page.goto(live_server["base_url"] + "/#strategy-vs-trader")
    page.wait_for_selector(".svt-matrix-container", timeout=15000)

    # Hero strip and diagnostics
    assert page.is_visible(".svt-hero-strip")
    assert page.is_visible(".svt-verdict-card")

    # Four-quadrant matrix cards
    assert page.locator(".svt-quadrant-card").count() == 4
    assert page.is_visible("text=Four-Quadrant Execution Matrix")
    assert page.is_visible("text=Good Wins")
    assert page.is_visible("text=Good Losses")
    assert page.is_visible("text=Bad Wins")
    assert page.is_visible("text=Bad Losses")

    # 2D discipline scatter plot canvas
    assert page.is_visible("#svt-scatter-canvas")
    assert page.is_visible("text=Discipline Scatter Distribution")

    # Cohort deep-dive
    assert page.is_visible(".svt-cohort-grid")
    assert page.is_visible("text=Execution Cohort Deep-Dive")

    # 1-click quadrant filter navigation to trades
    page.click(".quadrant-good-win .svt-filter-btn")
    page.wait_for_timeout(300)
    assert page.text_content("#page-title") == "Trades"


def test_live_journal_view_rendering_and_polling_controls(page, live_server, seeded_trade):
    page.goto(live_server["base_url"] + "/#live-journal")
    page.wait_for_selector("#lj-hero-strip", timeout=15000)

    # Hero KPI strip
    assert page.is_visible("#lj-hero-strip")
    assert page.is_visible("#lj-kpi-count")
    assert page.is_visible("#lj-kpi-profit")
    assert page.is_visible("#lj-kpi-volume")
    assert page.is_visible("#lj-kpi-protection")

    # Polling & auto-refresh toolbar
    assert page.is_visible("#btn-poll")
    assert page.is_visible("#lj-interval-select")
    assert page.is_visible("#lj-status")

    # Positions and events sections
    assert page.is_visible("#lj-positions-card")
    assert page.is_visible("#lj-events-section")
    assert page.is_visible("#lj-filter-all")
    assert page.is_visible("#lj-filter-sl")
    assert page.is_visible("#lj-filter-orders")

    # Trigger poll
    page.click("#btn-poll")
    page.wait_for_timeout(300)
    assert page.is_visible("#lj-last-poll")
