"""
Application bootstrap orchestrator.
"""

import logging
from typing import Tuple

from tradeaudit.app.config import get_settings, Settings
from tradeaudit.app.logging import setup_logging
from tradeaudit.app.exceptions import install_global_exception_handler
from tradeaudit.infrastructure.database.connection import DatabaseManager

logger = logging.getLogger("tradeaudit.bootstrap")


def bootstrap_application() -> Tuple[Settings, DatabaseManager]:
    """Execute complete application initialization sequence."""
    # 1. Install global exception hook
    install_global_exception_handler()

    # 2. Load configuration settings
    settings = get_settings()

    # 3. Setup console & file logging
    setup_logging(settings)

    logger.info("Initializing %s version %s...", settings.app_name, settings.app_version)

    # 4. Initialize Database connection and tables
    db_manager = DatabaseManager(settings)
    db_manager.init_db()
    if not db_manager.check_integrity():
        db_manager.close()
        raise RuntimeError(
            "TradeAudit database integrity check failed. Preserve the database file and restore a known-good backup."
        )

    logger.info("Bootstrap complete.")
    return settings, db_manager
