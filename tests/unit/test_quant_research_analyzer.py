"""
Unit tests for QuantResearchAnalyzer service (Phase 13).
"""

from datetime import datetime, timezone
import pytest

from tradeaudit.domain.models import Trade, TradeDeal
from tradeaudit.domain.analytics import (
    RuinRiskLevel,
    QuantResearchResult
)
from tradeaudit.app.services.quant_research_analyzer import QuantResearchAnalyzer


def _make_trade(ticket: int, profit: float, realized_r: float, symbol: str = "EURUSD") -> Trade:
    return Trade(
        id=ticket,
        position_id=ticket,
        account_id=12345,
        symbol=symbol,
        direction="BUY",
        volume=0.1,
        open_time=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        close_time=datetime(2026, 8, 1, 11, 0, tzinfo=timezone.utc),
        open_price=1.1000,
        close_price=1.1050,
        initial_sl=1.0950,
        initial_tp=1.1100,
        profit=profit,
        commission=0.0,
        swap=0.0,
        fee=0.0,
        status="CLOSED",
        price_risk=0.0050,
        monetary_risk=50.0,
        planned_rr=2.0,
        realized_r=realized_r
    )


@pytest.fixture
def analyzer():
    return QuantResearchAnalyzer()


@pytest.fixture
def sample_winning_trades():
    # 30 trades with healthy positive expectancy: 60% win rate with 2R wins, 1R losses
    trades = []
    for i in range(1, 31):
        if i % 5 in (1, 2, 3):  # 60% win rate
            trades.append(_make_trade(ticket=1000 + i, profit=100.0, realized_r=2.0))
        else:
            trades.append(_make_trade(ticket=1000 + i, profit=-50.0, realized_r=-1.0))
    return trades


@pytest.fixture
def sample_losing_trades():
    # 20 trades with negative expectancy: 30% win rate with 1R wins, 1.5R losses
    trades = []
    for i in range(1, 21):
        if i % 3 == 0:
            trades.append(_make_trade(ticket=2000 + i, profit=50.0, realized_r=1.0))
        else:
            trades.append(_make_trade(ticket=2000 + i, profit=-75.0, realized_r=-1.5))
    return trades


def test_monte_carlo_empty_trades(analyzer):
    res = analyzer.run_monte_carlo([], num_simulations=100)
    assert res.simulations_count == 100
    assert len(res.percentile_50th_r) == 0
    assert res.final_r_median == 0.0


def test_monte_carlo_simulation_reproducibility(analyzer, sample_winning_trades):
    res1 = analyzer.run_monte_carlo(sample_winning_trades, num_simulations=500, horizon_trades=30, random_seed=42)
    res2 = analyzer.run_monte_carlo(sample_winning_trades, num_simulations=500, horizon_trades=30, random_seed=42)

    assert res1.final_r_median == res2.final_r_median
    assert res1.max_drawdown_95th == res2.max_drawdown_95th
    assert res1.percentile_50th_r == res2.percentile_50th_r


def test_monte_carlo_positive_expectancy_ordering(analyzer, sample_winning_trades):
    res = analyzer.run_monte_carlo(sample_winning_trades, num_simulations=500, horizon_trades=30, random_seed=100)

    assert len(res.percentile_5th_r) == 31
    assert len(res.percentile_95th_r) == 31
    assert res.final_r_median > 0.0
    assert res.percentile_5th_r[-1] <= res.percentile_25th_r[-1] <= res.percentile_50th_r[-1] <= res.percentile_75th_r[-1] <= res.percentile_95th_r[-1]
    assert res.probability_of_target_r > 50.0


def test_risk_of_ruin_insufficient_sample(analyzer):
    few_trades = [_make_trade(ticket=1, profit=50.0, realized_r=1.0)]
    ror = analyzer.calculate_risk_of_ruin(few_trades)
    assert ror.risk_level == RuinRiskLevel.INSUFFICIENT_DATA


def test_risk_of_ruin_negative_expectancy(analyzer, sample_losing_trades):
    ror = analyzer.calculate_risk_of_ruin(sample_losing_trades, max_drawdown_tolerance_r=10.0, random_seed=42)
    assert ror.risk_level == RuinRiskLevel.CRITICAL_RISK
    assert ror.formulaic_ruin_probability == 100.0
    assert "inevitable" in ror.summary_verdict.lower()
    assert ror.simulation_horizon_trades == 60


def test_shuffle_and_bootstrap_are_distinguished(analyzer, sample_winning_trades):
    shuffled = analyzer.run_monte_carlo(sample_winning_trades, num_simulations=20, random_seed=7, sampling_method="shuffle")
    bootstrapped = analyzer.run_monte_carlo(sample_winning_trades, num_simulations=20, random_seed=7, sampling_method="bootstrap")
    assert shuffled.sampling_method == "shuffle_without_replacement"
    assert bootstrapped.sampling_method == "bootstrap_with_replacement"
    assert shuffled.final_r_5th == shuffled.final_r_95th


def test_risk_of_ruin_profitable_strategy(analyzer, sample_winning_trades):
    ror = analyzer.calculate_risk_of_ruin(sample_winning_trades, max_drawdown_tolerance_r=20.0, random_seed=42)
    assert ror.risk_level in (RuinRiskLevel.MINIMAL_RISK, RuinRiskLevel.LOW_RISK)
    assert ror.formulaic_ruin_probability < 10.0


def test_rolling_metrics_sliding_windows(analyzer, sample_winning_trades):
    res = analyzer.calculate_rolling_metrics(sample_winning_trades, window_sizes=(10, 20))
    
    assert 10 in res
    assert 20 in res

    roll10 = res[10]
    assert len(roll10.points) == 21  # 30 - 10 + 1
    assert roll10.points[0].trade_index == 10
    assert roll10.points[-1].trade_index == 30
    assert roll10.edge_stability_verdict in ("HIGHLY_STABLE_EDGE", "MODERATE_STABILITY_EDGE")
    assert roll10.stability_score > 0.5


def test_rolling_metrics_insufficient_trades_for_window(analyzer, sample_losing_trades):
    # 20 trades sample with window size 50
    res = analyzer.calculate_rolling_metrics(sample_losing_trades, window_sizes=(50,))
    assert res[50].edge_stability_verdict == "INSUFFICIENT_DATA"
    assert len(res[50].points) == 0


def test_bootstrap_confidence_intervals(analyzer, sample_winning_trades):
    ci = analyzer.calculate_bootstrap_confidence_intervals(
        sample_winning_trades,
        num_resamples=1000,
        confidence_level=0.95,
        random_seed=42
    )

    assert ci.sample_size == 30
    assert ci.win_rate_ci[0] < ci.win_rate_ci[1]
    assert 40.0 <= ci.win_rate_ci[0] <= 60.0
    assert ci.expectancy_ci[0] < ci.expectancy_ci[1]
    assert ci.is_statistically_significant is True


def test_analyze_quant_research_master(analyzer, sample_winning_trades):
    master: QuantResearchResult = analyzer.analyze_quant_research(
        sample_winning_trades,
        num_simulations=200,
        horizon_trades=25,
        ruin_threshold_r=15.0,
        target_r=25.0,
        random_seed=42
    )

    assert master.total_trades_analyzed == 30
    assert master.trades_with_r_count == 30
    assert master.monte_carlo.simulations_count == 200
    assert master.monte_carlo.horizon_trades == 25
    assert master.risk_of_ruin.risk_level != RuinRiskLevel.INSUFFICIENT_DATA
    assert 20 in master.rolling_analytics
    assert master.confidence_intervals.sample_size == 30
