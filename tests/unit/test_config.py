"""
Unit tests for configuration loading.
"""

from tradeaudit.app.config import Settings, get_settings


def test_settings_default_values():
    settings = Settings()
    assert settings.app_name == "TradeAudit"
    assert settings.app_version == "1.1.0"
    assert "sqlite" in settings.database_url


def test_get_settings_creates_log_dir(test_settings):
    assert test_settings.log_dir.exists()
