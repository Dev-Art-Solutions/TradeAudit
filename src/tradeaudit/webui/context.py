"""
Application service wiring for the web UI - mirrors the dependency graph
previously assembled in ui/main_window.py, minus anything Qt-specific.
"""
from tradeaudit.app.config import Settings
from tradeaudit.infrastructure.database.connection import DatabaseManager
from tradeaudit.infrastructure.security.credential_store import CredentialStore
from tradeaudit.infrastructure.repositories.settings_repository import SettingsRepository
from tradeaudit.infrastructure.repositories.trade_repository import TradeRepository
from tradeaudit.infrastructure.repositories.strategy_repository import StrategyRepository
from tradeaudit.infrastructure.repositories.trade_event_repository import TradeEventRepository
from tradeaudit.infrastructure.mt5.connection_service import MT5ConnectionService
from tradeaudit.infrastructure.mt5.candle_reader import MT5CandleReader
from tradeaudit.app.services.sync_service import SyncService
from tradeaudit.app.services.strategy_service import StrategyService
from tradeaudit.app.services.live_position_watcher import LivePositionWatcherService
from tradeaudit.app.services.backup_service import BackupService
from tradeaudit.app.services.trade_chart_service import TradeChartService
from tradeaudit.app.services.quant_research_analyzer import QuantResearchAnalyzer
from tradeaudit.app.services.report_generator import MarkdownReportGenerator


class AppContext:
    """Holds every long-lived service instance used by the API layer."""

    def __init__(self, settings: Settings, db_manager: DatabaseManager):
        self.settings = settings
        self.db_manager = db_manager

        self.mt5_service = MT5ConnectionService()
        self.credential_store = CredentialStore()
        self.settings_repo = SettingsRepository(db_manager)
        self.trade_repo = TradeRepository(db_manager)
        self.strategy_repo = StrategyRepository(db_manager)
        self.trade_event_repo = TradeEventRepository(db_manager)

        self.strategy_service = StrategyService(self.strategy_repo, self.trade_repo)
        self.sync_service = SyncService(trade_repo=self.trade_repo)
        self.live_watcher_service = LivePositionWatcherService(
            event_repository=self.trade_event_repo,
            sync_service=self.sync_service
        )
        self.backup_service = BackupService(settings=settings, db_manager=db_manager)
        self.candle_reader = MT5CandleReader(connection_service=self.mt5_service)
        self.trade_chart_service = TradeChartService(
            candle_reader=self.candle_reader,
            trade_event_repository=self.trade_event_repo
        )
        self.quant_analyzer = QuantResearchAnalyzer()
        self.report_generator = MarkdownReportGenerator(app_version=settings.app_version)

    def current_login(self) -> int:
        saved = self.settings_repo.load_mt5_settings()
        return saved.login if saved and saved.login else 0
