# Changelog

## Unreleased

### Added

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
