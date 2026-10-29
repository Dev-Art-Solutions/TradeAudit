# MQL5 article submission checklist

## Publication metadata

- **Title:** Building TradeAudit: turning MT5 deal history into trades I can actually review
- **Abstract:** A practical look at reconstructing MT5 deals into logical trades, preserving initial risk, separating strategy compliance from execution, and packaging the result as a local Windows analytics application.
- **Keywords:** MetaTrader 5, Python, trade journal, R-multiple, Monte Carlo, risk analysis, FastAPI, SQLite
- **Language:** English
- **Primary category:** MetaTrader 5 / Python integration

## Images and captions

Upload the images through the MQL5 editor rather than embedding repository-relative paths.

1. `docs/images/01-dashboard.png`  
   Caption: TradeAudit dashboard with monetary and R-based performance metrics.
2. `docs/images/02-strategy-vs-trader.png`  
   Caption: Comparison of compliant trades and execution deviations.
3. `docs/images/04-quant-risk.png`  
   Caption: Monte Carlo, risk estimates and rolling performance analysis.
4. `docs/images/03-trade-chart-replay.png`  
   Caption: Trade chart with execution levels, replay controls and technical overlays.
5. `docs/images/05-breakdowns.png`  
   Optional caption: Performance breakdowns by symbol, direction, session and time.

Use screenshots only after confirming that they contain no account number, broker name, server name, personal notes or identifiable trade comments.

## Editorial checks

- Keep the article educational. Explain the implementation choices and their limitations.
- Do not describe TradeAudit as an Expert Advisor, MQL5 Market product or trading signal.
- Do not promise profitability or imply that simulated paths are live results.
- Keep the distinction between deal aggregation, trade-history analysis and strategy backtesting.
- State that the application is read-only and does not place or modify orders.
- Retain the MAE/MFE limitation. OHLC candles cannot establish exact intrabar execution order.
- Use one repository link and one versioned release link. Remove either if the MQL5 editor or moderator rejects external links.
- Preview code blocks, lists and links in the MQL5 editor before submission.
- Run the final text through spelling review after pasting; editors can alter apostrophes and code indentation.

## Suggested author note

TradeAudit is a free, open-source portfolio project from Dev Art Solutions. The article describes its engineering and statistical conventions. It is not financial advice and does not guarantee future trading results.

## Files ready for submission

- Article HTML: `docs/mql5_tradeaudit_article.html`
- Screenshots: `docs/images/`
- Public release: `https://github.com/Dev-Art-Solutions/TradeAudit/releases/tag/v1.1.1`
