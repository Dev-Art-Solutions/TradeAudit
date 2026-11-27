"""
Markdown and AI-Ready Report Generation Service for TradeAudit.
Produces structured, comprehensive Markdown reports (Summary, Standard, Full)
incorporating performance metrics, strategy compliance, behavioral analytics,
privacy masking, known limitations, and prompt-engineered AI queries.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
import math

from tradeaudit.domain.models import (
    Trade,
    MT5AccountInfo,
    Strategy,
    ComplianceStatus,
    EmotionTag,
    BehaviorFlagType,
    UserBehaviorAction
)
from tradeaudit.domain.analytics import (
    PerformanceMetrics,
    StrategyVsTraderComparison,
    ProfitabilityVerdict
)
from tradeaudit.domain.filters import (
    AnalysisFilter,
    FilterEvaluator,
    PeriodPreset,
    DirectionFilter,
    ResultFilter
)
from tradeaudit.domain.report import (
    ExportType,
    PrivacyOptions,
    ReportConfig
)
from tradeaudit.app.services.performance_analyzer import PerformanceAnalyzer
from tradeaudit.app.services.strategy_trader_comparator import StrategyTraderComparator
from tradeaudit.app.services.breakdown_analyzer import BreakdownAnalyzer, AdvancedBreakdownResults
from tradeaudit.app.services.data_quality_analyzer import DataQualityAnalyzer, DataQualityReport
from tradeaudit.app.services.audit_snapshot_service import AuditSnapshotService, AuditSnapshot
from tradeaudit.app.services.quant_research_analyzer import QuantResearchAnalyzer
from tradeaudit.domain.analytics import QuantResearchResult


class MarkdownReportGenerator:
    """Service to generate structured, formatted Markdown reports for AI analysis and journaling."""

    def __init__(self, app_version: str = "0.1.0"):
        self.app_version = app_version

    def generate(
        self,
        trades: List[Trade],
        config: Optional[ReportConfig] = None,
        account_info: Optional[MT5AccountInfo] = None,
        strategies: Optional[Dict[int, Strategy]] = None
    ) -> str:
        """
        Generate a complete Markdown report based on trades, configuration, and account context.

        :param trades: Full or pre-filtered list of Trade domain objects.
        :param config: Report configuration (ExportType, filters, privacy options).
        :param account_info: MT5AccountInfo instance for account metadata (optional).
        :param strategies: Mapping of strategy_id -> Strategy instance (optional).
        :return: Formatted Markdown report string.
        """
        config = config or ReportConfig(app_version=self.app_version)
        strategy_map = strategies or {}

        # 1. Apply active filters
        filtered_trades = FilterEvaluator.apply(trades, config.filters)
        closed_trades = [t for t in filtered_trades if t.status and t.status.upper() == "CLOSED"]

        # 2. Compute performance metrics and comparative models
        metrics = PerformanceAnalyzer.analyze(closed_trades)
        comparison = StrategyTraderComparator.compare(closed_trades)
        breakdowns = BreakdownAnalyzer.analyze_all(closed_trades)
        quality = DataQualityAnalyzer.analyze(closed_trades)
        snapshot = AuditSnapshotService.build(closed_trades, self.app_version)
        quant_result: Optional[QuantResearchResult] = None
        if len(closed_trades) >= 3 and any(t.realized_r is not None for t in closed_trades):
            try:
                quant_result = QuantResearchAnalyzer().analyze_quant_research(closed_trades)
            except Exception:
                quant_result = None

        # 3. Assemble report sections
        sections: List[str] = []

        # YAML Frontmatter
        sections.append(self._build_metadata_header(config, account_info, quality, snapshot))

        # Title
        title_suffix = f" — {config.export_type.value} Audit Report"
        sections.append(f"# 📊 TradeAudit Performance & Execution Intelligence{title_suffix}\n")

        # Executive Summary
        sections.append(self._build_executive_summary(
            metrics, comparison, len(closed_trades), len(filtered_trades), quality, snapshot
        ))

        # Strategy vs Trader Execution Quality
        sections.append(self._build_strategy_trader_section(comparison))

        # Four-Quadrant Analysis
        sections.append(self._build_four_quadrant_section(comparison))

        # Behavioral & Discipline Analysis
        sections.append(self._build_behavioral_section(closed_trades, comparison))

        # Risk & Drawdown Discipline
        sections.append(self._build_risk_discipline_section(metrics, closed_trades))

        # Quantitative Risk & Capital Preservation Section
        if quant_result is not None:
            sections.append(self._build_quant_section(quant_result))

        # Standard and Full depth sections
        if config.export_type in (ExportType.STANDARD, ExportType.FULL):
            sections.append(self._build_breakdown_sections(breakdowns))
            sections.append(self._build_deviations_section(closed_trades, strategy_map, config.privacy))

        # Full depth sections
        if config.export_type == ExportType.FULL:
            sections.append(self._build_trade_ledger_table(closed_trades, strategy_map, config.privacy))

        # Known Limitations
        sections.append(self._build_known_limitations(metrics, closed_trades))

        # AI Analysis Questions & System Prompt
        sections.append(self._build_ai_questions_and_prompt(metrics, comparison, config))

        return "\n\n".join(sections).strip() + "\n"

    def build_ai_prompt(
        self,
        trades: List[Trade],
        config: Optional[ReportConfig] = None,
        persona: Optional[str] = None
    ) -> str:
        """Generate targeted AI audit questions and recommended system prompt."""
        cfg = config or ReportConfig()
        if persona:
            cfg.persona = persona
        filtered = FilterEvaluator.apply(trades, cfg.filters)
        closed = [t for t in filtered if t.status and t.status.upper() == "CLOSED"]
        metrics = PerformanceAnalyzer.analyze(closed)
        comparison = StrategyTraderComparator.compare(closed)
        return self._build_ai_questions_and_prompt(metrics, comparison, cfg)

    def _mask_account(self, login: int, privacy: PrivacyOptions) -> str:
        if not login:
            return "N/A"
        if not privacy.mask_account_number:
            return str(login)
        s = str(login)
        if len(s) <= 4:
            return "****"
        return f"***{s[-4:]}"

    def _mask_broker(self, server: str, company: str, privacy: PrivacyOptions) -> str:
        if not privacy.hide_broker:
            parts = [p for p in (company, server) if p]
            return " / ".join(parts) if parts else "Unknown Broker"
        return "[Broker Details Anonymized]"

    def _mask_ticket(self, position_id: int, privacy: PrivacyOptions) -> str:
        if not position_id:
            return "POS-000"
        if not privacy.mask_tickets:
            return f"#{position_id}"
        return f"T-{str(position_id)[-4:]}"

    def _build_metadata_header(
        self,
        config: ReportConfig,
        account_info: Optional[MT5AccountInfo],
        quality: Optional[DataQualityReport] = None,
        snapshot: Optional[AuditSnapshot] = None,
    ) -> str:
        gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        acc_str = self._mask_account(account_info.login if account_info else 0, config.privacy)
        broker_str = self._mask_broker(
            account_info.server if account_info else "",
            account_info.company if account_info else "",
            config.privacy
        )

        sym_str = ", ".join(config.filters.symbols) if config.filters.symbols else "ALL"
        strat_str = str(config.filters.strategy_id) if config.filters.strategy_id is not None else "ALL"
        comp_str = config.filters.compliance_status or "ALL"
        sha_str = snapshot.dataset_sha256 if snapshot else "N/A"
        q_score = quality.score if quality else 0
        q_grade = quality.grade if quality else "N/A"

        return f"""---
report_version: {config.report_version}
application: TradeAudit
app_version: {self.app_version}
export_type: {config.export_type.value}
generated_at: '{gen_time}'
dataset_sha256: '{sha_str}'
data_quality_score: {q_score}
data_quality_grade: '{q_grade}'
account: '{acc_str}'
broker: '{broker_str}'
filters_applied:
  period: '{config.filters.period.value}'
  direction: '{config.filters.direction.value}'
  symbols: '{sym_str}'
  strategy: '{strat_str}'
  compliance: '{comp_str}'
  result: '{config.filters.result.value}'
---"""

    def _build_executive_summary(
        self,
        m: PerformanceMetrics,
        c: StrategyVsTraderComparison,
        closed_count: int,
        total_count: int,
        quality: Optional[DataQualityReport] = None,
        snapshot: Optional[AuditSnapshot] = None,
    ) -> str:
        verdict_badge = {
            ProfitabilityVerdict.POSITIVE_EXPECTANCY: "🟢 **POSITIVE EXPECTANCY (Profitable Edge)**",
            ProfitabilityVerdict.BREAK_EVEN: "🟡 **BREAK-EVEN (Marginal Edge)**",
            ProfitabilityVerdict.NEGATIVE_EXPECTANCY: "🔴 **NEGATIVE EXPECTANCY (Unprofitable / Risk of Ruin)**",
            ProfitabilityVerdict.INSUFFICIENT_DATA: "⚪ **INSUFFICIENT SAMPLE SIZE (< 30 trades)**",
        }.get(m.verdict, str(m.verdict.value))

        lines = [
            "## 1. Executive Summary",
            "",
            f"**Audit Verdict**: {verdict_badge}",
            f"**Sample Analyzed**: {closed_count} Closed Trades (out of {total_count} total positions)",
            "",
            "| Core KPI | Value | Status / Note |",
            "| :--- | :--- | :--- |",
            f"| **Net Profit / Loss** | `${m.net_profit:,.2f}` | Gross Profit: `${m.gross_profit:,.2f}`, Gross Loss: `${m.gross_loss:,.2f}` |",
            f"| **Net Realized R** | `{m.net_r:+.2f}R` | Based on initial Stop-Loss monetary risk |",
            f"| **Win Rate** | `{m.win_rate * 100:.1f}%` | {m.winning_trades} Wins / {m.losing_trades} Losses / {m.breakeven_trades} BE |",
            f"| **Profit Factor** | `{m.profit_factor if m.profit_factor is not None else 'N/A'}` | Ideal benchmark: > 1.50 |",
            f"| **Expectancy (R)** | `{m.expectancy_r:+.2f}R` / trade | Average expected R return per execution |",
            f"| **Expectancy ($)** | `${m.expectancy_monetary:+,.2f}` / trade | Average monetary expected return |",
            f"| **System Quality Number (SQN)** | `{f'{m.sqn:.2f} ({m.sqn_rating})' if m.sqn is not None else 'N/A'}` | Van Tharp SQN statistical score |",
            f"| **Average Winner** | `{m.avg_win_r:+.2f}R` (${m.avg_win_monetary:,.2f}) | Win / Loss payoff ratio |",
            f"| **Average Loser** | `{m.avg_loss_r:+.2f}R` (${m.avg_loss_monetary:,.2f}) | Average risk realization |",
            f"| **Max Drawdown (R)** | `{m.max_drawdown_r:.2f}R` | Peak-to-trough drawdown in R |",
            f"| **Max Drawdown Duration** | `{m.max_drawdown_duration_trades} trades` ({m.max_drawdown_duration_days:.1f}d) | Peak-to-recovery horizon |",
            f"| **Max Drawdown ($)** | `${m.max_drawdown_monetary:,.2f}` | Peak-to-trough monetary drawdown |",
            f"| **Recovery Factor** | `{m.recovery_factor if m.recovery_factor is not None else 'N/A'}` | Net profit / absolute maximum monetary drawdown |",
            f"| **Trade Duration** | `{m.avg_duration_minutes if m.avg_duration_minutes is not None else 'N/A'} min avg` | {m.trades_with_duration}/{m.total_trades} closed trades have valid timestamps |",
            f"| **Consecutive Streaks** | `{m.max_consecutive_wins} Wins` / `{m.max_consecutive_losses} Losses` | Max streak duration |",
        ]
        if quality:
            lines.append(f"| **Audit Data Quality** | `{quality.score}/100 ({quality.grade})` | {quality.summary} |")
        if snapshot:
            lines.append(f"| **Evidence Fingerprint** | `{snapshot.dataset_sha256[:16]}...{snapshot.dataset_sha256[-12:]}` | SHA-256 verifiable dataset hash |")
        return "\n".join(lines)

    def _build_strategy_trader_section(self, c: StrategyVsTraderComparison) -> str:
        tot = c.total_performance
        comp = c.compliant_performance
        dev = c.deviation_performance
        emo = c.emotional_performance

        verdict_descriptions = {
            "HIGH_DISCIPLINE": "✅ **High Discipline**: Deviations are minimal and do not hurt overall profitability.",
            "EXECUTION_BREAKDOWN": "⚠️ **Execution Breakdown**: The underlying strategy is statistically profitable, but execution violations and emotional deviations are wiping out substantial R.",
            "FLAWED_STRATEGY_LUCKY_DEVIATIONS": "⚠️ **Unprofitable Strategy**: Compliant trades are negative; short-term gains stem from lucky rule deviations.",
            "FLAWED_STRATEGY_AND_EXECUTION": "🔴 **Flawed Strategy & Broken Discipline**: Both rules adherence and discretionary overrides produce negative expectancy.",
            "ALL_TRADES_DEVIATIONS": "⚪ **No Compliant Trades**: All evaluated trades had rule violations or were unassigned.",
            "BALANCED": "ℹ️ **Mixed / Inconclusive**: Strategy and execution metrics show mixed characteristics.",
            "NO_TRADES": "⚪ **No Closed Trades to Evaluate**"
        }
        diag = verdict_descriptions.get(c.quality_verdict, f"**Verdict**: {c.quality_verdict}")

        lines = [
            "## 2. Strategy Edge vs. Trader Execution",
            "",
            f"**Execution Diagnostic**: {diag}",
            "",
            f"> **💸 Cost of Deviations**: `{c.deviation_cost_r:+.2f}R` (`${c.deviation_cost_monetary:+,.2f}`)",
            "> *(Difference in performance between pure rule compliance and actual realized outcome)*",
            "",
            "| Execution Subset | Trades | Win Rate | Net P/L ($) | Net R | Expectancy (R) | Profit Factor | Max DD (R) |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            f"| **Overall Actual** | {tot.total_trades} | {tot.win_rate*100:.1f}% | ${tot.net_profit:,.2f} | {tot.net_r:+.2f}R | {tot.expectancy_r:+.2f}R | {tot.profit_factor if tot.profit_factor is not None else 'N/A'} | {tot.max_drawdown_r:.2f}R |",
            f"| 🟢 **Compliant Trades** | {comp.total_trades} | {comp.win_rate*100:.1f}% | ${comp.net_profit:,.2f} | {comp.net_r:+.2f}R | {comp.expectancy_r:+.2f}R | {comp.profit_factor if comp.profit_factor is not None else 'N/A'} | {comp.max_drawdown_r:.2f}R |",
            f"| 🔴 **Deviation Trades** | {dev.total_trades} | {dev.win_rate*100:.1f}% | ${dev.net_profit:,.2f} | {dev.net_r:+.2f}R | {dev.expectancy_r:+.2f}R | {dev.profit_factor if dev.profit_factor is not None else 'N/A'} | {dev.max_drawdown_r:.2f}R |",
            f"| 🧠 **Emotional / Flagged** | {emo.total_trades} | {emo.win_rate*100:.1f}% | ${emo.net_profit:,.2f} | {emo.net_r:+.2f}R | {emo.expectancy_r:+.2f}R | {emo.profit_factor if emo.profit_factor is not None else 'N/A'} | {emo.max_drawdown_r:.2f}R |"
        ]
        return "\n".join(lines)

    def _build_four_quadrant_section(self, c: StrategyVsTraderComparison) -> str:
        q = c.four_quadrants
        total_q = q.good_wins_count + q.good_losses_count + q.bad_wins_count + q.bad_losses_count
        gw_pct = (q.good_wins_count / total_q * 100) if total_q > 0 else 0.0
        gl_pct = (q.good_losses_count / total_q * 100) if total_q > 0 else 0.0
        bw_pct = (q.bad_wins_count / total_q * 100) if total_q > 0 else 0.0
        bl_pct = (q.bad_losses_count / total_q * 100) if total_q > 0 else 0.0

        lines = [
            "## 3. Four-Quadrant Execution Quality Analysis",
            "",
            "Categorizes trades by whether rules were respected vs. financial outcome:",
            "",
            f"> **🎯 Process Adherence**: `{c.rule_adherence_rate:.1f}%` of evaluated trades strictly followed strategy rules.",
            f"> **🩸 Avoidable Loss Drag**: `{c.bad_loss_drag_pct:.1f}%` of all realized loss capital was drained by Quadrant IV (Bad Losses).",
            f"> **✨ Discipline Alpha**: `{c.discipline_alpha_r:+.2f}R` (`${c.discipline_alpha_monetary:+,.2f}`) potential gain from eliminating unforced rule violations.",
            "",
            "| Quadrant | Outcome Description | Count | Share (%) | Net R | Net Profit ($) | Assessment |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
            f"| 🟢 **Good Win** | Strategy Followed + Win | {q.good_wins_count} | {gw_pct:.1f}% | `{q.good_wins_net_r:+.2f}R` | ${q.good_wins_profit:,.2f} | Ideal Execution & Positive Outcome |",
            f"| 🔵 **Good Loss** | Strategy Followed + Loss | {q.good_losses_count} | {gl_pct:.1f}% | `{q.good_losses_net_r:+.2f}R` | ${q.good_losses_profit:,.2f} | Acceptable Cost of Doing Business |",
            f"| 🟡 **Bad Win** | Strategy Violated + Win | {q.bad_wins_count} | {bw_pct:.1f}% | `{q.bad_wins_net_r:+.2f}R` | ${q.bad_wins_profit:,.2f} | Dangerous Positive Reinforcement |",
            f"| 🔴 **Bad Loss** | Strategy Violated + Loss | {q.bad_losses_count} | {bl_pct:.1f}% | `{q.bad_losses_net_r:+.2f}R` | ${q.bad_losses_profit:,.2f} | Pure Waste / Avoidable Leak |"
        ]
        return "\n".join(lines)

    def _build_behavioral_section(self, trades: List[Trade], c: StrategyVsTraderComparison) -> str:
        # Collect emotion tags
        emotion_counts: Dict[str, int] = {}
        flag_counts: Dict[str, int] = {}
        confirmed_count = 0
        rejected_count = 0
        unreviewed_count = 0

        for t in trades:
            if t.emotion_tag:
                emotion_counts[t.emotion_tag] = emotion_counts.get(t.emotion_tag, 0) + 1
            if t.user_behavior_action == UserBehaviorAction.CONFIRMED.value:
                confirmed_count += 1
            elif t.user_behavior_action == UserBehaviorAction.REJECTED.value:
                rejected_count += 1
            else:
                unreviewed_count += 1

            for flag in t.auto_behavior_flags:
                flag_name = flag.flag_type.value if hasattr(flag.flag_type, 'value') else str(flag.flag_type)
                flag_counts[flag_name] = flag_counts.get(flag_name, 0) + 1

        lines = [
            "## 4. Behavioral & Discipline Intelligence",
            "",
            "### Automatic Discipline Flags Detected",
            ""
        ]

        if flag_counts:
            lines.extend([
                "| Detected Behavioral Pattern | Occurrences | Pattern Significance |",
                "| :--- | :--- | :--- |"
            ])
            flag_meanings = {
                "POSSIBLE_REVENGE_TRADE": "Entered rapidly after a loss to make back money",
                "POSSIBLE_FOMO": "Chased price extension or entered impulsively without setup",
                "OVERTRADING": "Exceeded daily frequency limit or excessive concurrent exposures",
                "RISK_ESCALATION": "Increased position sizing / lot size significantly after drawdown",
                "SL_MOVED_AWAY": "Widened or removed Stop-Loss during adverse price excursion",
            }
            for flag, cnt in sorted(flag_counts.items(), key=lambda x: -x[1]):
                meaning = flag_meanings.get(flag, "Algorithmic behavioral irregularity")
                lines.append(f"| ⚠️ **{flag}** | {cnt} trades | {meaning} |")
        else:
            lines.append("✅ *No automatic behavioral anomalies detected in this dataset.*")

        lines.extend([
            "",
            "### Emotional State Distribution (User Self-Tags)",
            ""
        ])

        if emotion_counts:
            lines.extend([
                "| Emotional State | Count | Percentage |",
                "| :--- | :--- | :--- |"
            ])
            total_tags = sum(emotion_counts.values())
            for emo, cnt in sorted(emotion_counts.items(), key=lambda x: -x[1]):
                pct = (cnt / total_tags * 100) if total_tags > 0 else 0.0
                lines.append(f"| **{emo}** | {cnt} | {pct:.1f}% |")
        else:
            lines.append("ℹ️ *No user emotion tags logged.*")

        return "\n".join(lines)

    def _build_risk_discipline_section(self, m: PerformanceMetrics, trades: List[Trade]) -> str:
        # Calculate R distribution bins
        r_bins = {
            "> +3.0R": 0,
            "+2.0R to +3.0R": 0,
            "+1.0R to +2.0R": 0,
            "0.0R to +1.0R": 0,
            "Breakeven (0.0R)": 0,
            "-0.0R to -1.0R": 0,
            "-1.0R to -2.0R": 0,
            "< -2.0R (Severe Leak)": 0,
            "Unknown R (No Initial SL)": 0
        }

        for t in trades:
            if t.realized_r is None:
                r_bins["Unknown R (No Initial SL)"] += 1
            elif t.realized_r > 3.0:
                r_bins["> +3.0R"] += 1
            elif 2.0 < t.realized_r <= 3.0:
                r_bins["+2.0R to +3.0R"] += 1
            elif 1.0 < t.realized_r <= 2.0:
                r_bins["+1.0R to +2.0R"] += 1
            elif 0.0 < t.realized_r <= 1.0:
                r_bins["0.0R to +1.0R"] += 1
            elif t.realized_r == 0.0:
                r_bins["Breakeven (0.0R)"] += 1
            elif -1.0 <= t.realized_r < 0.0:
                r_bins["-0.0R to -1.0R"] += 1
            elif -2.0 <= t.realized_r < -1.0:
                r_bins["-1.0R to -2.0R"] += 1
            else:
                r_bins["< -2.0R (Severe Leak)"] += 1

        lines = [
            "## 5. Risk & Stop-Loss Discipline",
            "",
            f"- **Average Risk Per Trade**: `{m.avg_risk_percentage:.2f}%` of account equity",
            f"- **Trades with Defined Initial Risk (R)**: `{m.trades_with_r} / {len(trades)}` ({m.trades_with_r/len(trades)*100:.1f}%)" if trades else "- No trades",
            f"- **Missing Initial Stop-Loss**: `{r_bins['Unknown R (No Initial SL)']} trades` *(Trades without SL have undefined 1R risk)*",
            "",
            "### Realized R Distribution",
            "",
            "| R-Multiple Bracket | Trade Count | Distribution (%) |",
            "| :--- | :--- | :--- |"
        ]

        total_trades = len(trades)
        for bracket, cnt in r_bins.items():
            if cnt > 0:
                pct = (cnt / total_trades * 100) if total_trades > 0 else 0.0
                lines.append(f"| `{bracket}` | {cnt} | {pct:.1f}% |")

        return "\n".join(lines)

    def _build_quant_section(self, q: QuantResearchResult) -> str:
        """Build institutional quantitative risk, tail risk, and capital preservation section."""
        lines = [
            "## 6. Quantitative Risk Research & Capital Preservation",
            "",
            "| Institutional Metric | Value | Description |",
            "| :--- | :--- | :--- |",
            f"| **Sharpe Ratio (R)** | `{q.sharpe_ratio_r:.2f}` | Mean R / StdDev R per trade |",
            f"| **Sortino Ratio (R)** | `{q.sortino_ratio_r:.2f}` | Downside risk adjusted deviation |",
            f"| **Calmar Ratio (R)** | `{q.calmar_ratio_r:.2f}` | Total Net R / Historical Max DD R |",
            f"| **Historical VaR (95%)** | `{q.var_95_r:.2f}R` | 95% single-trade Value at Risk |",
            f"| **Expected Shortfall (CVaR 95%)** | `{q.cvar_95_r:.2f}R` | Average tail loss beyond 95% VaR |",
            f"| **Full Kelly Optimal Growth (f*)** | `{q.kelly_criterion_pct:.1f}%` | Theoretical optimal position sizing |",
            f"| **Recommended Half-Kelly** | `{q.half_kelly_pct:.1f}%` | Institutional safe sizing allocation |"
        ]

        if q.ruin_matrix:
            matrix = q.ruin_matrix
            lines.extend([
                "",
                "### Risk of Ruin Sensitivity Matrix",
                "",
                f"**Capital Preservation Resilience Score**: `{matrix.capital_preservation_score:.0f}/100`  ",
                f"**Recommended Optimal Risk Allocation**: `{matrix.optimal_risk_pct:.1f}%` per trade  ",
                "",
                "| Risk / Trade | 10% DD Ruin | 20% DD Ruin | 30% DD Ruin | 50% DD Ruin |",
                "| :--- | :--- | :--- | :--- | :--- |"
            ])
            for r_pct in matrix.risk_per_trade_options:
                row_cells = []
                for dd_pct in matrix.drawdown_options:
                    cell = next(
                        (c for c in matrix.cells if abs(c.risk_per_trade_pct - r_pct) < 1e-4 and abs(c.drawdown_pct - dd_pct) < 1e-4),
                        None
                    )
                    if cell:
                        row_cells.append(f"{cell.ruin_probability:.1f}% ({cell.consecutive_losses_to_ruin} losses)")
                    else:
                        row_cells.append("—")
                lines.append(f"| **{r_pct:.1f}%** | " + " | ".join(row_cells) + " |")

        return "\n".join(lines)

    def _build_breakdown_sections(self, b: AdvancedBreakdownResults) -> str:
        lines = [
            "## 7. Multi-Dimensional Performance Breakdowns",
            "",
            "### A. By Symbol",
            "",
            "| Symbol | Trades | Win Rate | Net P/L ($) | Net R | Expectancy (R) | Profit Factor | Max DD (R) |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        for sym, sm in sorted(b.by_symbol.items()):
            lines.append(
                f"| **{sym}** | {sm.total_trades} | {sm.win_rate*100:.1f}% | ${sm.net_profit:,.2f} | {sm.net_r:+.2f}R | {sm.expectancy_r:+.2f}R | {sm.profit_factor if sm.profit_factor is not None else 'N/A'} | {sm.max_drawdown_r:.2f}R |"
            )

        lines.extend([
            "",
            "### B. By Trade Direction",
            "",
            "| Direction | Trades | Win Rate | Net P/L ($) | Net R | Expectancy (R) | Profit Factor |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ])

        for d, dm in b.by_direction.items():
            lines.append(
                f"| **{d}** | {dm.total_trades} | {dm.win_rate*100:.1f}% | ${dm.net_profit:,.2f} | {dm.net_r:+.2f}R | {dm.expectancy_r:+.2f}R | {dm.profit_factor if dm.profit_factor is not None else 'N/A'} |"
            )

        lines.extend([
            "",
            "### C. By Trading Session",
            "",
            "| Session | Trades | Win Rate | Net P/L ($) | Net R | Expectancy (R) |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ])

        for sess, sem in b.by_session.items():
            if sem.total_trades > 0:
                lines.append(
                    f"| **{sess}** | {sem.total_trades} | {sem.win_rate*100:.1f}% | ${sem.net_profit:,.2f} | {sem.net_r:+.2f}R | {sem.expectancy_r:+.2f}R |"
                )

        lines.extend([
            "",
            "### D. Post-Win vs. Post-Loss Context",
            "",
            "| Context | Trades | Win Rate | Net P/L ($) | Net R | Expectancy (R) |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ])

        for ctx, cm in b.by_context.items():
            if cm.total_trades > 0:
                lines.append(
                    f"| **{ctx}** | {cm.total_trades} | {cm.win_rate*100:.1f}% | ${cm.net_profit:,.2f} | {cm.net_r:+.2f}R | {cm.expectancy_r:+.2f}R |"
                )

        if getattr(b, "by_duration", None):
            lines.extend([
                "",
                "### E. By Holding Duration Horizon",
                "",
                "| Holding Horizon | Trades | Win Rate | Net P/L ($) | Net R | Expectancy (R) | Profit Factor |",
                "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
            ])
            dur_labels = {
                "SCALP_UNDER_5M": "Scalp (< 5m)",
                "INTRADAY_5M_TO_1H": "Intraday (5m - 1h)",
                "INTRADAY_1H_TO_4H": "Intraday (1h - 4h)",
                "SESSION_4H_TO_1D": "Session (4h - 24h)",
                "SWING_OVER_1D": "Swing (> 24h)"
            }
            for dur_k, dur_m in b.by_duration.items():
                if dur_m.total_trades > 0:
                    lbl = dur_labels.get(dur_k, dur_k)
                    pf = f"{dur_m.profit_factor:.2f}" if dur_m.profit_factor is not None else "N/A"
                    lines.append(
                        f"| **{lbl}** | {dur_m.total_trades} | {dur_m.win_rate*100:.1f}% | ${dur_m.net_profit:,.2f} | {dur_m.net_r:+.2f}R | {dur_m.expectancy_r:+.2f}R | {pf} |"
                    )

        if getattr(b, "by_strategy", None):
            active_strats = {k: v for k, v in b.by_strategy.items() if v.total_trades > 0}
            if active_strats:
                lines.extend([
                    "",
                    "### F. By Strategy Assignment",
                    "",
                    "| Strategy | Trades | Win Rate | Net P/L ($) | Net R | Expectancy (R) | Profit Factor |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
                ])
                for s_name, s_m in active_strats.items():
                    pf = f"{s_m.profit_factor:.2f}" if s_m.profit_factor is not None else "N/A"
                    lines.append(
                        f"| **{s_name}** | {s_m.total_trades} | {s_m.win_rate*100:.1f}% | ${s_m.net_profit:,.2f} | {s_m.net_r:+.2f}R | {s_m.expectancy_r:+.2f}R | {pf} |"
                    )

        if getattr(b, "by_compliance", None):
            active_comp = {k: v for k, v in b.by_compliance.items() if v.total_trades > 0}
            if active_comp:
                lines.extend([
                    "",
                    "### G. By Strategy Compliance Status",
                    "",
                    "| Compliance Status | Trades | Win Rate | Net P/L ($) | Net R | Expectancy (R) | Profit Factor |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
                ])
                comp_labels = {
                    "COMPLIANT": "🎯 Fully Compliant",
                    "PARTIAL": "⚠️ Partial Compliance",
                    "DEVIATION": "❌ Rule Violation / Deviation",
                    "UNCHECKED": "⚪ Unchecked / Discretionary"
                }
                for c_k, c_m in active_comp.items():
                    pf = f"{c_m.profit_factor:.2f}" if c_m.profit_factor is not None else "N/A"
                    lbl = comp_labels.get(c_k, c_k)
                    lines.append(
                        f"| **{lbl}** | {c_m.total_trades} | {c_m.win_rate*100:.1f}% | ${c_m.net_profit:,.2f} | {c_m.net_r:+.2f}R | {c_m.expectancy_r:+.2f}R | {pf} |"
                    )

        return "\n".join(lines)

    def _build_deviations_section(
        self,
        trades: List[Trade],
        strategy_map: Dict[int, Strategy],
        privacy: PrivacyOptions
    ) -> str:
        dev_trades = [
            t for t in trades
            if t.compliance_status in (ComplianceStatus.DEVIATION.value, ComplianceStatus.PARTIAL.value)
        ]

        lines = [
            "## 8. Execution Deviations & Strategy Violations",
            "",
            f"**Total Rule Deviations**: `{len(dev_trades)} trades`"
        ]

        if not dev_trades:
            lines.append("\n✅ *Zero execution rule violations recorded in this dataset.*")
            return "\n".join(lines)

        lines.extend([
            "",
            "| Ticket | Symbol | Direction | Close Time | Strategy | Deviation Reason & Violations | Net R | Outcome ($) |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ])

        for t in dev_trades[:25]:  # Cap at top 25 for legibility
            t_id = self._mask_ticket(t.position_id, privacy)
            strat = strategy_map.get(t.strategy_id or 0)
            strat_name = strat.name if strat else f"ID #{t.strategy_id or 0}"
            time_str = t.close_time.strftime("%Y-%m-%d %H:%M") if t.close_time else "N/A"
            r_str = f"{t.realized_r:+.2f}R" if t.realized_r is not None else "N/A"
            reason = t.deviation_reason or t.compliance_details or "Unspecified rule violation"

            lines.append(
                f"| `{t_id}` | {t.symbol} | {t.direction} | {time_str} | {strat_name} | {reason} | `{r_str}` | `${t.net_profit:,.2f}` |"
            )

        if len(dev_trades) > 25:
            lines.append(f"\n*(Truncated: {len(dev_trades) - 25} additional deviation trades omitted for brevity)*")

        return "\n".join(lines)

    def _build_trade_ledger_table(
        self,
        trades: List[Trade],
        strategy_map: Dict[int, Strategy],
        privacy: PrivacyOptions
    ) -> str:
        lines = [
            "## 9. Complete Trade Ledger",
            "",
            f"**Total Positions Logged**: `{len(trades)}`",
            "",
            "| Ticket | Open Time | Symbol | Dir | Lots | Entry | Exit | Net P/L ($) | Realized R | Compliance | Emotion |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        for t in trades:
            t_id = self._mask_ticket(t.position_id, privacy)
            open_str = t.open_time.strftime("%Y-%m-%d %H:%M") if t.open_time else "N/A"
            dir_str = t.direction or "BUY"
            vol_str = f"{t.volume:.2f}"
            entry_str = f"{t.open_price:.5g}"
            exit_str = f"{t.close_price:.5g}" if t.close_price is not None else "Open"
            profit_str = f"${t.net_profit:,.2f}"
            r_str = f"{t.realized_r:+.2f}R" if t.realized_r is not None else "N/A"
            comp_str = t.compliance_status or "UNCHECKED"
            emo_str = t.emotion_tag or "-"

            lines.append(
                f"| `{t_id}` | {open_str} | {t.symbol} | {dir_str} | {vol_str} | {entry_str} | {exit_str} | {profit_str} | `{r_str}` | {comp_str} | {emo_str} |"
            )

        return "\n".join(lines)

    def _build_known_limitations(self, m: PerformanceMetrics, trades: List[Trade]) -> str:
        limitations = []

        if not m.is_sample_sufficient:
            limitations.append(
                f"- ⚠️ **Small Sample Size Warning**: Dataset has only {len(trades)} trades (minimum required: {m.min_sample_size}). Expectancy and Win Rate are subject to high statistical variance."
            )

        missing_sl_count = sum(1 for t in trades if t.initial_sl is None or t.initial_sl == 0.0)
        if missing_sl_count > 0:
            limitations.append(
                f"- ⚠️ **Missing Initial Stop-Loss**: {missing_sl_count} trades have undefined initial SL. Realized R cannot be calculated for these positions, defaulting to monetary P/L analysis."
            )

        if not limitations:
            limitations.append("- ✅ Dataset has adequate sample size (> 30 trades) and complete initial risk definitions.")

        lines = [
            "## 10. Data Integrity & Known Limitations",
            ""
        ]
        lines.extend(limitations)
        return "\n".join(lines)

    def _build_ai_questions_and_prompt(
        self,
        m: PerformanceMetrics,
        c: StrategyVsTraderComparison,
        config: ReportConfig
    ) -> str:
        persona_key = (getattr(config, "persona", None) or "quant").lower()

        PERSONAS = {
            "quant": {
                "title": "Quantitative Edge & Risk Officer",
                "questions": [
                    "1. **Core Edge Diagnosis**: Is my trading edge statistically sound in compliant setups, or am I reliant on high win-rate / low R:R overrides?",
                    "2. **Cost of Deviations**: How much of my account drawdown is directly attributable to rule violations and behavioral leaks vs. normal strategy variance?",
                    "3. **Contextual Weaknesses**: Which specific symbols, trading sessions, or post-loss emotional sequences create the highest downside risk?",
                    "4. **Actionable Remediation Plan**: What 3 concrete discipline rules or risk-management constraints should I enforce immediately to maximize Net R?"
                ],
                "prompt": (
                    "You are an elite quantitative trading coach, institutional risk manager, and behavioral finance auditor.\n"
                    "Analyze the attached TradeAudit performance report for a MetaTrader 5 trader.\n\n"
                    "Your objectives:\n"
                    "1. Separate strategy performance (Compliant trades) from execution discipline (Deviations / Emotional trades).\n"
                    "2. Quantify the exact financial impact of deviations (Deviation Cost R).\n"
                    "3. Identify behavioral leakage patterns (revenge trading, FOMO, overtrading, widening SL).\n"
                    "4. Deliver an uncompromising, constructive audit with a prioritized 3-step action plan to improve Expectancy."
                )
            },
            "prop_firm": {
                "title": "Prop Firm Challenge & Evaluation Auditor",
                "questions": [
                    "1. **Drawdown Breach Risk**: What is the maximum daily and trailing drawdown observed, and what is the statistical probability of breaching a 5% daily / 10% max limit based on my loss streaks?",
                    "2. **Consistency Score**: Are my profits overly clustered in 1-2 outlier trades, or is the gain distributed evenly across compliant setups?",
                    "3. **Martingale & Risk Escalation**: Did lot sizes or risk escalate after losses, endangering the evaluation account rules?",
                    "4. **Challenge Action Plan**: What lot-sizing ceiling and maximum daily trade stop should I lock in to pass a 2-step evaluation with 95% confidence?"
                ],
                "prompt": (
                    "You are a strict Prop Firm Risk Auditor and Evaluation Officer specializing in FTMO, FundedNext, and institutional evaluation guidelines.\n"
                    "Audit the attached TradeAudit report for a trader preparing for or trading a funded challenge account.\n\n"
                    "Your objectives:\n"
                    "1. Stress-test maximum daily drawdown and trailing loss against strict 5% daily / 10% maximum drawdown limits.\n"
                    "2. Evaluate consistency rules: assess whether any single trade generates > 30% of total profit.\n"
                    "3. Audit lot sizing and risk escalation: flag any revenge trading, Martingale lot doubling, or weekend holding risks.\n"
                    "4. Provide a fail-safe risk parameter rule sheet (max lots, max daily trades, hard stop per day)."
                )
            },
            "psychology": {
                "title": "Trading Psychologist & Discipline Mentor",
                "questions": [
                    "1. **Emotional Degradation Cycle**: How significantly does my win rate and average R drop after taking a loss or entering a drawdown streak?",
                    "2. **Loss Aversion & SL Widening**: Is there evidence of moving stop-losses away or holding losers too long compared to cutting them systematically?",
                    "3. **FOMO & Impulsive Entries**: Which session or market condition triggers the majority of impulsive unverified trades?",
                    "4. **Mindset Protocol**: What pre-session ritual and post-loss circuit breaker rule should I implement to prevent emotional tilt?"
                ],
                "prompt": (
                    "You are a specialized Performance Psychologist and Trading Discipline Mentor inspired by Mark Douglas and Jared Tendler.\n"
                    "Review the attached TradeAudit journal dossier focusing on emotional regulation and execution psychology.\n\n"
                    "Your objectives:\n"
                    "1. Analyze emotional tags and behavioral flags (FOMO, Revenge, Greed, Fear) to find the primary psychological leak.\n"
                    "2. Identify the emotional degradation sequence: calculate the performance delta on trades executed within 60 minutes of a losing trade.\n"
                    "3. Diagnose cognitive biases: loss aversion (moving SL), gambler's fallacy (increasing risk during streaks), and outcome bias.\n"
                    "4. Build an actionable 3-part psychological circuit breaker to halt tilt before capital is damaged."
                )
            }
        }

        persona = PERSONAS.get(persona_key, PERSONAS["quant"])

        lines = [
            f"## 11. Targeted AI Audit Questions ({persona['title']})",
            "",
            "Please paste this entire report into ChatGPT, Claude, or your LLM of choice, and ask:",
            ""
        ]
        lines.extend(persona["questions"])
        lines.extend([
            "",
            "---",
            "",
            f"## 🤖 Suggested System Prompt for AI Analysis ({persona['title']})",
            "",
            "```text",
            persona["prompt"],
            "```"
        ])
        return "\n".join(lines)
