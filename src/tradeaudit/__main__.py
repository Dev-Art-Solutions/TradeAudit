"""
Main entry point executable for TradeAudit.
"""

import sys
from tradeaudit.app.bootstrap import bootstrap_application


def main() -> int:
    """Run TradeAudit application."""
    settings, db_manager = bootstrap_application()

    if "--legacy-qt" in sys.argv:
        from tradeaudit.ui.app import TradeAuditApplication
        app = TradeAuditApplication(settings=settings, db_manager=db_manager)
        return app.run()

    from tradeaudit.webui.launcher import WebUIApplication
    app = WebUIApplication(settings=settings, db_manager=db_manager)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
