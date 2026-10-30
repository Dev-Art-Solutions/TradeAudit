"""
Launches the TradeAudit web UI: a uvicorn server on a background thread,
displayed inside a native pywebview window (no browser chrome).
"""
import logging
import socket
import threading
import time

import uvicorn
import webview

from tradeaudit.app.config import Settings, get_resource_path
from tradeaudit.infrastructure.database.connection import DatabaseManager
from tradeaudit.webui.context import AppContext
from tradeaudit.webui.server import create_app

logger = logging.getLogger("tradeaudit.webui.launcher")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class JsApi:
    """
    Methods exposed to the frontend as window.pywebview.api.* - used for things a
    web page can't do on its own, like opening a native "pick a file" dialog.
    """

    def __init__(self):
        self.window: "webview.Window | None" = None

    def browse_mt5_path(self):
        """Open a native file picker for the MT5 terminal executable."""
        if self.window is None:
            return None
        result = self.window.create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=("Executable Files (*.exe)", "All files (*.*)"),
        )
        return result[0] if result else None


class WebUIApplication:
    """Owns the FastAPI server thread and the pywebview window."""

    def __init__(self, settings: Settings, db_manager: DatabaseManager):
        self.settings = settings
        self.db_manager = db_manager
        self.ctx = AppContext(settings=settings, db_manager=db_manager)
        self.app = create_app(self.ctx)
        self.port = _free_port()
        self.server: "uvicorn.Server | None" = None

    def _run_server(self) -> None:
        config = uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.server.run()

    def _wait_until_ready(self, server_thread: threading.Thread, timeout: float = 10.0) -> None:
        """Do not open the desktop shell until Uvicorn can actually serve it."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.server is not None and self.server.started:
                return
            if not server_thread.is_alive():
                raise RuntimeError("TradeAudit local server stopped during startup.")
            time.sleep(0.05)
        raise RuntimeError("TradeAudit local server did not become ready within 10 seconds.")

    def run(self) -> int:
        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()
        self._wait_until_ready(server_thread)

        icon_path = get_resource_path("resources/icons/tradeaudit.ico")
        js_api = JsApi()
        window_kwargs = dict(
            title=f"{self.settings.app_name} v{self.settings.app_version}",
            url=f"http://127.0.0.1:{self.port}/",
            width=1400,
            height=900,
            min_size=(1000, 650),
            js_api=js_api,
        )

        js_api.window = webview.create_window(**window_kwargs)
        logger.info("Starting TradeAudit web UI on http://127.0.0.1:%s/", self.port)
        try:
            webview.start()
            return 0
        finally:
            logger.info("Stopping TradeAudit web UI")
            if self.server is not None:
                self.server.should_exit = True
            server_thread.join(timeout=5)
            if server_thread.is_alive():
                logger.warning("Local server did not stop within the shutdown timeout")
            self.ctx.mt5_service.disconnect()
            self.db_manager.close()
