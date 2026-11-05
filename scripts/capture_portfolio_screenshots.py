"""Capture privacy-safe portfolio screenshots from deterministic synthetic trades."""

from __future__ import annotations

import argparse
import random
import socket
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright

from tradeaudit.app.config import Settings
from tradeaudit.domain.models import MT5Settings, Trade
from tradeaudit.infrastructure.database.connection import DatabaseManager
from tradeaudit.webui.context import AppContext
from tradeaudit.webui.server import create_app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _demo_trades(account_id: int, count: int = 180) -> list[Trade]:
    rng = random.Random(20261031)
    start = datetime(2025, 1, 6, 8, 0, tzinfo=timezone.utc)
    symbols = ("EURUSD", "GBPUSD", "USDJPY", "XAUUSD")
    trades: list[Trade] = []
    for index in range(count):
        is_win = index % 5 in (0, 1, 3)
        realized_r = round(rng.uniform(1.2, 2.8), 2) if is_win else -1.0
        open_time = start + timedelta(hours=index * 9)
        trades.append(
            Trade(
                account_id=account_id,
                position_id=100_000 + index,
                symbol=symbols[index % len(symbols)],
                direction="BUY" if index % 2 == 0 else "SELL",
                volume=0.1,
                open_time=open_time,
                close_time=open_time + timedelta(minutes=45 + index % 90),
                open_price=1.1,
                close_price=1.101 if is_win else 1.0995,
                initial_sl=1.099,
                initial_tp=1.102,
                profit=realized_r * 100,
                monetary_risk=100,
                realized_r=realized_r,
                status="CLOSED",
                compliance_status="COMPLIANT" if index % 7 else "DEVIATION",
                emotion_tag="CALM" if index % 6 else "FOMO",
            )
        )
    return trades


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tradeaudit-portfolio-") as tmp:
        data_dir = Path(tmp)
        settings = Settings(
            env="testing",
            debug=False,
            data_dir=data_dir,
            database_url=f"sqlite:///{data_dir / 'portfolio.db'}",
        )
        settings.ensure_directories()
        database = DatabaseManager(settings)
        database.init_db()
        context = AppContext(settings=settings, db_manager=database)
        account_id = 424_242
        context.trade_repo.save_trades(account_id, _demo_trades(account_id))
        context.settings_repo.save_mt5_settings(MT5Settings(login=account_id, server="Portfolio-Demo"))

        port = _free_port()
        server = uvicorn.Server(
            uvicorn.Config(create_app(context), host="127.0.0.1", port=port, log_level="warning")
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        if not server.started:
            raise RuntimeError("Screenshot server failed to start.")

        dashboard = output_dir / "01-dashboard.png"
        diagnostics = output_dir / "06-system-health.png"
        evidence = output_dir / "07-audit-evidence.png"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(
                    viewport={"width": 1440, "height": 1000},
                    device_scale_factor=2,
                )
                page.goto(f"http://127.0.0.1:{port}/#dashboard")
                page.wait_for_selector("#dashboard-heading", timeout=15_000)
                page.wait_for_timeout(500)
                page.screenshot(path=str(dashboard), full_page=False)
                page.locator(".evidence-strip").scroll_into_view_if_needed()
                page.wait_for_timeout(300)
                page.screenshot(path=str(evidence), full_page=False)
                page.goto(f"http://127.0.0.1:{port}/#settings")
                page.wait_for_selector(".diagnostics-grid", timeout=15_000)
                # Keep the committed portfolio image reproducible and free of
                # workstation-specific temp paths / volatile disk figures.
                page.locator(".card").nth(1).locator(".kpi-sub").evaluate(
                    "el => el.innerHTML = 'Data Directory: <span class=\"mono\">%LOCALAPPDATA%\\\\TradeAudit</span><br>' +"
                    "'Database: <span class=\"mono\">sqlite:///.../tradeaudit.db</span><br>' +"
                    "'Protection policy: automatic pre-sync snapshot (at most once per 24h), retaining the latest 10 backups.'"
                )
                page.locator(".diagnostic-check", has_text="Free disk space").locator("small").evaluate(
                    "el => el.textContent = 'Healthy storage headroom available.'"
                )
                page.locator(".diagnostics-grid").scroll_into_view_if_needed()
                page.wait_for_timeout(300)
                page.screenshot(path=str(diagnostics), full_page=False)
                browser.close()
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            database.close()
        return [dashboard, diagnostics, evidence]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/images"))
    args = parser.parse_args()
    screenshots = capture(args.output_dir.resolve())
    for screenshot in screenshots:
        print(f"Captured {screenshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
