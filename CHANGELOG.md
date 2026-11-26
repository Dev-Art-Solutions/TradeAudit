# Changelog

## Unreleased

### Added

- Drawdown Duration Horizon analytics (`max_drawdown_duration_trades` and `max_drawdown_duration_days`) in `PerformanceAnalyzer` and Dashboard KPI cards tracking the maximum number of consecutive trades and calendar days spent underwater before setting a new equity high.

- Multi-format Filtered Trade History Export (CSV & JSON) supporting active client and server-side filtration by Symbol, Direction, Outcome, Strategy, and Compliance status with enriched trade metadata including holding duration, net profit, fees, and strategy naming.

- Quantitative Risk Research & Capital Preservation section (Sharpe, Sortino, Calmar, VaR 95%, CVaR 95%, Kelly Criterion, and Risk of Ruin Sensitivity Matrix) integrated directly into generated Markdown audit reports and HTML dossiers.
- Holding Duration Horizon (`by_duration`) and Strategy Assignment (`by_strategy`) breakdown tables integrated into Markdown and HTML export reports.

- Multi-tier Holding Duration Breakdown dimension (`by_duration`) in `BreakdownAnalyzer` and Breakdowns view (`#breakdowns`) categorizing trades across Scalp (< 5m), Intraday (5m-1h, 1h-4h), Session (4h-24h), and Swing (> 24h) horizons with dedicated category filtering, win rates, expectancies, and an Optimal Holding Time hero insight card.

- Risk of Ruin Sensitivity Matrix & Capital Preservation Table (`#quant-ror-matrix-card`) in Quant & Risk (`#quant`) simulating Brownian continuous diffusion ruin probabilities across varying position risk allocations (0.5% to 3.0%) and drawdown limits (10% to 50%), featuring consecutive loss buffers, Capital Preservation Resilience Score (`#quant-resilience-badge`), and optimal risk allocation recommendations.
- Trade Lifecycle Exit Quality classification and 1-Click Markdown Trade Card export (`#drawer-btn-copy-card`) in the Trade Inspection Drawer, providing full target capture, early exit, standard stop, and wide deviation feedback with instant clipboard copy for journaling.

- Real-Time Risk Exposure & Margin Safety Hub (`#lj-risk-hub`) in Live Journal (`#live-journal`) computing aggregate Downside Risk at hard Stop-Loss (in price points), aggregate Upside Target Potential at Take-Profit, portfolio-wide Planned Reward:Risk ratio, and Net Market Directional Bias (Long vs Short volume weighting).
- Open Exposure & Instrument Concentration Radar (`#lj-allocation-card`) in Live Journal aggregating active positions by instrument with volume distribution percentage progress bars, net lots direction badges, floating P/L, and Stop-Loss safety protection indicators.
- Individual position Risk and Planned R:R metrics column in the Live Journal MT5 positions ledger showing point distance to SL/TP and setup R:R skew with uncapped risk alerts on missing Stop-Losses.
- One-click Live Portfolio Snapshot clipboard export button (`#btn-copy-live-summary`) generating structured markdown summaries of open orders, floating P/L, exposure volume, and protection status with interactive toast feedback.
- One-click Quick Preset Filter Pills (`#trades-quick-filters`) on the Trades ledger (`#trades`) enabling instant 1-click triage for All Trades, Winners 🟢, Losers 🔴, Rule Violations ⚠️, Compliant 🎯, and Emotional/Tilt Trades ⚡ with automatic dropdown synchronization.
- Backend live positions summary metadata in `GET /api/live-journal/positions` returning real-time count, total profit, swap, volume, and unprotected order metrics.

- Multi-dimensional Strategy Breakdown dimension (`by_strategy`) in `BreakdownAnalyzer` and Breakdowns view (`#breakdowns`) computing complete performance metrics per strategy and unassigned positions, accompanied by a Top Strategy Edge hero insight card and category filter toggle.
- Trade Setup Pattern tagging and 5-Star Execution Quality Rating review (`#drawer-setup-input`, `#drawer-rating-select`) in the Trade Inspection Drawer with seamless saving to trade journal records and integration into external AI audit prompt generation.
- Institutional Risk-Adjusted Performance Ratios suite in Quant & Risk (`#quant`) computing R-multiple Sharpe Ratio, downside-volatility Sortino Ratio, Calmar Ratio (Net R / Max Drawdown R), and mathematical Kelly Criterion / Half-Kelly optimal capital allocation.
- Interactive Rolling Window Edge & Expectancy Progression Canvas (`#rolling-edge-canvas`) plotting sliding window expectancy evolution across trade history with zero baseline, positive/negative shaded bands, crosshair tooltips, and 20/50/100 trade window switcher.
- Global Trading Sessions Performance Matrix and live market clock hub in the Breakdowns view (`#breakdowns`) covering Asia, London, New York, London/NY Overlap, and Off-Hours sessions with real-time active indicators, win rates, net P/L, expectancy R, and 1-click drill-down filtering to the trades ledger.
- Single-trade AI Audit Prompt generator button (`#drawer-btn-copy-ai-prompt`) in the Trade Inspection Drawer, synthesizing structured MT5 order data, lifecycle SL modifications, rule compliance, and emotion tags for instant external LLM analysis.
- Trade holding duration formatting and planned vs. realized R:R capture efficiency indicators in the Trade Inspection Drawer execution section.
- What-If "Discipline Edge" cumulative equity curves in Strategy vs Trader (`#svt-equity-canvas`) contrasting Actual Realized trajectory against Compliant Rule-Strict and No-Bad-Losses counterfactuals.
- Discipline Alpha quantification measuring the recoverable net R and monetary gain achievable by eliminating Quadrant IV unforced errors.
- Time-series trajectory generation in `StrategyTraderComparator` tracking actual, compliant, and no-bad-losses cumulative R curves step-by-step.
- Interactive crosshair tooltips on the What-If equity curves showing trade-by-trade R comparisons on hover.
- Interactive period, symbol, and strategy filtering toolbar on the Dashboard with quick preset pills (All Time, This Month, Last Month, This Week, Today) and live trade volume counters.
- Advanced risk, payout, and directional breakdown metrics on the Dashboard: Win/Loss monetary payout ratio, largest winning trade, largest losing trade, and Long vs. Short execution win rates.
- Multi-dimensional query parameter support in `GET /api/dashboard` (`period`, `symbol`, `strategy_id`, `custom_start`, `custom_end`) backed by `AnalysisFilter` and `FilterEvaluator`.
- One-click "Today" / current month calendar jump button (`#cal-btn-today`) and dynamic month synchronization in the interactive Trading Calendar.
- Interactive Monte Carlo scenario stress-testing control bar in Quant & Risk supporting customizable horizon, ruin/DD threshold, profit target goal, and sampling methodology (Bootstrap vs. Shuffle).
- One-click scenario presets: Prop Firm Evaluation (10R DD / 10R Target), Conservative Risk Preservation (5R DD / 15R Target), and Aggressive Growth (15R DD / 30R Target).
- Institutional tail risk analytics suite computing historical non-parametric Value at Risk (95% & 99% VaR) and Expected Shortfall (95% & 99% CVaR).
- Parameterized `/api/quant` endpoint with validation constraints and multi-scenario caching.
- Batch trade editing suite in the Trades ledger with multi-selection checkboxes, select-all toggle, and floating bulk action toolbar.
- Bulk strategy assignment and automatic compliance re-evaluation endpoint (`POST /api/trades/bulk-update`) processing batch updates in a single atomic transaction.
- Bulk emotion tagging and unassignment controls allowing traders to rapidly journal multiple trades simultaneously.
- AI Report Persona selection in the audit dossier generator with three specialized evaluation frameworks: Quant & Risk Officer (`quant`), Prop Firm Auditor (`prop_firm`), and Psychology Coach (`psychology`).
- Standalone HTML dossier export (`GET /api/report/export-html`) with embedded dark theme styles, formatted tables, metric cards, and `@media print` layout.
- Native browser print and PDF export button in AI Reports providing zero-dependency clean document printing without sidebars or toolbars.

- Audit Data Quality scoring across risk, stop-loss, strategy-compliance, timing, and trader-review evidence.
- Prioritized dashboard recommendations for incomplete datasets.
- Unit and browser regression coverage for the new quality contract and visualization.
- Privacy-safe runtime diagnostics covering database, storage, disk, backups, and the MT5 adapter.
- An in-app operational readiness panel and downloadable diagnostics snapshot for support workflows.
- Versioned audit evidence snapshots with deterministic SHA-256 dataset fingerprints and no account identifiers.
- Verifiable dataset fingerprint and audit data quality scoring embedded into generated Markdown reports.
- One-click copy interaction and visual indicator for the audit evidence SHA-256 fingerprint on the dashboard.
- Automatic pre-sync SQLite safety snapshots with 24-hour throttling, ten-backup retention, and fail-closed synchronization.
- Backup inventory listing endpoint with live metadata and size tracking in settings.
- Robust Path serialization support in API serialization utilities.
- Configurable report depth selection (Summary, Standard, Full with trade ledger) and direct Markdown file download in the AI Reports tab.
- Trade chart screenshot serving endpoint (`GET /api/screenshots/{filename}`) with token query validation, strict path traversal safeguards, and PNG verification.
- Trade journal screenshot detachment workflow and secure deletion endpoint (`DELETE /api/trades/{trade_id}/screenshots/{filename}`).
- Interactive screenshot gallery, thumbnail cards, and full-resolution lightbox modal preview in the Trade Chart journal.
- Interactive HTML rendering and view mode toggle (Formatted View vs. Raw Markdown) for AI audit reports.
- One-click "Copy AI Prompt" button extracting tailored system prompts and targeted questions for ChatGPT and Claude.
- Scoped report filtering by trading period, symbol, and configurable privacy/anonymization toggles in the AI Reports tab.
- Monte Carlo equity simulation envelope cone chart displaying 5th, 25th, 50th median, 75th, and 95th percentiles with high-DPI canvas rendering.
- Bootstrap 95% Confidence Intervals display exposing empirical win rate, expectancy, profit factor, and average R bounds alongside statistical significance indicators.
- Tail risk stress testing metrics covering 95th-percentile consecutive loss streaks, max drawdown, and target achievement probability in Quant & Risk.
- Unit and browser E2E test coverage for `/api/quant` calculations, Monte Carlo visualizations, and confidence interval metrics.
- Multi-dimensional breakdown analytics suite exposing all 8 dimensions: Symbol, Direction, Session, Weekday, Hourly, Contextual Sequence (Post-Win vs Post-Loss), Streaks, and Emotion.
- Hourly distribution visual bar chart plotting net P/L and trade frequency across the 24-hour UTC cycle.
- Key breakdown insights hero strip highlighting top instrument, optimal session, peak weekday, and post-loss revenge drag indicators.
- Category navigation filter and visual win rate mini progress bars across breakdown tables.
- Unit and browser E2E test coverage for `/api/breakdown` multi-dimensional calculations and interactive views.
- Interactive Four-Quadrant Execution Matrix in "Strategy vs Trader" contrasting Process Adherence (Rules Followed vs Broken) against Market Outcome (Profit vs Loss) with Good Wins, Good Losses, Bad Wins, and Bad Losses cards.
- Interactive 2D Discipline Scatter Plot canvas displaying trades in the Realized R vs Process Adherence plane with quadrant zones, zero baseline crosshairs, and hover tooltips.
- Hero discipline strip with adherence score progress bar, deviation capital leak quantification (in R and monetary), bad losses drag, and quality diagnosis verdicts.
- Execution cohort deep-dive comparison cards contrasting Compliant (Strategy Edge), Deviation (Discipline Leaks), and Emotional (Psychological Drag) trades.
- 1-click quadrant filter navigation enabling instant drill-down from matrix cells to filtered trades in the ledger.
- Unit and Playwright browser E2E test coverage for `/api/strategy-vs-trader` endpoint metrics, matrix rendering, and drill-down interactions.
- Real-time Portfolio & Exposure hero strip in Live Journal tracking open position count, net floating P/L, lot exposure (long vs short), and Stop-Loss safety alerts.
- Live position monitoring table with dynamic SL protection badges, pip distance metrics, take-profit levels, and financing fees.
- Configurable auto-refresh interval selector (Manual, 5s, 10s, 30s) with active polling timer lifecycle management and pulsing beacon indicator.
- Live lifecycle audit event ledger and behavioral alerts tracking trailing Stop-Loss moves, partial closes, and red-flag SL-widening violations.
- Server-side persistence and delivery of recent trade lifecycle events even during disconnected terminal sessions.
- Unit and Playwright browser E2E test coverage for `/api/live-journal/positions` endpoints, hero metrics, and polling controls.
- Strategy portfolio summary hero strip in Strategies view showing active strategy count, overall compliance discipline rate %, total realized profit, and total net R.
- Interactive strategy rule preset quick-loader with 4 preconfigured rule sets: Trend Following, Day Trading Reversal, Scalp Momentum, and Prop Firm Strict Rules.
- Allowed trading sessions multi-select checklist (Asia, London, New York) and comma-separated allowed symbols input in strategy rule configuration.
- Real-time strategy performance metrics cards on each strategy detailing trade volume, win rate %, realized profit, net R, and adherence rate with 1-click drill-down filtering to the trade ledger.
- Unit and Playwright browser E2E test coverage for strategy rule presets, session/symbol persistence, and UI strategy creation flows.
- Interactive Trading Calendar and Daily P&L Heatmap on the Dashboard with month navigation, profitable day ratio, and 1-click date drill-down to the trade ledger.
- Toggle between currency ($ P/L) and risk-adjusted units (R-Multiple) across calendar days.
- Underwater Drawdown (R) equity curve visualization with crimson depth gradient and high-water mark recovery tracking.
- Aggregate daily summary engine in `/api/dashboard` computing daily trade frequency, win/loss rates, net monetary outcome, and realized R.
- Unit and Playwright browser E2E test coverage for dashboard daily summaries, calendar interactions, and underwater drawdown rendering.
- Slide-over Trade Inspection Drawer in the Trade Ledger revealing deep execution pricing, duration, risk analysis, rule compliance evaluation, and MT5 deals.
- Position lifecycle modification timeline in the trade drawer showing historical trailing Stop-Loss and Take-Profit adjustments.
- In-drawer trade reflection notes editor with real-time persistence to behavioral journal storage.
- Direct jump button from the inspection drawer into interactive candlestick chart replay.
- Unit and Playwright browser E2E test coverage for trade detail inspection, lifecycle history, and drawer workflows.

## 1.1.1 — 2026-10-27

- Grant the GitHub release workflow permission to publish binary assets.

## 1.1.0 — 2026-10-27

### Added

- Recovery factor based on net profit divided by absolute maximum monetary drawdown.
- Average and median closed-trade duration with data-completeness counts.
- Explicit bootstrap-with-replacement and shuffle-without-replacement Monte Carlo modes.
- Simulation horizon, sampling method and model-assumption metadata in quantitative results.
- SHA-256 checksum manifest in tagged GitHub releases.
- Release gap audit covering analytics, persistence, packaging and public-launch risks.

### Changed

- Replaced unconditional “Guaranteed Ruin” language with a qualified critical-risk estimate.
- Dashboard and Markdown report now expose recovery and duration metrics.

### Known limitations

- MAE/MFE is not reported until traceable candle/tick coverage and approximation metadata are persisted.
- Risk-of-ruin results assume representative, stationary R-multiples and do not establish future outcomes.
- `risk_per_trade_pct` is informational while drawdown tolerance is expressed in R.
- Trade-history resampling is not a strategy backtest and does not model changing regimes or clustered trades.
