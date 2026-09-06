"""
Strategy vs Trader Comparator Service for TradeAudit.
Contrasts strategy edge (compliant performance) against trader execution quality (deviations, emotional trades).
Calculates Four-Quadrant statistics and Deviation Cost (R).
"""

from typing import List
from datetime import datetime

from tradeaudit.domain.models import Trade, ComplianceStatus, EmotionTag, UserBehaviorAction
from tradeaudit.domain.analytics import (
    PerformanceMetrics,
    FourQuadrantCounts,
    StrategyVsTraderComparison
)
from tradeaudit.app.services.performance_analyzer import PerformanceAnalyzer


class StrategyTraderComparator:
    """Service for comparing strategy performance vs execution breakdown and behavioral mistakes."""

    @classmethod
    def compare(cls, trades: List[Trade], min_sample_size: int = 30) -> StrategyVsTraderComparison:
        """
        Perform complete comparative analysis between strategy rules and trader execution.

        Args:
            trades: List of Trade domain entities.
            min_sample_size: Minimum sample size threshold for statistical confidence.

        Returns:
            StrategyVsTraderComparison containing total, compliant, deviation, and emotional metrics.
        """
        closed_trades = [t for t in trades if t.status and t.status.upper() == "CLOSED"]

        total_perf = PerformanceAnalyzer.analyze(closed_trades, min_sample_size=min_sample_size)

        if len(closed_trades) == 0:
            return StrategyVsTraderComparison(
                total_performance=total_perf,
                compliant_performance=PerformanceMetrics(min_sample_size=min_sample_size),
                deviation_performance=PerformanceMetrics(min_sample_size=min_sample_size),
                emotional_performance=PerformanceMetrics(min_sample_size=min_sample_size),
                four_quadrants=FourQuadrantCounts(),
                deviation_cost_r=0.0,
                deviation_cost_monetary=0.0,
                quality_verdict="NO_TRADES"
            )

        # Categorize trade subsets
        compliant_trades = [
            t for t in closed_trades
            if t.compliance_status == ComplianceStatus.COMPLIANT.value
        ]

        deviation_trades = [
            t for t in closed_trades
            if t.compliance_status in (ComplianceStatus.DEVIATION.value, ComplianceStatus.PARTIAL.value)
        ]

        emotional_trades = [
            t for t in closed_trades
            if (t.emotion_tag and t.emotion_tag != EmotionTag.CALM.value)
            or t.user_behavior_action == UserBehaviorAction.CONFIRMED.value
            or len(t.auto_behavior_flags) > 0
        ]

        # Calculate metrics for each subset
        compliant_perf = PerformanceAnalyzer.analyze(compliant_trades, min_sample_size=min_sample_size)
        deviation_perf = PerformanceAnalyzer.analyze(deviation_trades, min_sample_size=min_sample_size)
        emotional_perf = PerformanceAnalyzer.analyze(emotional_trades, min_sample_size=min_sample_size)

        # Compute Four Quadrant Statistics
        quadrants = FourQuadrantCounts()

        for t in compliant_trades:
            t_r = t.realized_r if t.realized_r is not None else 0.0
            if t.net_profit > 0:
                quadrants.good_wins_count += 1
                quadrants.good_wins_net_r += t_r
                quadrants.good_wins_profit += t.net_profit
            elif t.net_profit < 0:
                quadrants.good_losses_count += 1
                quadrants.good_losses_net_r += t_r
                quadrants.good_losses_profit += t.net_profit

        for t in deviation_trades:
            t_r = t.realized_r if t.realized_r is not None else 0.0
            if t.net_profit > 0:
                quadrants.bad_wins_count += 1
                quadrants.bad_wins_net_r += t_r
                quadrants.bad_wins_profit += t.net_profit
            elif t.net_profit < 0:
                quadrants.bad_losses_count += 1
                quadrants.bad_losses_net_r += t_r
                quadrants.bad_losses_profit += t.net_profit

        # Round Four Quadrant totals
        quadrants.good_wins_net_r = round(quadrants.good_wins_net_r, 4)
        quadrants.good_wins_profit = round(quadrants.good_wins_profit, 2)
        quadrants.good_losses_net_r = round(quadrants.good_losses_net_r, 4)
        quadrants.good_losses_profit = round(quadrants.good_losses_profit, 2)

        quadrants.bad_wins_net_r = round(quadrants.bad_wins_net_r, 4)
        quadrants.bad_wins_profit = round(quadrants.bad_wins_profit, 2)
        quadrants.bad_losses_net_r = round(quadrants.bad_losses_net_r, 4)
        quadrants.bad_losses_profit = round(quadrants.bad_losses_profit, 2)

        # Deviation Cost R: performance gap between pure compliance and actual realized.
        # Only meaningful once at least one trade has actually been checked against a
        # strategy - with no compliant trades at all, "compliant_perf.net_r" is just the
        # PerformanceMetrics default (0.0), which would otherwise make the cost equal to
        # the *negative* of total performance for every unassigned account.
        has_compliance_data = len(compliant_trades) > 0 or len(deviation_trades) > 0
        if has_compliance_data:
            deviation_cost_r = round(compliant_perf.net_r - total_perf.net_r, 4)
            deviation_cost_monetary = round(compliant_perf.net_profit - total_perf.net_profit, 2)
        else:
            deviation_cost_r = 0.0
            deviation_cost_monetary = 0.0

        # Quality Diagnostic Verdict
        if not has_compliance_data:
            quality_verdict = "NO_STRATEGY_ASSIGNED"
        elif len(compliant_trades) == 0 and len(deviation_trades) > 0:
            quality_verdict = "ALL_TRADES_DEVIATIONS"
        elif compliant_perf.net_r > 0 and deviation_cost_r > 0:
            quality_verdict = "EXECUTION_BREAKDOWN"
        elif compliant_perf.net_r <= 0 and deviation_perf.net_r > 0:
            quality_verdict = "FLAWED_STRATEGY_LUCKY_DEVIATIONS"
        elif compliant_perf.net_r <= 0 and deviation_perf.net_r <= 0:
            quality_verdict = "FLAWED_STRATEGY_AND_EXECUTION"
        elif deviation_cost_r <= 0 and compliant_perf.net_r > 0:
            quality_verdict = "HIGH_DISCIPLINE"
        else:
            quality_verdict = "BALANCED"

        return StrategyVsTraderComparison(
            total_performance=total_perf,
            compliant_performance=compliant_perf,
            deviation_performance=deviation_perf,
            emotional_performance=emotional_perf,
            four_quadrants=quadrants,
            deviation_cost_r=deviation_cost_r,
            deviation_cost_monetary=deviation_cost_monetary,
            quality_verdict=quality_verdict
        )
