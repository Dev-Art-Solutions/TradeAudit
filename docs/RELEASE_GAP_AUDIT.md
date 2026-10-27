# TradeAudit Release Gap Audit

Audit date: 2026-10-27  
Scope: current `main` working tree, compared with the targeted enhancement plan.

## Baseline evidence

| Capability | Status | Evidence | Release acceptance criterion |
|---|---|---|---|
| Core performance (R, expectancy, PF, drawdown, streaks) | Implemented | `performance_analyzer.py`, `test_performance_analyzer.py` | Regression tests pass for empty, partial-R, win/loss and drawdown samples. |
| Symbol/direction/session/time breakdowns | Implemented | `breakdown_analyzer.py` and its tests | API and report agree for the same filtered trade set. |
| Monte Carlo, ruin estimates, rolling metrics, bootstrap CI | Partial | `quant_research_analyzer.py` | Sampling mode, horizon, assumptions and seed are explicit; nonpositive expectancy is not described as guaranteed ruin. |
| MT5 deal aggregation, partial close and scale-in handling | Implemented, needs broader fixtures | `trade_aggregator.py`, `test_trade_aggregator.py` | Hedging, netting, reversal and partial-close fixtures are green and account-isolated. |
| Planned and realized R | Implemented | `rmultiple_calculator.py` | Unknown initial SL yields unknown R and is counted as incomplete. |
| Recovery factor and duration analytics | Implemented in this enhancement | `performance_analyzer.py` | Recovery factor is undefined at zero drawdown; duration excludes invalid/missing timestamps. |
| MAE/MFE, capture/giveback and exit efficiency | Missing | No domain contract or calculation service | Use only candles/ticks inside the open interval; persist provenance, approximation and completeness flags. |
| Execution-quality cost view | Partial | Commission/swap/fee and planned/realized R exist; no reliable slippage baseline | Never infer requested price or spread when source records do not provide them. |
| UI/API/report integration | Partial | Generic dataclass API serialization exposes new aggregate metrics; report includes them | Add dedicated excursion/execution cards only after traceable per-trade data exists. |
| SQLite migration/versioning | Partial | Startup schema creation and compatibility columns exist in `database/connection.py`; no general migration framework | Upgrade a copied legacy database, preserve all rows, and record schema version. |
| Credential storage, loopback token, log masking | Implemented, release verification pending | credential store, server middleware, logging tests | Clean Windows install proves secrets/account identifiers do not enter logs or sample exports. |
| Packaging and release workflows | Implemented, gates incomplete | `TradeAudit.spec`, installer scripts, `ci.yml`, `release.yml` | Release must run tests and packaged smoke test and publish SHA-256 checksums before GitHub release. |

## Ranked issues

1. **P0 — Statistical wording and methodology:** the previous nonpositive-expectancy branch said “Guaranteed Ruin”; `risk_per_trade_pct` was displayed but did not alter an R-denominated threshold. The implementation now uses qualified critical-risk wording and publishes horizon and assumptions. The parameter remains informational by design until the API accepts an account-percent drawdown limit.
2. **P0 — Excursion data provenance:** MAE/MFE cannot be calculated correctly from the current persisted trade record alone. A future schema must store source granularity (`tick` or `OHLC`), coverage interval, missing-data status, pip size/currency conversion source and calculation version. OHLC output must be labelled approximate.
3. **P1 — Release test environment:** the local full suite currently fails during collection because installed Starlette expects `httpx.BaseTransport`, absent from the resolved local `httpx` module. CI installs declared dependencies afresh, but dependencies are only lower-bounded and not locked.
4. **P1 — Migration assurance:** add schema versioning plus legacy upgrade/backup/corrupt-database integration tests before adding excursion columns.
5. **P1 — Release integrity:** produce checksums and run a packaged executable smoke check before the release action.
6. **P2 — Stress scenarios:** add transparent spread/commission/slippage adjustments only for fields present in source data; do not label trade-history resampling as strategy backtesting.
7. **P2 — Public launch:** screenshots, anonymized sample report, clean Windows 10/11 verification and external publication require release credentials and environments and are not established by repository tests.

## Data conventions adopted

- Recovery factor is net profit divided by absolute maximum monetary drawdown. It is `null` when maximum drawdown is zero because the ratio is undefined.
- Duration is `close_time - open_time` in minutes for closed trades with ordered, nonmissing timestamps. Completeness is reported as a sample count.
- Bootstrap Monte Carlo samples observed R values with replacement and estimates outcome uncertainty under stationarity. Shuffle mode permutes without replacement and estimates sequence risk for the observed sample. Neither models clustered dependence or changing market regimes.
- Risk of ruin is a model estimate, not a guarantee. Its empirical horizon is explicit. With an R-denominated drawdown limit, `risk_per_trade_pct` is metadata; callers must convert account-percent tolerance to R or use a future percent-denominated interface.

## Verification record

- `pytest tests/unit/test_performance_analyzer.py tests/unit/test_quant_research_analyzer.py -q`: 20 passed.
- `pytest tests/unit --ignore=tests/unit/test_webui_server.py -q`: 140 passed.
- `pytest tests/unit -q`: collection blocked before execution by the local FastAPI/Starlette and `httpx==0.13.3` incompatibility described above.
- Full API unit and Playwright suites remain mandatory on a clean dependency environment before release.

## Deferred schema for MAE/MFE

The minimum safe addition is a versioned one-to-one trade-excursion record rather than nullable columns silently mixed into `trades`. It should include price/pips/currency/R values, favorable peak, adverse trough, pip size, conversion rate/source, source granularity, coverage start/end, expected/observed sample counts, approximation flag, quality status and calculation version. Initial-risk R fields must stay null when initial SL or monetary risk is unknown. This avoids presenting inferred bar extremes as exact tick execution and supports recalculation when better data becomes available.
