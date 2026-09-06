"""
FastAPI backend for the TradeAudit web UI. Wraps the existing, already-tested
service/domain/infrastructure layers - no business logic lives here.
"""
import logging
import secrets
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from tradeaudit.app.exceptions import MT5Error, CredentialStoreError
from tradeaudit.domain.models import MT5Settings, Strategy
from tradeaudit.domain.candles import TimeFrame
from tradeaudit.app.services.performance_analyzer import PerformanceAnalyzer
from tradeaudit.app.services.breakdown_analyzer import BreakdownAnalyzer
from tradeaudit.app.services.strategy_trader_comparator import StrategyTraderComparator
from tradeaudit.webui.context import AppContext
from tradeaudit.webui.serialization import to_jsonable

logger = logging.getLogger("tradeaudit.webui.server")

STATIC_DIR = Path(__file__).resolve().parent / "static"


class SettingsPayload(BaseModel):
    mt5_path: str = ""
    login: int = 0
    server: str = ""
    timeout_ms: int = 60000


class ConnectPayload(SettingsPayload):
    password: str = ""


class StrategyPayload(BaseModel):
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    allowed_symbols: list[str] = []
    allowed_sessions: list[str] = []
    min_rr: Optional[float] = None
    max_risk_pct: Optional[float] = None
    max_trades_per_day: Optional[int] = None
    requires_sl: bool = False
    requires_tp: bool = False
    allowed_direction: str = "ALL"
    is_active: bool = True


class AssignStrategyPayload(BaseModel):
    strategy_id: Optional[int] = None


def create_app(ctx: AppContext, api_token: Optional[str] = None) -> FastAPI:
    app = FastAPI(title="TradeAudit API")
    quant_cache: dict = {}

    # This server binds to 127.0.0.1 only, but "only reachable from this machine"
    # is not "only reachable by this app": any other local process, or a website
    # open in the user's regular browser, can otherwise fire unauthenticated
    # requests at a known/guessable localhost port (connect, sync, save settings,
    # trigger a backup...). The token is embedded into the index page we serve
    # ourselves and echoed back on every /api/* call - a cross-origin page can't
    # read it (blocked by browser same-origin policy) and a bare local process
    # never sees it unless it already loaded our own UI.
    app.state.api_token = api_token or secrets.token_urlsafe(32)

    @app.middleware("http")
    async def _require_api_token(request: Request, call_next):
        if request.url.path.startswith("/api/"):
            if request.headers.get("X-TradeAudit-Token") != app.state.api_token:
                return Response(status_code=401, content="Missing or invalid API token.")
        return await call_next(request)

    def closed_trades():
        trades = ctx.trade_repo.get_trades(ctx.current_login())
        return trades, [t for t in trades if t.status == "CLOSED"]

    # ---------------------------------------------------------------- state

    @app.get("/api/state")
    def get_state():
        saved = ctx.settings_repo.load_mt5_settings()
        account_info = None
        if ctx.mt5_service.is_connected():
            try:
                account_info = ctx.mt5_service.get_account_info()
            except Exception:
                account_info = None
        return {
            "app_name": ctx.settings.app_name,
            "app_version": ctx.settings.app_version,
            "connection_state": ctx.mt5_service.state.value,
            "last_error": ctx.mt5_service.last_error,
            "account": to_jsonable(account_info),
            "settings": to_jsonable(saved) if saved else None,
            "storage": {
                "data_dir": str(ctx.settings.data_dir),
                "database_url": ctx.settings.database_url,
            },
        }

    @app.post("/api/settings")
    def save_settings(payload: SettingsPayload):
        settings = MT5Settings(
            mt5_path=payload.mt5_path.strip(),
            login=payload.login,
            server=payload.server.strip(),
            timeout_ms=payload.timeout_ms,
        )
        ctx.settings_repo.save_mt5_settings(settings)
        return {"ok": True}

    @app.post("/api/connect")
    def connect(payload: ConnectPayload):
        settings = MT5Settings(
            mt5_path=payload.mt5_path.strip(),
            login=payload.login,
            server=payload.server.strip(),
            timeout_ms=payload.timeout_ms,
        )
        ctx.settings_repo.save_mt5_settings(settings)

        password = payload.password
        if not password and settings.login:
            try:
                password = ctx.credential_store.get_password(settings.login) or ""
            except CredentialStoreError:
                password = ""

        try:
            account_info = ctx.mt5_service.connect(
                mt5_path=settings.mt5_path,
                login=settings.login,
                password=password,
                server=settings.server,
                timeout_ms=settings.timeout_ms,
            )
        except MT5Error as e:
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        if settings.login and payload.password:
            try:
                ctx.credential_store.save_password(settings.login, payload.password)
            except CredentialStoreError as e:
                logger.warning("Could not save password to credential store: %s", e)

        return {"account": to_jsonable(account_info)}

    @app.post("/api/disconnect")
    def disconnect():
        ctx.mt5_service.disconnect()
        return {"ok": True}

    @app.post("/api/sync")
    def sync():
        saved = ctx.settings_repo.load_mt5_settings()
        if not saved or not saved.login:
            raise HTTPException(status_code=400, detail="Configure MT5 account settings first.")

        account_info = None
        if ctx.mt5_service.is_connected():
            try:
                account_info = ctx.mt5_service.get_account_info()
            except Exception:
                account_info = None

        result = ctx.sync_service.sync_account_history(account_id=saved.login, account_info=account_info)
        return to_jsonable(result)

    @app.post("/api/backup")
    def backup():
        try:
            path = ctx.backup_service.create_backup(tag="manual")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"path": str(path)}

    @app.get("/api/logs/recent")
    def recent_logs(lines: int = 300):
        """
        Tail the app's own log file. Lets a non-technical user grab diagnostic
        context (e.g. to paste into a support request) without hunting through
        %LOCALAPPDATA% for a file they don't know exists.
        """
        log_path = ctx.settings.log_dir / ctx.settings.log_file_name
        if not log_path.exists():
            return {"path": str(log_path), "lines": []}
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        return {"path": str(log_path), "lines": [l.rstrip("\n") for l in all_lines[-lines:]]}

    # --------------------------------------------------------------- trades

    @app.get("/api/trades")
    def list_trades():
        trades, _ = closed_trades()
        return [to_jsonable(t) for t in trades]

    @app.get("/api/trades/{trade_id}")
    def get_trade(trade_id: int):
        trades, _ = closed_trades()
        for t in trades:
            if t.id == trade_id:
                return to_jsonable(t)
        raise HTTPException(status_code=404, detail="Trade not found.")

    @app.post("/api/trades/{trade_id}/assign-strategy")
    def assign_strategy(trade_id: int, payload: AssignStrategyPayload):
        ctx.strategy_service.assign_strategy_to_trade(
            account_id=ctx.current_login(), trade_id=trade_id, strategy_id=payload.strategy_id
        )
        return {"ok": True}

    # ----------------------------------------------------------- dashboard

    @app.get("/api/dashboard")
    def dashboard():
        _, closed = closed_trades()
        metrics = PerformanceAnalyzer.analyze(closed)
        account_info = None
        if ctx.mt5_service.is_connected():
            try:
                account_info = ctx.mt5_service.get_account_info()
            except Exception:
                account_info = None
        return {"metrics": to_jsonable(metrics), "account": to_jsonable(account_info)}

    # ---------------------------------------------------------- strategies

    @app.get("/api/strategies")
    def list_strategies():
        return [to_jsonable(s) for s in ctx.strategy_service.get_all_strategies()]

    @app.post("/api/strategies")
    def create_strategy(payload: StrategyPayload):
        strategy = Strategy(**payload.model_dump(exclude={"id"}))
        saved = ctx.strategy_service.create_strategy(strategy)
        return to_jsonable(saved)

    @app.put("/api/strategies/{strategy_id}")
    def update_strategy(strategy_id: int, payload: StrategyPayload):
        strategy = Strategy(id=strategy_id, **payload.model_dump(exclude={"id"}))
        saved = ctx.strategy_service.update_strategy(strategy)
        return to_jsonable(saved)

    @app.delete("/api/strategies/{strategy_id}")
    def delete_strategy(strategy_id: int):
        ok = ctx.strategy_service.delete_strategy(strategy_id)
        return {"ok": ok}

    # ------------------------------------------------------- analytics tabs

    @app.get("/api/strategy-vs-trader")
    def strategy_vs_trader():
        _, closed = closed_trades()
        comparison = StrategyTraderComparator.compare(closed)
        return to_jsonable(comparison)

    @app.get("/api/breakdown")
    def breakdown():
        _, closed = closed_trades()
        return to_jsonable(BreakdownAnalyzer.analyze_all(closed))

    @app.get("/api/quant")
    def quant():
        _, closed = closed_trades()
        # Monte Carlo + bootstrap CI over 1000 simulations is CPU-bound pure Python and
        # took ~23s against a real 2.3k-trade account - far too slow to recompute on every
        # tab visit. Cache by trade count (invalidated by the next sync) and use fewer
        # simulations for this interactive view; the full-precision run still backs the
        # exported report if that ever needs it.
        cache_key = (ctx.current_login(), len(closed))
        if cache_key not in quant_cache:
            quant_cache.clear()
            quant_cache[cache_key] = ctx.quant_analyzer.analyze_quant_research(closed, num_simulations=300)
        return to_jsonable(quant_cache[cache_key])

    @app.get("/api/report")
    def report():
        trades, _ = closed_trades()
        strategies = {s.id: s for s in ctx.strategy_service.get_all_strategies() if s.id is not None}
        account_info = None
        if ctx.mt5_service.is_connected():
            try:
                account_info = ctx.mt5_service.get_account_info()
            except Exception:
                account_info = None
        markdown = ctx.report_generator.generate(trades=trades, account_info=account_info, strategies=strategies)
        return {"markdown": markdown}

    # ------------------------------------------------------------ live journal

    @app.get("/api/live-journal/positions")
    def live_positions():
        account_id = ctx.current_login()
        if not account_id:
            return {"status": "Configure MT5 settings first", "positions": [], "events": []}
        if not ctx.mt5_service.is_connected():
            return {"status": "MT5 Disconnected", "positions": [], "events": []}
        positions = ctx.live_watcher_service.poll_positions(account_id)
        events = ctx.trade_event_repo.get_all_events(limit=100)
        return {
            "status": f"Active ({len(positions)} open position(s))",
            "positions": [to_jsonable(p) for p in positions],
            "events": [to_jsonable(e) for e in events],
        }

    # ------------------------------------------------------------ trade chart

    @app.get("/api/trade-chart/{trade_id}")
    def trade_chart(trade_id: int, timeframe: str = "M15"):
        trades, _ = closed_trades()
        trade = next((t for t in trades if t.id == trade_id), None)
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found.")
        try:
            tf = TimeFrame(timeframe)
        except ValueError:
            tf = TimeFrame.M15
        candles = ctx.trade_chart_service.get_candles_for_trade(trade, timeframe=tf)
        overlay = ctx.trade_chart_service.build_overlay(trade)
        return {"candles": to_jsonable(candles), "overlay": to_jsonable(overlay)}

    # ------------------------------------------------------------------ SPA

    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")

    @app.get("/")
    def index():
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        token_script = f'<script>window.__TA_TOKEN__="{app.state.api_token}";</script>'
        html = html.replace("</head>", f"{token_script}</head>")
        return HTMLResponse(content=html)

    return app
