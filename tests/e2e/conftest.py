"""
Fixtures for browser-driven end-to-end tests of the web UI. Spins up a real
uvicorn server (the same FastAPI app the packaged app serves) on a background
thread against an isolated temp SQLite database, and hands tests its base URL.
"""
import os
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn

from tradeaudit.infrastructure.database.connection import DatabaseManager
from tradeaudit.webui.context import AppContext
from tradeaudit.webui.server import create_app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_server(tmp_path: Path, monkeypatch):
    # Settings.log_dir is a computed property (data_dir / "logs"), so passing
    # log_dir= to the constructor is silently ignored - env vars are the only
    # reliable way to fully isolate a Settings instance for a test.
    monkeypatch.setenv("TRADEAUDIT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TRADEAUDIT_DATABASE_URL", f"sqlite:///{tmp_path / 'e2e.db'}")
    monkeypatch.setenv("TRADEAUDIT_ENV", "development")

    from tradeaudit.app.config import Settings
    settings = Settings()
    settings.ensure_directories()

    db_manager = DatabaseManager(settings)
    db_manager.init_db()
    ctx = AppContext(settings=settings, db_manager=db_manager)
    app = create_app(ctx)

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10
    while not getattr(server, "started", False) and time.time() < deadline:
        time.sleep(0.05)

    yield {"base_url": f"http://127.0.0.1:{port}", "ctx": ctx}

    server.should_exit = True
    thread.join(timeout=5)
