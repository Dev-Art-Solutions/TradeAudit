from datetime import datetime, timedelta

from tradeaudit.app.services.data_quality_analyzer import DataQualityAnalyzer
from tradeaudit.domain.models import Trade


def complete_trade(trade_id: int = 1) -> Trade:
    opened = datetime(2026, 1, 1, 9, 0)
    return Trade(
        id=trade_id,
        status="CLOSED",
        open_time=opened,
        close_time=opened + timedelta(hours=1),
        initial_sl=1.095,
        realized_r=1.5,
        strategy_id=7,
        compliance_status="COMPLIANT",
        emotion_tag="CALM",
    )


def test_empty_dataset_has_no_misleading_quality_grade():
    report = DataQualityAnalyzer.analyze([])
    assert report.score == 0
    assert report.grade == "N/A"
    assert report.dimensions == []


def test_complete_dataset_scores_excellent():
    report = DataQualityAnalyzer.analyze([complete_trade(), complete_trade(2)])
    assert report.score == 100
    assert report.grade == "Excellent"
    assert report.actions == []
    assert all(d.coverage == 1 for d in report.dimensions)


def test_missing_risk_and_review_data_produces_actionable_gaps():
    trade = complete_trade()
    trade.realized_r = None
    trade.initial_sl = None
    trade.emotion_tag = None

    report = DataQualityAnalyzer.analyze([trade])

    assert report.score == 30
    assert report.grade == "Needs attention"
    assert [d.key for d in report.dimensions if d.coverage == 0] == ["risk", "stop_loss", "review"]
    assert len(report.actions) == 3


def test_score_uses_coverage_across_all_trades():
    incomplete = complete_trade(2)
    incomplete.strategy_id = None
    incomplete.compliance_status = "UNCHECKED"
    incomplete.emotion_tag = None

    report = DataQualityAnalyzer.analyze([complete_trade(), incomplete])

    assert report.score == 85
    assert report.grade == "Good"
