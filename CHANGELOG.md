# Changelog

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
