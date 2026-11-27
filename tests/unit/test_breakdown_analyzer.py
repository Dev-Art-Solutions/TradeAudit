"""
Unit tests for BreakdownAnalyzer service (Phase 9).
"""

from datetime import datetime
import pytest

from tradeaudit.domain.models import Trade
from tradeaudit.app.services.breakdown_analyzer import BreakdownAnalyzer


@pytest.fixture
def sample_breakdown_trades():
    """Create sample trades covering symbols, directions, times, sessions, streaks, and emotions."""
    # Trade 1: EURUSD, BUY, Win, Asia (02:00), Monday, CALM
    t1 = Trade(
        id=1,
        account_id=1001,
        position_id=101,
        symbol="EURUSD",
        direction="BUY",
        open_time=datetime(2024, 1, 1, 2, 0),  # Monday 02:00 UTC (Asia)
        close_time=datetime(2024, 1, 1, 3, 0),
        profit=100.0,
        realized_r=2.0,
        status="CLOSED",
        emotion_tag="CALM"
    )

    # Trade 2: EURUSD, BUY, Loss, London (09:00), Tuesday, FOMO
    t2 = Trade(
        id=2,
        account_id=1001,
        position_id=102,
        symbol="EURUSD",
        direction="BUY",
        open_time=datetime(2024, 1, 2, 9, 0),  # Tuesday 09:00 UTC (London)
        close_time=datetime(2024, 1, 2, 10, 0),
        profit=-50.0,
        realized_r=-1.0,
        status="CLOSED",
        emotion_tag="FOMO"
    )

    # Trade 3: GBPUSD, SELL, Win, Overlap (14:00), Wednesday, REVENGE
    t3 = Trade(
        id=3,
        account_id=1001,
        position_id=103,
        symbol="GBPUSD",
        direction="SELL",
        open_time=datetime(2024, 1, 3, 14, 0),  # Wednesday 14:00 UTC (London, NY, Overlap)
        close_time=datetime(2024, 1, 3, 15, 0),
        profit=150.0,
        realized_r=3.0,
        status="CLOSED",
        emotion_tag="REVENGE"
    )

    # Trade 4: GBPUSD, SELL, Loss, New York (18:00), Thursday, CALM
    t4 = Trade(
        id=4,
        account_id=1001,
        position_id=104,
        symbol="GBPUSD",
        direction="SELL",
        open_time=datetime(2024, 1, 4, 18, 0),  # Thursday 18:00 UTC (New York)
        close_time=datetime(2024, 1, 4, 19, 0),
        profit=-50.0,
        realized_r=-1.0,
        status="CLOSED",
        emotion_tag="CALM"
    )

    return [t1, t2, t3, t4]


def test_analyze_by_symbol(sample_breakdown_trades):
    results = BreakdownAnalyzer.analyze_by_symbol(sample_breakdown_trades)
    assert "EURUSD" in results
    assert "GBPUSD" in results
    assert results["EURUSD"].total_trades == 2
    assert results["GBPUSD"].total_trades == 2
    assert results["EURUSD"].net_r == 1.0
    assert results["GBPUSD"].net_r == 2.0


def test_analyze_by_direction(sample_breakdown_trades):
    results = BreakdownAnalyzer.analyze_by_direction(sample_breakdown_trades)
    assert "BUY" in results
    assert "SELL" in results
    assert results["BUY"].total_trades == 2
    assert results["SELL"].total_trades == 2
    assert results["BUY"].winning_trades == 1
    assert results["SELL"].winning_trades == 1


def test_analyze_by_session(sample_breakdown_trades):
    results = BreakdownAnalyzer.analyze_by_session(sample_breakdown_trades)
    assert results["ASIA"].total_trades == 1
    assert results["LONDON"].total_trades == 2  # t2 and t3 (14:00 is London & NY)
    assert results["NEW_YORK"].total_trades == 2  # t3 and t4
    assert results["OVERLAP"].total_trades == 1  # t3 (14:00)


def test_analyze_by_weekday(sample_breakdown_trades):
    results = BreakdownAnalyzer.analyze_by_weekday(sample_breakdown_trades)
    assert results["Monday"].total_trades == 1
    assert results["Tuesday"].total_trades == 1
    assert results["Wednesday"].total_trades == 1
    assert results["Thursday"].total_trades == 1
    assert results["Friday"].total_trades == 0


def test_analyze_by_hour(sample_breakdown_trades):
    results = BreakdownAnalyzer.analyze_by_hour(sample_breakdown_trades)
    assert results[2].total_trades == 1
    assert results[9].total_trades == 1
    assert results[14].total_trades == 1
    assert results[18].total_trades == 1
    assert results[0].total_trades == 0


def test_analyze_by_context(sample_breakdown_trades):
    results = BreakdownAnalyzer.analyze_by_context(sample_breakdown_trades)
    # Chronological sequence of outcomes: t1 (WIN), t2 (LOSS), t3 (WIN), t4 (LOSS)
    # t1: INITIAL_OR_BE
    # t2: POST_WIN (after t1 win)
    # t3: POST_LOSS (after t2 loss)
    # t4: POST_WIN (after t3 win)
    assert results["INITIAL_OR_BE"].total_trades == 1
    assert results["POST_WIN"].total_trades == 2
    assert results["POST_LOSS"].total_trades == 1


def test_analyze_by_streak(sample_breakdown_trades):
    results = BreakdownAnalyzer.analyze_by_streak(sample_breakdown_trades)
    # t1: STREAK_0 -> WIN (win_streak = 1)
    # t2: WIN_STREAK_1 -> LOSS (loss_streak = 1)
    # t3: LOSS_STREAK_1 -> WIN (win_streak = 1)
    # t4: WIN_STREAK_1 -> LOSS
    assert results["STREAK_0"].total_trades == 1
    assert results["WIN_STREAK_1"].total_trades == 2
    assert results["LOSS_STREAK_1"].total_trades == 1


def test_analyze_by_emotion(sample_breakdown_trades):
    results = BreakdownAnalyzer.analyze_by_emotion(sample_breakdown_trades)
    assert "CALM" in results
    assert "FOMO" in results
    assert "REVENGE" in results
    assert results["CALM"].total_trades == 2
    assert results["FOMO"].total_trades == 1
    assert results["REVENGE"].total_trades == 1


def test_analyze_all(sample_breakdown_trades):
    all_res = BreakdownAnalyzer.analyze_all(sample_breakdown_trades)
    assert len(all_res.by_symbol) == 2
    assert len(all_res.by_direction) == 2
    assert len(all_res.by_session) == 5
    assert len(all_res.by_weekday) == 7
    assert len(all_res.by_hour) == 24
    assert len(all_res.by_duration) == 5
    assert len(all_res.by_compliance) >= 2


def test_analyze_by_compliance(sample_breakdown_trades):
    sample_breakdown_trades[0].compliance_status = "COMPLIANT"
    sample_breakdown_trades[1].compliance_status = "DEVIATION"
    sample_breakdown_trades[2].compliance_status = "COMPLIANT"
    sample_breakdown_trades[3].compliance_status = "UNCHECKED"

    results = BreakdownAnalyzer.analyze_by_compliance(sample_breakdown_trades)
    assert "COMPLIANT" in results
    assert "DEVIATION" in results
    assert "UNCHECKED" in results
    assert results["COMPLIANT"].total_trades == 2
    assert results["COMPLIANT"].winning_trades == 2
    assert results["DEVIATION"].total_trades == 1
    assert results["DEVIATION"].winning_trades == 0
    assert results["UNCHECKED"].total_trades == 1


def test_analyze_by_duration(sample_breakdown_trades):
    # sample_breakdown_trades:
    # t1: 2:00 to 3:00 -> 60 mins -> INTRADAY_1H_TO_4H
    # t2: 9:00 to 10:00 -> 60 mins -> INTRADAY_1H_TO_4H
    # t3: 14:00 to 15:30 -> 90 mins -> INTRADAY_1H_TO_4H
    # t4: 17:00 to 17:03 -> 3 mins -> SCALP_UNDER_5M
    sample_breakdown_trades[3].open_time = datetime(2024, 1, 4, 17, 0)
    sample_breakdown_trades[3].close_time = datetime(2024, 1, 4, 17, 3)

    results = BreakdownAnalyzer.analyze_by_duration(sample_breakdown_trades)
    assert "SCALP_UNDER_5M" in results
    assert "INTRADAY_5M_TO_1H" in results
    assert "INTRADAY_1H_TO_4H" in results
    assert "SESSION_4H_TO_1D" in results
    assert "SWING_OVER_1D" in results
    assert results["SCALP_UNDER_5M"].total_trades == 1
    assert results["INTRADAY_1H_TO_4H"].total_trades == 3


def test_analyze_by_strategy(sample_breakdown_trades):
    sample_breakdown_trades[0].strategy_id = 1
    sample_breakdown_trades[1].strategy_id = 2
    strats = {1: "Trend Following", 2: "London Breakout"}

    results = BreakdownAnalyzer.analyze_by_strategy(sample_breakdown_trades, strategies=strats)
    assert "Trend Following" in results
    assert "London Breakout" in results
    assert "Unassigned" in results
    assert results["Trend Following"].total_trades == 1
    assert results["London Breakout"].total_trades == 1
    assert results["Unassigned"].total_trades == 2
