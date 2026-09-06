"""
Unit tests for StrategyTraderComparator service (Phase 8).
"""

from datetime import datetime
import pytest

from tradeaudit.domain.models import Trade, ComplianceStatus, EmotionTag, UserBehaviorAction
from tradeaudit.app.services.strategy_trader_comparator import StrategyTraderComparator


def test_empty_trades_list():
    comparison = StrategyTraderComparator.compare([])
    assert comparison.quality_verdict == "NO_TRADES"
    assert comparison.total_performance.total_trades == 0
    assert comparison.compliant_performance.total_trades == 0
    assert comparison.deviation_performance.total_trades == 0
    assert comparison.emotional_performance.total_trades == 0
    assert comparison.deviation_cost_r == 0.0


def test_strategy_vs_trader_comparison_subsets():
    now = datetime.now()
    trades = [
        # Good Win: Compliant + Win (+2R, +200 USD)
        Trade(
            id=1, status="CLOSED", direction="BUY", profit=200.0,
            realized_r=2.0, compliance_status=ComplianceStatus.COMPLIANT.value,
            emotion_tag=EmotionTag.CALM.value, open_time=now, close_time=now
        ),
        # Good Loss: Compliant + Loss (-1R, -100 USD)
        Trade(
            id=2, status="CLOSED", direction="BUY", profit=-100.0,
            realized_r=-1.0, compliance_status=ComplianceStatus.COMPLIANT.value,
            emotion_tag=EmotionTag.CALM.value, open_time=now, close_time=now
        ),
        # Bad Loss: Deviation + Loss (-2R, -200 USD) (Emotional FOMO)
        Trade(
            id=3, status="CLOSED", direction="SELL", profit=-200.0,
            realized_r=-2.0, compliance_status=ComplianceStatus.DEVIATION.value,
            emotion_tag=EmotionTag.FOMO.value, open_time=now, close_time=now
        ),
        # Bad Win: Deviation + Win (+1R, +100 USD)
        Trade(
            id=4, status="CLOSED", direction="BUY", profit=100.0,
            realized_r=1.0, compliance_status=ComplianceStatus.PARTIAL.value,
            emotion_tag=EmotionTag.CALM.value, open_time=now, close_time=now
        ),
    ]

    comparison = StrategyTraderComparator.compare(trades, min_sample_size=4)

    # Total performance
    assert comparison.total_performance.total_trades == 4
    assert comparison.total_performance.net_r == 0.0  # 2 - 1 - 2 + 1 = 0
    assert comparison.total_performance.net_profit == 0.0  # 200 - 100 - 200 + 100 = 0

    # Compliant performance (Trades 1 & 2)
    assert comparison.compliant_performance.total_trades == 2
    assert comparison.compliant_performance.net_r == 1.0  # 2 - 1 = 1
    assert comparison.compliant_performance.net_profit == 100.0

    # Deviation performance (Trades 3 & 4)
    assert comparison.deviation_performance.total_trades == 2
    assert comparison.deviation_performance.net_r == -1.0  # -2 + 1 = -1
    assert comparison.deviation_performance.net_profit == -100.0

    # Emotional performance (Trade 3)
    assert comparison.emotional_performance.total_trades == 1
    assert comparison.emotional_performance.net_r == -2.0

    # Deviation Cost R: Compliant Net R (1.0) - Total Net R (0.0) = +1.0 R
    assert comparison.deviation_cost_r == 1.0
    assert comparison.deviation_cost_monetary == 100.0

    # Quality Verdict: Execution Breakdown (Strategy gave +1R compliant, total gave 0R)
    assert comparison.quality_verdict == "EXECUTION_BREAKDOWN"

    # Four Quadrants
    quads = comparison.four_quadrants
    assert quads.good_wins_count == 1
    assert quads.good_wins_net_r == 2.0
    assert quads.good_losses_count == 1
    assert quads.good_losses_net_r == -1.0
    assert quads.bad_wins_count == 1
    assert quads.bad_wins_net_r == 1.0
    assert quads.bad_losses_count == 1
    assert quads.bad_losses_net_r == -2.0


def test_high_discipline_verdict():
    now = datetime.now()
    trades = [
        Trade(
            id=1, status="CLOSED", profit=300.0, realized_r=3.0,
            compliance_status=ComplianceStatus.COMPLIANT.value, open_time=now, close_time=now
        ),
        Trade(
            id=2, status="CLOSED", profit=100.0, realized_r=1.0,
            compliance_status=ComplianceStatus.COMPLIANT.value, open_time=now, close_time=now
        ),
    ]
    comparison = StrategyTraderComparator.compare(trades)
    assert comparison.deviation_cost_r == 0.0
    assert comparison.quality_verdict == "HIGH_DISCIPLINE"


def test_no_strategy_assigned_does_not_fabricate_deviation_cost():
    """
    Real accounts commonly have trades with no strategy assigned at all
    (compliance_status stays UNCHECKED). Before the fix, deviation_cost_r was
    computed as compliant_perf.net_r (0.0 default) - total_perf.net_r, which
    fabricated a large "deviation cost" out of thin air and mislabeled the
    verdict as FLAWED_STRATEGY_AND_EXECUTION whenever the account was simply
    losing money with no strategy tracking in place.
    """
    now = datetime.now()
    trades = [
        Trade(id=1, status="CLOSED", profit=-100.0, realized_r=-1.0,
              compliance_status=ComplianceStatus.UNCHECKED.value, open_time=now, close_time=now),
        Trade(id=2, status="CLOSED", profit=-50.0, realized_r=-0.5,
              compliance_status=ComplianceStatus.UNCHECKED.value, open_time=now, close_time=now),
    ]
    comparison = StrategyTraderComparator.compare(trades)
    assert comparison.deviation_cost_r == 0.0
    assert comparison.deviation_cost_monetary == 0.0
    assert comparison.quality_verdict == "NO_STRATEGY_ASSIGNED"


def test_all_trades_deviations_verdict():
    now = datetime.now()
    trades = [
        Trade(
            id=1, status="CLOSED", profit=-100.0, realized_r=-1.0,
            compliance_status=ComplianceStatus.DEVIATION.value, open_time=now, close_time=now
        ),
    ]
    comparison = StrategyTraderComparator.compare(trades)
    assert comparison.quality_verdict == "ALL_TRADES_DEVIATIONS"
