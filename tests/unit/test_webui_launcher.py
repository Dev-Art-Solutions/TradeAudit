"""Lifecycle tests for the native web UI launcher."""

import sys
from types import SimpleNamespace

import pytest

sys.modules.setdefault(
    "webview",
    SimpleNamespace(Window=object, OPEN_DIALOG=0, create_window=lambda **_: None, start=lambda: None),
)

from tradeaudit.webui.launcher import WebUIApplication


class _Thread:
    def __init__(self, alive: bool):
        self._alive = alive

    def is_alive(self) -> bool:
        return self._alive


def test_wait_until_ready_returns_for_started_server():
    application = WebUIApplication.__new__(WebUIApplication)
    application.server = SimpleNamespace(started=True)

    application._wait_until_ready(_Thread(alive=True), timeout=0.1)


def test_wait_until_ready_fails_when_server_thread_stops():
    application = WebUIApplication.__new__(WebUIApplication)
    application.server = None

    with pytest.raises(RuntimeError, match="stopped during startup"):
        application._wait_until_ready(_Thread(alive=False), timeout=0.1)
