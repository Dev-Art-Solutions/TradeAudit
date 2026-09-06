"""
Main entry point executable for TradeAudit.
"""

import sys
from tradeaudit.app.bootstrap import bootstrap_application
from tradeaudit.webui.launcher import WebUIApplication


def main() -> int:
    """Run TradeAudit application."""
    settings, db_manager = bootstrap_application()
    app = WebUIApplication(settings=settings, db_manager=db_manager)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
