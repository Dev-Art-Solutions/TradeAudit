"""
FastAPI backend for the TradeAudit web UI. Wraps the existing, already-tested
service/domain/infrastructure layers - no business logic lives here.
"""
import base64
import binascii
import csv
import io
import logging
import secrets
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tradeaudit.app.exceptions import MT5Error, CredentialStoreError
from tradeaudit.domain.models import MT5Settings, Strategy
from tradeaudit.infrastructure.database.models import TradeModel
from tradeaudit.domain.candles import TimeFrame
from tradeaudit.domain.annotations import ChartAnnotation, AnnotationType, TradeJournalNote
from tradeaudit.app.services.performance_analyzer import PerformanceAnalyzer
from tradeaudit.app.services.breakdown_analyzer import BreakdownAnalyzer
from tradeaudit.app.services.strategy_trader_comparator import StrategyTraderComparator
from tradeaudit.webui.context import AppContext
from tradeaudit.webui.serialization import to_jsonable

logger = logging.getLogger("tradeaudit.webui.server")

STATIC_DIR = Path(__file__).resolve().parent / "static"


class SettingsPayload(BaseModel):
    mt5_path: str = Field(default="", max_length=1024)
    login: int = Field(default=0, ge=0)
    server: str = Field(default="", max_length=255)
    timeout_ms: int = Field(default=60000, ge=1000, le=300000)


class ConnectPayload(SettingsPayload):
    password: str = Field(default="", max_length=1024)


class StrategyPayload(BaseModel):
    id: Optional[int] = None
    name: str = Field(default="", min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    allowed_symbols: list[str] = Field(default_factory=list, max_length=200)
    allowed_sessions: list[str] = Field(default_factory=list, max_length=20)
    min_rr: Optional[float] = Field(default=None, ge=0, le=100)
    max_risk_pct: Optional[float] = Field(default=None, ge=0, le=100)
    max_trades_per_day: Optional[int] = Field(default=None, ge=1, le=10000)
    requires_sl: bool = False
    requires_tp: bool = False
    allowed_direction: str = "ALL"
    is_active: bool = True


class AssignStrategyPayload(BaseModel):
    strategy_id: Optional[int] = None


class TradeEmotionPayload(BaseModel):
    emotion_tag: Optional[str] = Field(default=None, max_length=64)
    behavior_notes: Optional[str] = Field(default=None, max_length=10000)


class JournalNotePayload(BaseModel):
    setup_name: str = Field(default="", max_length=255)
    rating: str = Field(default="A", max_length=8)
    pre_trade_thesis: str = Field(default="", max_length=20000)
    post_trade_review: str = Field(default="", max_length=20000)
    lessons_learned: str = Field(default="", max_length=20000)
    mistakes_identified: list[str] = Field(default_factory=list, max_length=200)
    checklist_data: dict[str, bool] = Field(default_factory=dict)


class AnnotationPayload(BaseModel):
    id: Optional[int] = None
    timeframe: str = Field(default="M15", max_length=16)
    annotation_type: str = Field(default="TREND_LINE", max_length=32)
    p1_time: Optional[str] = None
    p1_price: float = 0.0
    p2_time: Optional[str] = None
    p2_price: float = 0.0
    color: str = Field(default="#58a6ff", pattern=r"^#[0-9a-fA-F]{6}$")
    line_width: int = Field(default=2, ge=1, le=20)
    text: str = Field(default="", max_length=4000)


class ScreenshotPayload(BaseModel):
    image_base64: str = Field(min_length=1, max_length=7_000_000)


MAX_REQUEST_BYTES = 8 * 1024 * 1024
MAX_SCREENSHOT_BYTES = 5 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


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
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        started_at = time.perf_counter()

        def secure(response: Response) -> Response:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            response.headers["Cache-Control"] = "no-store"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; img-src 'self' data:; connect-src 'self'; "
                "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
                "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
            )
            response.headers["X-Request-ID"] = request_id
            return response

        host = (request.url.hostname or "").lower()
        allowed_hosts = {"127.0.0.1", "localhost", "::1"}
        if api_token is not None:  # Explicit tokens are used by the in-process test client.
            allowed_hosts.add("testserver")
        if host not in allowed_hosts:
            return secure(Response(status_code=400, content="Invalid host."))

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_BYTES:
                    return secure(Response(status_code=413, content="Request body too large."))
            except ValueError:
                return secure(Response(status_code=400, content="Invalid Content-Length header."))

        if request.url.path.startswith("/api/"):
            supplied_token = request.headers.get("X-TradeAudit-Token", "")
            if not secrets.compare_digest(supplied_token, app.state.api_token):
                return secure(Response(status_code=401, content="Missing or invalid API token."))
            origin = request.headers.get("origin")
            if origin and not origin.startswith(("http://127.0.0.1:", "http://localhost:")):
                return secure(Response(status_code=403, content="Invalid request origin."))

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled request failure request_id=%s method=%s path=%s",
                request_id,
                request.method,
                request.url.path,
            )
            response = JSONResponse(
                status_code=500,
                content={"detail": "Unexpected application error.", "request_id": request_id},
            )
        duration_ms = (time.perf_counter() - started_at) * 1000
        if response.status_code >= 500 or duration_ms >= 1000:
            logger.warning(
                "Request completed request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
        return secure(response)

    def closed_trades():
        login = ctx.current_login()
        trades = ctx.trade_repo.get_trades(login)
        if not trades and not login:
            with ctx.db_manager.session_scope() as session:
                first = session.query(TradeModel.account_id).first()
                if first:
                    trades = ctx.trade_repo.get_trades(first[0])
        return trades, [t for t in trades if t.status == "CLOSED"]

    # ---------------------------------------------------------------- state

    @app.get("/api/health")
    def health():
        database_ok = ctx.db_manager.check_connection()
        if not database_ok:
            raise HTTPException(status_code=503, detail="Database health check failed.")
        return {
            "status": "ok",
            "version": ctx.settings.app_version,
            "database": "ok",
            "mt5": ctx.mt5_service.state.value,
        }

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
        except Exception:
            logger.exception("Unexpected MT5 connection failure")
            raise HTTPException(status_code=500, detail="Unexpected MT5 connection failure. See application logs.")

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
        if result.success:
            quant_cache.clear()
            try:
                ctx.strategy_service.reevaluate_account_compliance(saved.login)
                ctx.behavior_service.run_behavior_analysis_for_account(saved.login)
            except Exception as e:
                logger.warning("Post-sync compliance/behavior evaluation warning: %s", e)
        return to_jsonable(result)

    @app.post("/api/backup")
    def backup():
        try:
            path = ctx.backup_service.create_backup(tag="manual")
        except Exception:
            logger.exception("Manual backup failed")
            raise HTTPException(status_code=500, detail="Backup failed. See application logs.")
        return {"path": str(path)}

    @app.get("/api/logs/recent")
    def recent_logs(lines: int = Query(default=300, ge=1, le=2000)):
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

    @app.get("/api/trades/export-csv")
    def export_trades_csv():
        trades, _ = closed_trades()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Position ID", "Symbol", "Direction", "Volume",
            "Open Time", "Close Time", "Open Price", "Close Price",
            "Initial SL", "Initial TP", "Profit", "Swap", "Commission",
            "Realized R", "Status", "Compliance Status", "Emotion Tag",
            "Strategy ID", "Behavior Notes"
        ])
        for t in trades:
            writer.writerow([
                t.id, t.position_id, t.symbol, t.direction, t.volume,
                t.open_time.isoformat() if t.open_time else "",
                t.close_time.isoformat() if t.close_time else "",
                t.open_price, t.close_price if t.close_price is not None else "",
                t.initial_sl if t.initial_sl is not None else "",
                t.initial_tp if t.initial_tp is not None else "",
                t.profit, t.swap, t.commission,
                t.realized_r if t.realized_r is not None else "",
                t.status, t.compliance_status or "",
                t.emotion_tag or "", t.strategy_id if t.strategy_id is not None else "",
                t.behavior_notes or ""
            ])
        csv_data = output.getvalue()
        login = ctx.current_login() or "history"
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="tradeaudit_{login}_{datetime.now().strftime("%Y%m%d")}.csv"'}
        )

    @app.get("/api/trades/{trade_id}")
    def get_trade(trade_id: int):
        trades, _ = closed_trades()
        for t in trades:
            if t.id == trade_id:
                return to_jsonable(t)
        raise HTTPException(status_code=404, detail="Trade not found.")

    @app.post("/api/trades/{trade_id}/assign-strategy")
    def assign_strategy(trade_id: int, payload: AssignStrategyPayload):
        account_id = ctx.current_login()
        if not account_id:
            with ctx.db_manager.session_scope() as session:
                tm = session.query(TradeModel).filter(TradeModel.id == trade_id).first()
                if tm:
                    account_id = tm.account_id
        trade = ctx.strategy_service.assign_strategy_to_trade(
            account_id=account_id, trade_id=trade_id, strategy_id=payload.strategy_id
        )
        return {"ok": True, "trade": to_jsonable(trade)}

    @app.post("/api/trades/{trade_id}/emotion")
    def update_trade_emotion(trade_id: int, payload: TradeEmotionPayload):
        ok = ctx.behavior_service.update_emotion_tag(
            trade_id=trade_id,
            emotion_tag=payload.emotion_tag,
            behavior_notes=payload.behavior_notes,
        )
        return {"ok": ok}

    @app.post("/api/behavior/analyze")
    def run_behavior_analysis():
        account_id = ctx.current_login()
        if not account_id:
            with ctx.db_manager.session_scope() as session:
                first = session.query(TradeModel.account_id).first()
                if first:
                    account_id = first[0]
        if not account_id:
            return {"flags": {}}
        flags_map = ctx.behavior_service.run_behavior_analysis_for_account(account_id)
        return {"flags": {str(k): to_jsonable(v) for k, v in flags_map.items()}}

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

    # ------------------------------------------------------------ journal & annotations

    def _parse_iso(value: Optional[str]):
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @app.get("/api/trades/{trade_id}/journal")
    def get_journal_note(trade_id: int):
        return to_jsonable(ctx.journal_service.get_or_create_note(trade_id))

    @app.post("/api/trades/{trade_id}/journal")
    def save_journal_note(trade_id: int, payload: JournalNotePayload):
        note = ctx.journal_service.get_or_create_note(trade_id)
        note.setup_name = payload.setup_name
        note.rating = payload.rating
        note.pre_trade_thesis = payload.pre_trade_thesis
        note.post_trade_review = payload.post_trade_review
        note.lessons_learned = payload.lessons_learned
        note.mistakes_identified = payload.mistakes_identified
        note.checklist_data = payload.checklist_data
        note.updated_at = datetime.now(timezone.utc)
        saved = ctx.journal_service.save_note(note)
        return to_jsonable(saved)

    @app.get("/api/trades/{trade_id}/annotations")
    def list_annotations(trade_id: int, timeframe: Optional[str] = None):
        return [to_jsonable(a) for a in ctx.journal_service.get_annotations(trade_id, timeframe)]

    @app.post("/api/trades/{trade_id}/annotations")
    def create_annotation(trade_id: int, payload: AnnotationPayload):
        try:
            ann_type = AnnotationType(payload.annotation_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown annotation_type: {payload.annotation_type}")
        annotation = ChartAnnotation(
            id=payload.id,
            trade_id=trade_id,
            timeframe=payload.timeframe,
            annotation_type=ann_type,
            p1_time=_parse_iso(payload.p1_time),
            p1_price=payload.p1_price,
            p2_time=_parse_iso(payload.p2_time),
            p2_price=payload.p2_price,
            color=payload.color,
            line_width=payload.line_width,
            text=payload.text,
        )
        saved = ctx.journal_service.save_annotation(annotation)
        return to_jsonable(saved)

    @app.delete("/api/annotations/{annotation_id}")
    def delete_annotation(annotation_id: int):
        ok = ctx.journal_service.delete_annotation(annotation_id)
        return {"ok": ok}

    @app.delete("/api/trades/{trade_id}/annotations")
    def clear_annotations(trade_id: int, timeframe: Optional[str] = None):
        count = ctx.journal_service.clear_annotations(trade_id, timeframe)
        return {"cleared": count}

    @app.post("/api/trades/{trade_id}/screenshot")
    def save_screenshot(trade_id: int, payload: ScreenshotPayload):
        try:
            header, encoded = payload.image_base64.split(",", 1) if "," in payload.image_base64 else ("", payload.image_base64)
            if header and header != "data:image/png;base64":
                raise ValueError("Unsupported image type")
            image_bytes = base64.b64decode(encoded, validate=True)
            if len(image_bytes) > MAX_SCREENSHOT_BYTES:
                raise HTTPException(status_code=413, detail="Screenshot exceeds the 5 MB limit.")
            if not image_bytes.startswith(PNG_SIGNATURE):
                raise ValueError("Invalid PNG signature")
        except HTTPException:
            raise
        except (ValueError, TypeError, binascii.Error):
            raise HTTPException(status_code=400, detail="Invalid image data.")

        ctx.settings.screenshots_dir.mkdir(parents=True, exist_ok=True)
        filename = f"trade_{trade_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
        out_path = ctx.settings.screenshots_dir / filename
        out_path.write_bytes(image_bytes)

        note = ctx.journal_service.attach_screenshot_to_trade(trade_id, str(out_path))
        return {"path": str(out_path), "note": to_jsonable(note)}

    # ------------------------------------------------------------------ SPA

    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")

    @app.get("/")
    def index():
        html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
        token_script = f'<script>window.__TA_TOKEN__="{app.state.api_token}";</script>'
        html = html.replace("</head>", f"{token_script}</head>")
        return HTMLResponse(content=html)

    return app
