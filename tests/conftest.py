"""
Pytest global fixtures for TradeAudit testing.
"""

import tempfile
from pathlib import Path
import pytest

from tradeaudit.app.config import Settings
from tradeaudit.infrastructure.database.connection import DatabaseManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test isolation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
        # Teardown: close logging handlers to release file handles on Windows
        from tradeaudit.app.logging import close_logging
        close_logging()


@pytest.fixture
def test_settings(temp_dir):
    """Provide isolated test settings with temporary file paths."""
    db_path = temp_dir / "test_tradeaudit.db"
    settings = Settings(
        app_name="TradeAuditTest",
        app_version="0.1.0-test",
        env="testing",
        debug=True,
        log_level="DEBUG",
        log_dir=temp_dir / "logs",
        log_file_name="test.log",
        database_url=f"sqlite:///{db_path}"
    )
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    return settings


@pytest.fixture
def test_db_manager(test_settings):
    """Provide initialized DatabaseManager backed by temp SQLite file."""
    manager = DatabaseManager(test_settings)
    manager.init_db()
    yield manager
    manager.close()


@pytest.fixture
def sample_breakdown_trades():
    """Create sample trades covering symbols, directions, times, sessions, streaks, and emotions."""
    from datetime import datetime
    from tradeaudit.domain.models import Trade

    t1 = Trade(
        id=1,
        account_id=1001,
        position_id=101,
        symbol="EURUSD",
        direction="BUY",
        open_time=datetime(2024, 1, 1, 2, 0),  # Monday 02:00 UTC (Asia)
        close_time=datetime(2024, 1, 1, 3, 0),
        profit=100.0,
        realized_r=2.0,
        status="CLOSED",
        emotion_tag="CALM"
    )

    t2 = Trade(
        id=2,
        account_id=1001,
        position_id=102,
        symbol="EURUSD",
        direction="BUY",
        open_time=datetime(2024, 1, 2, 9, 0),  # Tuesday 09:00 UTC (London)
        close_time=datetime(2024, 1, 2, 10, 0),
        profit=-50.0,
        realized_r=-1.0,
        status="CLOSED",
        emotion_tag="FOMO"
    )

    t3 = Trade(
        id=3,
        account_id=1001,
        position_id=103,
        symbol="GBPUSD",
        direction="SELL",
        open_time=datetime(2024, 1, 3, 14, 0),  # Wednesday 14:00 UTC (London, NY, Overlap)
        close_time=datetime(2024, 1, 3, 15, 0),
        profit=150.0,
        realized_r=3.0,
        status="CLOSED",
        emotion_tag="REVENGE"
    )

    t4 = Trade(
        id=4,
        account_id=1001,
        position_id=104,
        symbol="GBPUSD",
        direction="SELL",
        open_time=datetime(2024, 1, 4, 18, 0),  # Thursday 18:00 UTC (New York)
        close_time=datetime(2024, 1, 4, 19, 0),
        profit=-50.0,
        realized_r=-1.0,
        status="CLOSED",
        emotion_tag="CALM"
    )

    return [t1, t2, t3, t4]


