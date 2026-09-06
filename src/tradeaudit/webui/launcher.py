"""
Launches the TradeAudit web UI: a uvicorn server on a background thread,
displayed inside a native pywebview window (no browser chrome).
"""
import logging
import socket
import threading

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

    def _run_server(self) -> None:
        config = uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="warning")
        server = uvicorn.Server(config)
        server.run()

    def run(self) -> int:
        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()

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
        webview.start()
        return 0
