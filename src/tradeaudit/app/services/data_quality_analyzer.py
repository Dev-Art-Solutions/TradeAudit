"""Assess whether a trade dataset is complete enough for reliable auditing."""

from dataclasses import dataclass, field
from typing import Iterable

from tradeaudit.domain.models import ComplianceStatus, Trade


@dataclass(frozen=True)
class DataQualityDimension:
    key: str
    label: str
    coverage: float
    weight: int
    complete: int
    total: int


@dataclass(frozen=True)
class DataQualityReport:
    score: int
    grade: str
    summary: str
    dimensions: list[DataQualityDimension] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)


class DataQualityAnalyzer:
    """Produce a deterministic completeness score for closed trade records.

    The score intentionally measures data availability, not trading performance.
    This keeps profitable results from masking missing risk or review evidence.
    """

    _DIMENSIONS = (
        ("risk", "R-multiple coverage", 35),
        ("stop_loss", "Initial stop-loss coverage", 25),
        ("compliance", "Strategy audit coverage", 20),
        ("timing", "Complete trade timing", 10),
        ("review", "Trader review coverage", 10),
    )

    @classmethod
    def analyze(cls, trades: Iterable[Trade]) -> DataQualityReport:
        records = list(trades)
        total = len(records)
        if not total:
            return DataQualityReport(
                score=0,
                grade="N/A",
                summary="Sync closed trades to evaluate audit data quality.",
            )

        checks = {
            "risk": lambda trade: trade.realized_r is not None,
            "stop_loss": lambda trade: trade.initial_sl not in (None, 0),
            "compliance": lambda trade: (
                trade.strategy_id is not None
                and trade.compliance_status not in (None, "", ComplianceStatus.UNCHECKED.value)
            ),
            "timing": lambda trade: trade.open_time is not None and trade.close_time is not None,
            "review": lambda trade: bool(trade.emotion_tag or trade.behavior_notes),
        }

        dimensions = []
        for key, label, weight in cls._DIMENSIONS:
            complete = sum(1 for trade in records if checks[key](trade))
            dimensions.append(DataQualityDimension(
                key=key,
                label=label,
                coverage=complete / total,
                weight=weight,
                complete=complete,
                total=total,
            ))

        score = round(sum(item.coverage * item.weight for item in dimensions))
        grade = cls._grade(score)
        actions = cls._actions(dimensions)
        summary = {
            "Excellent": "The audit is backed by highly complete trade evidence.",
            "Good": "The dataset is reliable, with a few review gaps remaining.",
            "Fair": "Core analytics are usable, but missing context limits confidence.",
            "Needs attention": "Fill critical risk and audit gaps before relying on conclusions.",
        }[grade]
        return DataQualityReport(score, grade, summary, dimensions, actions)

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 90:
            return "Excellent"
        if score >= 75:
            return "Good"
        if score >= 55:
            return "Fair"
        return "Needs attention"

    @staticmethod
    def _actions(dimensions: list[DataQualityDimension]) -> list[str]:
        messages = {
            "risk": "Restore initial risk data so more trades can be measured in R.",
            "stop_loss": "Capture the initial stop loss for trades that currently have none.",
            "compliance": "Assign strategies and run compliance evaluation on unchecked trades.",
            "timing": "Repair incomplete open/close timestamps before session analysis.",
            "review": "Add emotion tags or review notes to strengthen behavioral analysis.",
        }
        return [messages[item.key] for item in dimensions if item.coverage < 0.8][:3]
