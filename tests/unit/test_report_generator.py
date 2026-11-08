"""
Unit tests for MarkdownReportGenerator and report domain models (Phase 11).
"""

from datetime import datetime, timedelta
import pytest

from tradeaudit.domain.models import (
    Trade,
    TradeDeal,
    MT5AccountInfo,
    Strategy,
    ComplianceStatus,
    EmotionTag,
    BehaviorFlag,
    BehaviorFlagType,
    ConfidenceLevel,
    UserBehaviorAction
)
from tradeaudit.domain.filters import (
    AnalysisFilter,
    PeriodPreset,
    DirectionFilter,
    ResultFilter
)
from tradeaudit.domain.report import (
    ExportType,
    PrivacyOptions,
    ReportConfig
)
from tradeaudit.app.services.report_generator import MarkdownReportGenerator


@pytest.fixture
def sample_trades() -> list[Trade]:
    base_time = datetime(2026, 8, 25, 10, 0, 0)
    trades = [
        # Trade 1: Compliant BUY win on EURUSD (+2R)
        Trade(
            id=1,
            account_id=1234567,
            position_id=9001,
            symbol="EURUSD",
            direction="BUY",
            volume=1.0,
            open_time=base_time,
            close_time=base_time + timedelta(hours=2),
            open_price=1.1000,
            close_price=1.1040,
            initial_sl=1.0980,
            initial_tp=1.1060,
            profit=400.0,
            status="CLOSED",
            monetary_risk=200.0,
            realized_r=2.0,
            risk_percentage=1.0,
            strategy_id=1,
            compliance_status=ComplianceStatus.COMPLIANT.value,
            emotion_tag=EmotionTag.CALM.value
        ),
        # Trade 2: Compliant BUY loss on EURUSD (-1R)
        Trade(
            id=2,
            account_id=1234567,
            position_id=9002,
            symbol="EURUSD",
            direction="BUY",
            volume=1.0,
            open_time=base_time + timedelta(days=1),
            close_time=base_time + timedelta(days=1, hours=1),
            open_price=1.1020,
            close_price=1.1000,
            initial_sl=1.1000,
            initial_tp=1.1080,
            profit=-200.0,
            status="CLOSED",
            monetary_risk=200.0,
            realized_r=-1.0,
            risk_percentage=1.0,
            strategy_id=1,
            compliance_status=ComplianceStatus.COMPLIANT.value,
            emotion_tag=EmotionTag.CALM.value
        ),
        # Trade 3: Deviation SELL loss on GBPUSD (-1.5R) with Revenge tag
        Trade(
            id=3,
            account_id=1234567,
            position_id=9003,
            symbol="GBPUSD",
            direction="SELL",
            volume=2.0,
            open_time=base_time + timedelta(days=1, minutes=70),
            close_time=base_time + timedelta(days=1, hours=3),
            open_price=1.3000,
            close_price=1.3030,
            initial_sl=1.3020,
            initial_tp=1.2940,
            profit=-600.0,
            status="CLOSED",
            monetary_risk=400.0,
            realized_r=-1.5,
            risk_percentage=2.0,
            strategy_id=1,
            compliance_status=ComplianceStatus.DEVIATION.value,
            deviation_reason="MAX_RISK_PERCENT violated: 2.0% > 1.0%",
            emotion_tag=EmotionTag.REVENGE.value,
            auto_behavior_flags=[
                BehaviorFlag(
                    flag_type=BehaviorFlagType.POSSIBLE_REVENGE_TRADE,
                    confidence=ConfidenceLevel.HIGH,
                    reason="Opened 10m after loss with 2x risk"
                )
            ],
            user_behavior_action=UserBehaviorAction.CONFIRMED.value
        ),
        # Trade 4: Trade without SL (Unknown R)
        Trade(
            id=4,
            account_id=1234567,
            position_id=9004,
            symbol="XAUUSD",
            direction="BUY",
            volume=0.5,
            open_time=base_time + timedelta(days=2),
            close_time=base_time + timedelta(days=2, hours=1),
            open_price=2500.0,
            close_price=2510.0,
            initial_sl=None,
            initial_tp=None,
            profit=500.0,
            status="CLOSED",
            monetary_risk=None,
            realized_r=None,
            risk_percentage=None,
            strategy_id=None,
            compliance_status=ComplianceStatus.UNCHECKED.value
        )
    ]
    return trades


@pytest.fixture
def sample_account() -> MT5AccountInfo:
    return MT5AccountInfo(
        login=1234567,
        name="John Doe",
        server="MetaQuotes-Demo",
        company="MetaQuotes Ltd",
        currency="USD",
        balance=10000.0,
        equity=10100.0
    )


@pytest.fixture
def sample_strategies() -> dict[int, Strategy]:
    return {
        1: Strategy(
            id=1,
            name="Trend Pullback",
            description="4H trend continuation",
            max_risk_pct=1.0,
            min_rr=1.5
        )
    }


def test_generate_summary_report(sample_trades, sample_account, sample_strategies):
    generator = MarkdownReportGenerator(app_version="0.1.0")
    config = ReportConfig(
        export_type=ExportType.SUMMARY,
        privacy=PrivacyOptions(mask_account_number=True, hide_broker=True, mask_tickets=True)
    )

    report = generator.generate(
        trades=sample_trades,
        config=config,
        account_info=sample_account,
        strategies=sample_strategies
    )

    # Check YAML Header
    assert "---" in report
    assert "report_version: 1" in report
    assert "export_type: Summary" in report
    assert "dataset_sha256:" in report
    assert "data_quality_score:" in report
    assert "account: '***4567'" in report
    assert "broker: '[Broker Details Anonymized]'" in report

    # Check Sections
    assert "# 📊 TradeAudit Performance & Execution Intelligence — Summary Audit Report" in report
    assert "## 1. Executive Summary" in report
    assert "Audit Data Quality" in report
    assert "Evidence Fingerprint" in report
    assert "## 2. Strategy Edge vs. Trader Execution" in report
    assert "## 3. Four-Quadrant Execution Quality Analysis" in report
    assert "## 4. Behavioral & Discipline Intelligence" in report
    assert "## 5. Risk & Stop-Loss Discipline" in report
    assert "## 10. Targeted AI Audit Questions" in report
    assert "## 🤖 Suggested System Prompt for AI Analysis" in report

    # Summary report should NOT include breakdowns or full ledger
    assert "## 6. Multi-Dimensional Performance Breakdowns" not in report
    assert "## 8. Complete Trade Ledger" not in report


def test_generate_standard_report(sample_trades, sample_account, sample_strategies):
    generator = MarkdownReportGenerator(app_version="0.1.0")
    config = ReportConfig(
        export_type=ExportType.STANDARD,
        privacy=PrivacyOptions(mask_account_number=True, hide_broker=False, mask_tickets=True)
    )

    report = generator.generate(
        trades=sample_trades,
        config=config,
        account_info=sample_account,
        strategies=sample_strategies
    )

    assert "export_type: Standard" in report
    assert "broker: 'MetaQuotes Ltd / MetaQuotes-Demo'" in report
    assert "## 6. Multi-Dimensional Performance Breakdowns" in report
    assert "### A. By Symbol" in report
    assert "### B. By Trade Direction" in report
    assert "### C. By Trading Session" in report
    assert "## 7. Execution Deviations & Strategy Violations" in report
    assert "MAX_RISK_PERCENT violated" in report
    # Full ledger should still NOT be present in Standard
    assert "## 8. Complete Trade Ledger" not in report


def test_generate_full_report(sample_trades, sample_account, sample_strategies):
    generator = MarkdownReportGenerator(app_version="0.1.0")
    config = ReportConfig(
        export_type=ExportType.FULL,
        privacy=PrivacyOptions(mask_account_number=False, hide_broker=False, mask_tickets=False)
    )

    report = generator.generate(
        trades=sample_trades,
        config=config,
        account_info=sample_account,
        strategies=sample_strategies
    )

    assert "export_type: Full" in report
    assert "account: '1234567'" in report
    assert "## 8. Complete Trade Ledger" in report
    assert "#9001" in report
    assert "#9002" in report
    assert "#9003" in report
    assert "#9004" in report


def test_report_filter_adherence(sample_trades, sample_account, sample_strategies):
    generator = MarkdownReportGenerator(app_version="0.1.0")

    # Filter only EURUSD trades
    config = ReportConfig(
        export_type=ExportType.FULL,
        filters=AnalysisFilter(symbols=["EURUSD"])
    )

    report = generator.generate(
        trades=sample_trades,
        config=config,
        account_info=sample_account,
        strategies=sample_strategies
    )

    assert "symbols: 'EURUSD'" in report
    assert "Sample Analyzed**: 2 Closed Trades" in report
    assert "EURUSD" in report
    assert "GBPUSD" not in report
    assert "XAUUSD" not in report


def test_report_strategy_and_compliance_filtering(sample_trades, sample_account, sample_strategies):
    generator = MarkdownReportGenerator(app_version="0.1.0")

    # Filter only COMPLIANT trades
    config = ReportConfig(
        export_type=ExportType.STANDARD,
        filters=AnalysisFilter(compliance_status="COMPLIANT")
    )

    report = generator.generate(
        trades=sample_trades,
        config=config,
        account_info=sample_account,
        strategies=sample_strategies
    )

    assert "compliance: 'COMPLIANT'" in report
    assert "Sample Analyzed**: 2 Closed Trades" in report


def test_report_empty_trades():
    generator = MarkdownReportGenerator(app_version="0.1.0")
    config = ReportConfig(export_type=ExportType.SUMMARY)

    report = generator.generate(trades=[], config=config)

    assert "---" in report
    assert "0 Closed Trades" in report
    assert "INSUFFICIENT SAMPLE SIZE" in report


def test_build_ai_prompt_returns_targeted_questions_and_system_prompt(sample_trades):
    generator = MarkdownReportGenerator(app_version="0.1.0")
    ai_prompt = generator.build_ai_prompt(sample_trades)

    assert "## 10. Targeted AI Audit Questions" in ai_prompt
    assert "## 🤖 Suggested System Prompt for AI Analysis" in ai_prompt
    assert "You are an elite quantitative trading coach" in ai_prompt
    assert "Core Edge Diagnosis" in ai_prompt
