# TradeAudit — Case Study

## 1. Overview

TradeAudit is a production-oriented MetaTrader 5 trade auditing, risk
analytics, and behavioral intelligence platform. It connects to a real MT5
terminal, reconstructs logical trades from raw broker deal history,
accounts for risk in R-multiples rather than raw currency, separates
strategy quality from execution quality, and runs quantitative research
(Monte Carlo, Risk of Ruin, rolling-window edge stability) on the result.

## 2. Problem

Raw MT5 trade history — a flat list of buy/sell deals — doesn't answer the
questions a trader actually needs answered:

- Does the strategy have a positive expectancy edge at all, independent of
  any one lucky or unlucky stretch?
- When the account is losing, is that the strategy's fault or the trader's
  — did they deviate from the plan?
- How much does rule-breaking cost, expressed in a way that's comparable
  across trades of different size (R, not currency)?
- Is performance actually degrading over time, or does it just feel that
  way after a losing streak?

Answering these requires turning a deal ledger into structured trades with
known initial risk, tagging each one against an explicit rule set, and
running statistics that account for sample-size uncertainty — not just
summing profit and loss.

## 3. Engineering Challenges

### MT5 deal ≠ logical trade

A single position can open, scale in, partially close, and close out across
many separate MT5 deals, and a hedging-mode account can hold simultaneous
opposite-direction positions on the same symbol. `TradeAggregator` groups
deals by `position_id`, computes volume-weighted average entry/exit prices,
and tracks status (`OPEN`/`CLOSED`) from the resulting fill sequence.

### The initial-SL bug this project's own testing caught

R-multiple accounting is only meaningful if it's based on the *original*
stop loss, never a trailed one. Verifying this against a real MT5 demo
account (10,697 deals, not synthetic fixtures) surfaced a real bug: MT5
**deals** never carry `sl`/`tp` fields — only the **order** that generated
a deal does. The code read `sl`/`tp` off the deal, which silently defaulted
to zero via `getattr`, so `initial_sl` came back unknown for every trade
synced from a real account — even though 164 unit tests were green,
because they constructed the domain object directly and never exercised
the real MT5-shape mapping. The fix joins each entry deal to its
originating order by ticket; the regression tests
(`tests/unit/test_history_reader.py`) model the real MT5 field shape
(deals without `sl`/`tp`, orders with them) specifically so this class of
bug can't silently return.

### Strategy vs. execution

`StrategyTraderComparator` splits closed trades into compliant vs.
deviation subsets and reports "deviation cost" as the R/currency gap
between how the strategy alone would have performed and what was actually
realized. A related bug found the same way: with no strategy assigned to
any trade yet (a first-run account, not a data-entry problem), the
compliant-performance baseline defaulted to zero, which made the formula
report a large fabricated "cost" and a misleading `FLAWED_STRATEGY_AND_EXECUTION`
verdict on any losing, unassigned account. It now reports
`NO_STRATEGY_ASSIGNED` with a zero cost until a strategy is actually
assigned.

### Large-history performance

Profiling the real 10,697-deal / 5,347-trade account (not a synthetic
benchmark) found two concrete bottlenecks: an N+1 query loading each
trade's deals with a separate round-trip (4.4s → 1.9s after batching), and
Monte Carlo / bootstrap resampling using `random.choice()` in a per-element
loop (~15 million calls, ~23s) instead of the batched `random.choices()`
— a 7.7x speedup with identical statistical behavior. Both were only
visible under real data volume; the unit test fixtures never had enough
rows to expose them.

### Behavioral analysis as heuristics, not diagnosis

Revenge-trading, FOMO, and overtrading flags are pattern-matching
heuristics (e.g. "opened within N minutes of the prior loss") with an
explicit confidence level and a plain-text reason attached to each flag —
not a claim of psychological certainty. The report generator and UI both
surface the reason, not just the label.

## 4. Architecture

```text
MetaTrader 5 Terminal
        │  (MetaTrader5 Python API)
        ▼
MT5 Connection / History / Candle Adapters
        │
        ▼
Trade Aggregation  (deals → logical trades, position-id grouped)
        │
        ▼
Risk / R-Multiple Engine  (initial-SL based, order-joined)
        │
        ▼
Strategy Compliance Engine  ──┐
        │                     │
        ▼                     ▼
Behavioral Analysis    Strategy vs Trader Comparison
        │                     │
        └─────────┬───────────┘
                   ▼
      Quantitative Research (Monte Carlo, Risk of Ruin, rolling metrics)
                   │
                   ▼
        Application Services (sync, backup, reporting)
                   │
                   ▼
          FastAPI local backend  (127.0.0.1, per-session auth token)
                   │
                   ▼
       Web UI inside a pywebview window (no browser chrome)
```

The domain/service/infrastructure layers have no UI dependency at all — the
web UI is a thin frontend over the same service classes a first PySide6
(Qt6) desktop UI used to call. That Qt UI was retired once the web UI
reached full feature parity, verified by a real end-to-end test for every
capability it used to be the only place to find (chart annotation
coverage, zoom/pan, clipboard image copy, per-annotation erase) rather
than by inspection.

## 5. Key Capabilities

R-multiple performance analytics · strategy compliance engine ·
four-quadrant strategy-vs-trader analysis · behavioral flag detection ·
Monte Carlo / Risk of Ruin / rolling-window quant research · bar-by-bar
candlestick trade replay with chart annotations and a trade journal ·
Markdown/AI-ready report export · Windows packaging (PyInstaller + Inno
Setup) with a one-command build script and a tag-triggered GitHub Actions
release pipeline.

## 6. Validation

197 automated tests (185 unit + a Playwright-driven browser end-to-end
suite covering the actual rendered UI, not just the API) run in CI across
Python 3.11–3.13. Beyond the test suite, the sync/aggregation/analytics
pipeline and every backend fix listed above were verified against a real
MT5 demo account with thousands of real deals — not fixture data — before
being called done. No private account numbers, broker names, or
credentials appear anywhere in this repository; the screenshots in the
README use a fully synthetic seeded dataset.

## 7. Technology

Python · MetaTrader5 Python API · FastAPI · pywebview · SQLAlchemy ·
SQLite (WAL mode, enforced foreign keys) · HTML/CSS/JavaScript ·
PyInstaller · Inno Setup · GitHub Actions · pytest · Playwright.

## 8. What this demonstrates for client work

MT5 API integration (connection lifecycle, history/candle reading, deal ↔
order reconciliation) · trading-domain data modeling · risk/R-multiple
engines · rule-based compliance systems · quantitative/statistical
analytics in pure Python · a desktop-app-as-local-web-service architecture
(FastAPI + pywebview) · Windows packaging and installer pipelines ·
GitHub Actions CI/CD for a desktop product · finding and fixing real bugs
by testing against production-shaped data instead of trusting a green
test suite alone.

## 9. Disclaimer

TradeAudit is software for trading analytics and engineering
demonstration purposes. It does not guarantee profitability and does not
provide investment advice. All figures should be verified independently
before being used to make trading decisions.

---

Built by **Dev Art Solutions** — [devart.solutions](https://devart.solutions)
