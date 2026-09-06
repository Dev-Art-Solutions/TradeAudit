# CLAUDE.md — TradeAudit Project Guide

TradeAudit is a desktop trading intelligence platform for **MetaTrader 5 (MT5)**. It provides automated history synchronization, trade aggregation, rigorous R-multiple risk accounting, compliance tracking, behavioral/emotional discipline analysis, quantitative research (Monte Carlo, Risk of Ruin, bootstrap intervals), Markdown/AI-ready reporting, and interactive candlestick chart replay.

---

## 🛠️ Technology Stack

- **Language & Runtime:** Python 3.11+ (Windows x64 primary target)
- **UI (default):** FastAPI local backend (127.0.0.1, token-authenticated) serving an HTML/CSS/JS frontend hosted inside a native `pywebview` window - same dark theme (`#0d1117`, `#161b22`, `#1f2937`)
- **UI (legacy):** PySide6 (Qt 6.x), still available via `python -m tradeaudit --legacy-qt` - see `docs/LEGACY_UI_STATUS.md` for current parity
- **Database & ORM:** SQLite 3 with SQLAlchemy 2.x (WAL mode, foreign keys enforced)
- **Broker & Market Integration:** MetaTrader5 Python SDK (with synthetic offline fallbacks for testing/demo)
- **Security & Credentials:** Python `keyring` backed by Windows Credential Locker
- **Distribution & Packaging:** PyInstaller (`TradeAudit.spec`), Inno Setup (`installer/TradeAudit.iss`), one-command `build.bat`, GitHub Actions CI + tag-triggered release workflow
- **Testing:** `pytest` (unit), Playwright + `pytest-playwright` (browser end-to-end against the real web UI), `pytest-qt` (legacy Qt UI only)

---

## 🏗️ Architecture & Module Structure

The project strictly follows layered architecture principles:

```text
TradeAudit/
├── installer/                   # Inno Setup Windows installer scripts and assets
├── plans/                       # Roadmap and specification documentation
├── resources/                   # Application icons, fonts, and static assets
├── scripts/                     # Automated build and packaging scripts (.ps1 / .bat)
├── src/tradeaudit/              # Core application package
│   ├── app/                     # Application lifecycle, configuration, and services
│   │   ├── config.py            # App settings, directory resolution (%LOCALAPPDATA%)
│   │   ├── exceptions.py        # Domain & infrastructure exception hierarchy
│   │   ├── logging_config.py    # Rotating file logging with sensitive data masking
│   │   └── services/            # Business & orchestration logic
│   │       ├── backup_service.py              # Automated SQLite DB backups & rotation
│   │       ├── behavior_analyzer.py          # Revenge trading, FOMO, overtrading detection
│   │       ├── breakdown_analyzer.py         # Multi-dimensional analytics (session, weekday, hour)
│   │       ├── live_position_watcher.py      # Real-time position monitor & SL/TP change tracker
│   │       ├── performance_analyzer.py       # Win rate, expectancy, net R, profit factor, DD
│   │       ├── quant_research_analyzer.py    # Monte Carlo, Risk of Ruin, Rolling metrics, Bootstrap CI
│   │       ├── report_generator.py           # Markdown & ChatGPT AI prompt generation
│   │       ├── risk_calculator.py            # Price risk, monetary risk, risk percentage
│   │       ├── rmultiple_calculator.py       # Planned R:R and Realized R engine
│   │       ├── strategy_compliance_engine.py # Rule-based strategy verification
│   │       ├── strategy_service.py           # Strategy CRUD & trade assignment
│   │       ├── strategy_trader_comparator.py # 4-quadrant Strategy vs Trader discipline analysis
│   │       ├── sync_service.py               # MT5 history synchronization & aggregation
│   │       ├── trade_aggregator.py           # Deal-to-trade grouping & scale-in / partial close logic
│   │       ├── trade_chart_service.py        # OHLC candle extraction & execution overlay assembly
│   │       └── trade_validator.py            # SL/TP direction and setup sanity checks
│   │
│   ├── domain/                  # Pure domain entities, value objects, and enums
│   │   ├── analytics.py         # PerformanceMetrics, DrawdownPoint, BreakdownSummary
│   │   ├── candles.py           # Candle, TimeFrame, TradeExecutionOverlay
│   │   ├── filters.py           # AnalysisFilter, DateRangePreset, DirectionFilter
│   │   ├── models.py            # Trade, TradeDeal, Strategy, MT5Settings, MT5AccountInfo, Emotions
│   │   ├── quant.py             # MonteCarloSimulation, RiskOfRuinResult, RollingMetricSeries
│   │   └── report.py            # AuditReport, ReportSection, PrivacyMaskingOptions
│   │
│   ├── infrastructure/          # Data persistence, security, and external MT5 SDK
│   │   ├── database/            # SQLAlchemy database engine and ORM tables
│   │   │   ├── connection.py    # DatabaseManager, session lifecycle
│   │   │   └── models.py        # Table definitions (accounts, trades, deals, events, strategies)
│   │   ├── mt5/                 # MetaTrader 5 adapters
│   │   │   ├── candle_reader.py       # Historical rates reader (copy_rates_range + fallback)
│   │   │   ├── connection_service.py  # Terminal connection & account info
│   │   │   ├── history_reader.py      # Raw deals and orders reader
│   │   │   └── position_reader.py     # Live position polling
│   │   ├── repositories/        # Repository pattern interfaces for SQLite models
│   │   │   ├── settings_repository.py
│   │   │   ├── strategy_repository.py
│   │   │   ├── trade_event_repository.py
│   │   │   └── trade_repository.py
│   │   └── security/            # Secure credential store using system keyring
│   │       └── credential_store.py
│   │
│   ├── webui/                    # Default UI: FastAPI backend + HTML/CSS/JS frontend
│   │   ├── server.py             # create_app(): all /api/* routes, token-auth middleware
│   │   ├── context.py            # AppContext: wires every service, shared by all routes
│   │   ├── launcher.py           # WebUIApplication: uvicorn thread + pywebview window + JsApi (native file dialog)
│   │   └── static/                # index.html / app.js / styles.css (vanilla JS SPA, no build step)
│   │
│   └── ui/                      # Legacy PySide6 Presentation Layer (--legacy-qt)
│       ├── main_window.py       # Main application shell and tab coordination
│       ├── dialogs/             # Modal dialogs (TradeChartDialog, StrategyDialog, etc.)
│       ├── views/               # Major tab views:
│       │   ├── dashboard_view.py          # Performance overview, KPI cards & QtCharts
│       │   ├── trades_view.py             # Aggregated trades & deals table with sync
│       │   ├── strategy_view.py           # Strategy editor & rule manager
│       │   ├── strategy_vs_trader_view.py # 4-quadrant discipline matrix & deviation cost
│       │   ├── breakdown_view.py          # Symbol, session, weekday, hour analytics
│       │   ├── live_journal_view.py       # Real-time position monitor & SL/TP modifications
│       │   ├── report_view.py             # Markdown report generation & AI prompt export
│       │   ├── quant_research_view.py     # Monte Carlo, Risk of Ruin & rolling analytics
│       │   ├── trade_chart_view.py        # Interactive candlestick chart visualizer & replay
│       │   └── settings_view.py           # MT5 connection & database backup management
│       └── widgets/             # Reusable UI widgets
│           ├── account_info_card.py
│           ├── candlestick_chart_widget.py
│           ├── charts_widget.py
│           ├── connection_status_badge.py
│           ├── filter_bar.py
│           └── kpi_card.py
│
└── tests/
    ├── unit/                     # 185 tests covering domain/services/infrastructure/webui/legacy-Qt
    └── e2e/                      # Playwright-driven browser tests against the real web UI
```

---

## ⚡ Development & Workflow Commands

### 1. Environment Setup
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .[dev]
```

### 2. Running the Application
```bash
python -m tradeaudit
```

### 3. Running Unit Tests
```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test module
pytest tests/unit/test_trade_chart_service.py
```

### 4. Building Executables & Installer (Windows)
```powershell
# Build standalone folder distribution (dist/TradeAudit/TradeAudit.exe)
.\scripts\build_exe.ps1

# Run tests, build PyInstaller binary, create .zip, and compile Inno Setup installer
.\scripts\build_installer.ps1
```

---

## 🛡️ Coding Guidelines & Principles

1. **Strict Type Safety & Immutability:** Use Python dataclasses (`@dataclass(frozen=True)` where appropriate), typed enums (`str, Enum`), and explicit type annotations on all public functions.
2. **Deterministic Risk Calculations:**
   - Always base R calculations on the **initial Stop Loss**. Never redefine initial risk after SL is trailed.
   - If a trade has no known initial SL, set realized R to `None` / `UNKNOWN`.
3. **Safe Offline & CI Testing:**
   - Services depending on MT5 must always gracefully handle MT5 unavailability by falling back to synthetic generators or mock adapters.
   - Unit tests must never require a live running MT5 terminal.
4. **Security First:**
   - Never log passwords or store credentials in plain text.
   - Account passwords must strictly be stored in Windows Credential Locker via `CredentialStore`.
   - Exported AI reports must support account number masking.
5. **UI & Theme Consistency:**
   - Adhere to the established GitHub dark mode palette: `#0d1117` (background), `#161b22` (cards/panels), `#30363d` (borders), `#58a6ff` (accents), `#26a69a` (wins/bullish), `#ef5350` (losses/bearish).

---

## 📋 Implemented Roadmap Phases

- **Phase 0:** Project Foundation, SQLite, Logging, PySide6 Shell
- **Phase 1:** MT5 Connection, Secure Credential Locker, Account Status
- **Phase 2:** MT5 History Import, Deal Aggregation, Duplicate Protection
- **Phase 3:** Risk, R-Multiple Engine (Planned R:R, Realized R, Risk %)
- **Phase 4:** Core Analytics (Win Rate, Expectancy, Profit Factor, Drawdown)
- **Phase 5:** Interactive Analysis Filters, Dashboard, QtCharts
- **Phase 6:** Strategy Management & Automated Compliance Engine
- **Phase 7:** Behavioral & Emotional Discipline Detection (Revenge, FOMO, Overtrading)
- **Phase 8:** Strategy vs Trader 4-Quadrant Analysis & Deviation Cost R
- **Phase 9:** Advanced Breakdown Analytics (Symbol, Session, Weekday, Hour, Streaks)
- **Phase 10:** Live Trade Journal & Real-Time SL/TP Modification Tracking
- **Phase 11:** Markdown & AI-Ready Export for ChatGPT Analysis
- **Phase 12:** Production Windows EXE Packaging & Inno Setup Pipeline
- **Phase 13:** Quantitative Research (Monte Carlo, Risk of Ruin, Rolling Metrics)
- **Phase 14:** Interactive Candlestick Chart Visualizer & Bar-by-Bar Trade Replay
- **Phase 15:** Chart Annotation Drawing Tools, 1-Click Screenshots & Trade Notes Review Studio
