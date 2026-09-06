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
  trendline / horizontal ray / text note annotations, 1-click screenshot,
  and a trade journal (setup name, grade, thesis, review, lessons learned)

## Qt-only (not yet ported to the web UI)

- **Rectangle zone and arrow annotation types.** The domain model
  (`AnnotationType`) and database schema support all six annotation types;
  the web UI's drawing toolbar currently implements three (trendline,
  horizontal ray, text note). Rectangle zones and directional arrows only
  exist in the Qt `CandlestickChartWidget`.
- **Interactive chart zoom/pan.** The Qt chart widget supports a `PAN` tool
  and a "fit to view" zoom reset. The web chart currently renders a fixed
  bar count with no zoom/pan gesture.
- **Copy chart image to clipboard.** Qt's `ChartScreenshotService` can copy
  a `QWidget.grab()` directly to the OS clipboard in addition to saving a
  file. It's a `QObject`/Qt-widget API and doesn't apply as-is to a
  browser-rendered `<canvas>` — the web UI's screenshot button only saves
  to disk (`%LOCALAPPDATA%/TradeAudit/screenshots/`, or `screenshots/` in
  dev) via `canvas.toDataURL()`. A clipboard-write from the web UI would
  need a separate implementation (e.g. the Clipboard API's `ClipboardItem`
  for images), not a reuse of the Qt path.
- **Eraser tool** for removing a single annotation by clicking it directly
  on the chart. The web UI only offers "Clear Drawings" (clears every
  annotation for the loaded trade/timeframe at once) plus per-annotation
  delete via the API (`DELETE /api/annotations/{id}`), which isn't wired
  to a chart-click gesture yet.

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

**Not yet — recommend keeping it as documented legacy for now.** The
rectangle/arrow annotation tools and chart zoom/pan are real, visible
capability the web UI doesn't have. Removing the Qt UI today would be a
net feature loss, not just a UI swap. Once those three gaps close (rectangle
+ arrow annotation types, chart zoom/pan, and a decision on whether
clipboard-image-copy is worth implementing for the browser canvas),
`--legacy-qt` and `src/tradeaudit/ui/` can be removed along with
`PySide6`/`pytest-qt` from the dependency list — nothing else in the
codebase depends on Qt being present.

## Tests that only exist because of Qt

`tests/unit/test_dashboard_view.py`, `test_main_window.py`,
`test_ui_*.py`, and `test_chart_drawing_logic.py` /
`test_chart_screenshot_service.py` exercise Qt widgets directly and would
be deleted (not ported) if Qt is removed — their web-UI equivalents are
`tests/e2e/test_ui_flows.py`, which drives the actual rendered page instead
of instantiating Qt widgets in-process.
