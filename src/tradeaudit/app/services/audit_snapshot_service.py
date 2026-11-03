"""Create reproducible, privacy-safe evidence snapshots for trade audits."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable

from tradeaudit.app.services.data_quality_analyzer import DataQualityAnalyzer
from tradeaudit.app.services.performance_analyzer import PerformanceAnalyzer
from tradeaudit.domain.models import Trade


@dataclass(frozen=True)
class AuditSnapshot:
    schema_version: int
    generated_at: str
    app_version: str
    dataset_sha256: str
    trade_count: int
    period: dict
    metrics: dict
    data_quality: dict

    def as_dict(self) -> dict:
        return asdict(self)


class AuditSnapshotService:
    """Fingerprint audit inputs and package aggregate evidence without identity data."""

    SCHEMA_VERSION = 1

    @classmethod
    def build(cls, trades: Iterable[Trade], app_version: str) -> AuditSnapshot:
        records = [trade for trade in trades if trade.status and trade.status.upper() == "CLOSED"]
        canonical_records = sorted(
            (cls._canonical_trade(trade) for trade in records),
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
        canonical_json = json.dumps(
            canonical_records, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
        )
        fingerprint = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        metrics = PerformanceAnalyzer.analyze(records)
        quality = DataQualityAnalyzer.analyze(records)
        starts = [trade.open_time for trade in records if trade.open_time]
        ends = [trade.close_time for trade in records if trade.close_time]
        return AuditSnapshot(
            schema_version=cls.SCHEMA_VERSION,
            generated_at=datetime.now(timezone.utc).isoformat(),
            app_version=app_version,
            dataset_sha256=fingerprint,
            trade_count=len(records),
            period={"from": cls._iso(min(starts)) if starts else None, "to": cls._iso(max(ends)) if ends else None},
            metrics={
                "verdict": metrics.verdict.value,
                "win_rate": metrics.win_rate,
                "net_profit": metrics.net_profit,
                "expectancy_r": metrics.expectancy_r,
                "profit_factor": metrics.profit_factor,
                "max_drawdown_r": metrics.max_drawdown_r,
                "trades_with_r": metrics.trades_with_r,
            },
            data_quality={
                "score": quality.score,
                "grade": quality.grade,
                "coverage": {dimension.key: dimension.coverage for dimension in quality.dimensions},
            },
        )

    @classmethod
    def _canonical_trade(cls, trade: Trade) -> dict:
        return {
            "symbol": trade.symbol,
            "direction": trade.direction,
            "volume": cls._number(trade.volume),
            "open_time": cls._iso(trade.open_time),
            "close_time": cls._iso(trade.close_time),
            "open_price": cls._number(trade.open_price),
            "close_price": cls._number(trade.close_price),
            "initial_sl": cls._number(trade.initial_sl),
            "initial_tp": cls._number(trade.initial_tp),
            "net_profit": cls._number(trade.net_profit),
            "realized_r": cls._number(trade.realized_r),
            "compliance_status": trade.compliance_status,
            "emotion_tag": trade.emotion_tag,
        }

    @staticmethod
    def _number(value):
        return None if value is None else round(float(value), 8)

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
