"""
Unit tests for PerformanceAnalyzer service.
"""

from datetime import datetime, timedelta
import pytest

from tradeaudit.domain.models import Trade
from tradeaudit.domain.analytics import ProfitabilityVerdict
from tradeaudit.app.services.performance_analyzer import PerformanceAnalyzer


def create_sample_trade(
    profit: float,
    realized_r: float = None,
    status: str = "CLOSED",
    close_minutes_offset: int = 0
) -> Trade:
    """Helper function to build a mock trade for performance testing."""
    base_time = datetime(2026, 1, 1, 10, 0)
    open_t = base_time + timedelta(minutes=close_minutes_offset)
    close_t = open_t + timedelta(minutes=30)
    return Trade(
        status=status,
        profit=profit,
        swap=0.0,
        commission=0.0,
        fee=0.0,
        realized_r=realized_r,
        open_time=open_t,
        close_time=close_t
    )


def test_empty_trades_list():
    """Verify behavior when no trades are passed."""
    metrics = PerformanceAnalyzer.analyze([])
    assert metrics.total_trades == 0
    assert metrics.verdict == ProfitabilityVerdict.INSUFFICIENT_DATA
    assert metrics.max_drawdown_r == 0.0
    assert metrics.max_drawdown_monetary == 0.0
    assert metrics.cumulative_r_series == []
    assert metrics.cumulative_monetary_series == []


def test_filters_open_trades():
    """Verify open trades are ignored in performance metrics."""
    open_trade = Trade(status="OPEN", profit=500.0, realized_r=5.0)
    closed_trade = create_sample_trade(profit=100.0, realized_r=2.0, status="CLOSED")

    metrics = PerformanceAnalyzer.analyze([open_trade, closed_trade], min_sample_size=30)
    assert metrics.total_trades == 1
    assert metrics.net_profit == 100.0
    assert metrics.net_r == 2.0


def test_core_metrics_calculation():
    """Verify win rate, profit factor, monetary and R averages, and expectancy."""
    trades = [
        create_sample_trade(profit=100.0, realized_r=2.0, close_minutes_offset=1),
        create_sample_trade(profit=-50.0, realized_r=-1.0, close_minutes_offset=2),
        create_sample_trade(profit=150.0, realized_r=3.0, close_minutes_offset=3),
        create_sample_trade(profit=-50.0, realized_r=-1.0, close_minutes_offset=4),
        create_sample_trade(profit=0.0, realized_r=0.0, close_minutes_offset=5),
    ]

    metrics = PerformanceAnalyzer.analyze(trades, min_sample_size=5)

    assert metrics.total_trades == 5
    assert metrics.winning_trades == 2
    assert metrics.losing_trades == 2
    assert metrics.breakeven_trades == 1

    assert metrics.win_rate == 0.4
    assert metrics.loss_rate == 0.4

    assert metrics.net_profit == 150.0
    assert metrics.gross_profit == 250.0
    assert metrics.gross_loss == 100.0
    assert metrics.profit_factor == 2.5

    assert metrics.avg_win_monetary == 125.0
    assert metrics.avg_loss_monetary == 50.0
    assert metrics.expectancy_monetary == 30.0

    assert metrics.trades_with_r == 5
    assert metrics.net_r == 3.0
    assert metrics.avg_win_r == 2.5
    assert metrics.avg_loss_r == 1.0
    assert metrics.expectancy_r == 0.6


def test_drawdown_curve_r_and_monetary():
    """Verify peak-to-trough max drawdown calculation for R and monetary series."""
    trades = [
        create_sample_trade(profit=100.0, realized_r=2.0, close_minutes_offset=1),   # cum: 100, 2.0R (peak: 100, 2.0R)
        create_sample_trade(profit=-150.0, realized_r=-3.0, close_minutes_offset=2), # cum: -50, -1.0R (dd: 150, 3.0R)
        create_sample_trade(profit=50.0, realized_r=1.0, close_minutes_offset=3),    # cum: 0, 0.0R (dd: 100, 2.0R)
        create_sample_trade(profit=-100.0, realized_r=-2.0, close_minutes_offset=4), # cum: -100, -2.0R (dd: 200, 4.0R)
    ]

    metrics = PerformanceAnalyzer.analyze(trades, min_sample_size=4)

    assert metrics.cumulative_monetary_series == [100.0, -50.0, 0.0, -100.0]
    assert metrics.max_drawdown_monetary == 200.0
    assert metrics.recovery_factor == -0.5

    assert metrics.cumulative_r_series == [2.0, -1.0, 0.0, -2.0]
    assert metrics.drawdown_r_series == [0.0, 3.0, 2.0, 4.0]
    assert metrics.max_drawdown_r == 4.0


def test_duration_metrics_and_undefined_recovery_factor():
    trades = [create_sample_trade(profit=100.0, realized_r=1.0)]
    metrics = PerformanceAnalyzer.analyze(trades)
    assert metrics.avg_duration_minutes == 30.0
    assert metrics.median_duration_minutes == 30.0
    assert metrics.trades_with_duration == 1
    assert metrics.recovery_factor is None


def test_streak_counters():
    """Verify maximum consecutive win and loss streak calculations."""
    profits = [10.0, 20.0, 30.0, -10.0, -20.0, 15.0, -5.0, -5.0, -5.0, -5.0]
    trades = [create_sample_trade(profit=p, close_minutes_offset=i) for i, p in enumerate(profits)]

    metrics = PerformanceAnalyzer.analyze(trades, min_sample_size=10)

    assert metrics.max_consecutive_wins == 3
    assert metrics.max_consecutive_losses == 4


def test_profitability_verdicts():
    """Verify sample size thresholds and edge verdict classifications."""
    # Insufficient sample (< 30 trades)
    small_sample = [create_sample_trade(profit=10.0, realized_r=1.0, close_minutes_offset=i) for i in range(10)]
    m_small = PerformanceAnalyzer.analyze(small_sample, min_sample_size=30)
    assert m_small.verdict == ProfitabilityVerdict.INSUFFICIENT_DATA
    assert m_small.is_sample_sufficient is False

    # Positive Expectancy (30 winning trades)
    pos_sample = [create_sample_trade(profit=20.0, realized_r=1.0, close_minutes_offset=i) for i in range(30)]
    m_pos = PerformanceAnalyzer.analyze(pos_sample, min_sample_size=30)
    assert m_pos.verdict == ProfitabilityVerdict.POSITIVE_EXPECTANCY
    assert m_pos.is_sample_sufficient is True

    # Negative Expectancy (30 losing trades)
    neg_sample = [create_sample_trade(profit=-20.0, realized_r=-1.0, close_minutes_offset=i) for i in range(30)]
    m_neg = PerformanceAnalyzer.analyze(neg_sample, min_sample_size=30)
    assert m_neg.verdict == ProfitabilityVerdict.NEGATIVE_EXPECTANCY

    # Break Even Expectancy
    be_sample = [
        create_sample_trade(profit=20.0 if i % 2 == 0 else -20.0, realized_r=0.02 if i % 2 == 0 else -0.02, close_minutes_offset=i)
        for i in range(30)
    ]
    m_be = PerformanceAnalyzer.analyze(be_sample, min_sample_size=30)
    assert m_be.verdict == ProfitabilityVerdict.BREAK_EVEN


def test_missing_sl_handling():
    """Verify trades without realized_r are excluded from R metrics but included in monetary metrics."""
    trades = [
        create_sample_trade(profit=100.0, realized_r=2.0, close_minutes_offset=1),
        create_sample_trade(profit=50.0, realized_r=None, close_minutes_offset=2),
        create_sample_trade(profit=-30.0, realized_r=-1.0, close_minutes_offset=3),
    ]

    metrics = PerformanceAnalyzer.analyze(trades, min_sample_size=3)

    assert metrics.total_trades == 3
    assert metrics.net_profit == 120.0
    assert metrics.trades_with_r == 2
    assert metrics.net_r == 1.0


def test_reproducibility():
    """Verify running analyzer on identical dataset yields identical results."""
    trades = [
        create_sample_trade(profit=100.0, realized_r=2.0, close_minutes_offset=1),
        create_sample_trade(profit=-50.0, realized_r=-1.0, close_minutes_offset=2),
    ]

    res1 = PerformanceAnalyzer.analyze(trades)
    res2 = PerformanceAnalyzer.analyze(trades)

    assert res1 == res2
