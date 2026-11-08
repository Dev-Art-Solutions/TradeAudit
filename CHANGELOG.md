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
