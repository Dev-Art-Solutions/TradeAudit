# Legacy Qt UI Status

TradeAudit shipped its first several development phases on a PySide6 (Qt6)
desktop UI. It has since been replaced as the default UI by a local web UI
(FastAPI backend + HTML/CSS/JS frontend, hosted in a `pywebview` window) —
see the main [README](../README.md) for why. The Qt UI is still in the
repository and still runs via `python -m tradeaudit --legacy-qt`.

This document tracks feature parity between the two, so it's clear what
using `--legacy-qt` actually buys you today.

## Shared, unaffected by the UI choice

Everything below lives in `src/tradeaudit/app/`, `domain/`, and
`infrastructure/` and is identical regardless of which UI calls it: MT5
sync, trade aggregation, R-multiple/risk calculations, the strategy
compliance engine, behavioral analysis, breakdown analytics, Monte
Carlo / Risk of Ruin / rolling metrics, Markdown report generation, and
all repository/database code. Neither UI has its own copy of any of this —
a bug fixed once is fixed for both.

## Available in both UIs

- Dashboard (KPIs, cumulative R / P&L curves, drawdown, streaks)
- Trades table with MT5 sync
- Strategy management (create/edit/delete, compliance rules)
- Strategy vs Trader four-quadrant analysis
- Breakdowns (symbol, direction, session, weekday, hour, streak, emotion)
- Live Journal (open position polling, SL/TP modification history)
- AI-ready Markdown report generation with clipboard copy
- Quant & Risk (Monte Carlo, Risk of Ruin, rolling window stability)
- Trade Chart: candlestick rendering, bar-by-bar replay with speed control,
  all six annotation types (trendline, horizontal ray, rectangle zone,
  arrow up/down, text note) with a click-to-erase eraser tool for
  removing one at a time, scroll-to-zoom and drag-to-pan, 1-click
  screenshot with a separate "Copy Image" to clipboard, and a trade
  journal (setup name, grade, thesis, review, lessons learned)

## Qt-only (not yet ported to the web UI)

None remaining. The three gaps this document used to track (annotation
tool coverage, chart zoom/pan, and per-annotation erase) have all closed —
see "Is removing Qt safe right now?" below.

## Web-UI-only

- Native file-picker "Browse…" for the MT5 terminal path (`pywebview`
  `create_file_dialog`), replacing Qt's `QFileDialog` with a fix for the
  original "account can't be entered" usability complaint (the old UI used
  a `QSpinBox` — spinner semantics on an identifier field — for the login
  number; the web UI uses a plain text input).
- Local API auth token, onboarding banner for first-run users, and an
  in-app "View Recent Log" / "Copy to Clipboard" diagnostics panel in
  Settings — none of these have Qt equivalents, since they were built
  specifically to address gaps found while hardening the web UI.

## Is removing Qt safe right now?

**Yes, on feature grounds.** Every gap this document tracked (annotation
tool coverage, chart zoom/pan, clipboard-image-copy, and per-annotation
erase) is closed and covered by a real Playwright test that verifies the
actual behavior (a persisted delete after reload, a real clipboard
read-back, a hit-test that only erases the clicked shape) — not just that
a button exists. Removing `--legacy-qt`, `src/tradeaudit/ui/`, and the
`PySide6`/`pytest-qt` dependencies is a reasonable next step whenever
that's wanted; nothing else in the codebase depends on Qt being present.
It hasn't been done automatically here because removing a whole UI +
dependency is a decision worth a deliberate yes, not a side effect of
closing the last parity gap.

## Tests that only exist because of Qt

`tests/unit/test_dashboard_view.py`, `test_main_window.py`,
`test_ui_*.py`, and `test_chart_drawing_logic.py` /
`test_chart_screenshot_service.py` exercise Qt widgets directly and would
be deleted (not ported) if Qt is removed — their web-UI equivalents are
`tests/e2e/test_ui_flows.py`, which drives the actual rendered page instead
of instantiating Qt widgets in-process.
