"""
Domain structures and enums for core performance analytics.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List


class ProfitabilityVerdict(str, Enum):
    """Profitability verdict evaluation for a sample of trades."""
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NEGATIVE_EXPECTANCY = "NEGATIVE_EXPECTANCY"
    BREAK_EVEN = "BREAK_EVEN"
    POSITIVE_EXPECTANCY = "POSITIVE_EXPECTANCY"


@dataclass
class PerformanceMetrics:
    """Aggregated core performance analytics metrics."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0
    win_rate: float = 0.0
    loss_rate: float = 0.0
    net_profit: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: Optional[float] = None
    net_r: float = 0.0
    trades_with_r: int = 0
    avg_win_monetary: float = 0.0
    avg_loss_monetary: float = 0.0
    avg_win_r: float = 0.0
    avg_loss_r: float = 0.0
    avg_r: float = 0.0
    avg_risk_percentage: float = 0.0
    expectancy_r: float = 0.0
    expectancy_monetary: float = 0.0
    max_drawdown_r: float = 0.0
    max_drawdown_monetary: float = 0.0
    recovery_factor: Optional[float] = None
    avg_duration_minutes: Optional[float] = None
    median_duration_minutes: Optional[float] = None
    trades_with_duration: int = 0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    verdict: ProfitabilityVerdict = ProfitabilityVerdict.INSUFFICIENT_DATA
    min_sample_size: int = 30
    is_sample_sufficient: bool = False
    cumulative_r_series: List[float] = field(default_factory=list)
    drawdown_r_series: List[float] = field(default_factory=list)
    cumulative_monetary_series: List[float] = field(default_factory=list)


@dataclass
class FourQuadrantCounts:
    """Four-Quadrant classification counts and aggregate R/monetary statistics."""
    good_wins_count: int = 0
    good_wins_net_r: float = 0.0
    good_wins_profit: float = 0.0

    good_losses_count: int = 0
    good_losses_net_r: float = 0.0
    good_losses_profit: float = 0.0

    bad_wins_count: int = 0
    bad_wins_net_r: float = 0.0
    bad_wins_profit: float = 0.0

    bad_losses_count: int = 0
    bad_losses_net_r: float = 0.0
    bad_losses_profit: float = 0.0


@dataclass
class StrategyVsTraderComparison:
    """Comparative analysis metrics contrasting strategy quality against execution quality."""
    total_performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    compliant_performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    deviation_performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    emotional_performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    four_quadrants: FourQuadrantCounts = field(default_factory=FourQuadrantCounts)
    deviation_cost_r: float = 0.0
    deviation_cost_monetary: float = 0.0
    quality_verdict: str = "INSUFFICIENT_DATA"


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo trade resampling simulations."""
    simulations_count: int = 0
    horizon_trades: int = 0
    percentile_5th_r: List[float] = field(default_factory=list)
    percentile_25th_r: List[float] = field(default_factory=list)
    percentile_50th_r: List[float] = field(default_factory=list)
    percentile_75th_r: List[float] = field(default_factory=list)
    percentile_95th_r: List[float] = field(default_factory=list)
    final_r_median: float = 0.0
    final_r_5th: float = 0.0
    final_r_95th: float = 0.0
    max_drawdown_median: float = 0.0
    max_drawdown_95th: float = 0.0
    max_drawdown_worst: float = 0.0
    probability_of_ruin_threshold: float = 0.0
    probability_of_target_r: float = 0.0
    worst_consecutive_losses_95th: int = 0
    sampling_method: str = "bootstrap_with_replacement"
    assumptions: List[str] = field(default_factory=list)


class RuinRiskLevel(str, Enum):
    """Categorization of risk of ruin severity."""
    MINIMAL_RISK = "MINIMAL_RISK"
    LOW_RISK = "LOW_RISK"
    MODERATE_RISK = "MODERATE_RISK"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL_RISK = "CRITICAL_RISK"
    GUARANTEED_RUIN = "GUARANTEED_RUIN"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class RiskOfRuinAnalysis:
    """Risk of Ruin metrics based on win rate, payoff ratio, and drawdown tolerance."""
    empirical_ruin_probability: float = 0.0
    formulaic_ruin_probability: float = 0.0
    max_drawdown_tolerance_r: float = 20.0
    risk_per_trade_pct: float = 1.0
    risk_level: RuinRiskLevel = RuinRiskLevel.INSUFFICIENT_DATA
    summary_verdict: str = ""
    recommendations: List[str] = field(default_factory=list)
    simulation_horizon_trades: int = 0
    assumptions: List[str] = field(default_factory=list)


@dataclass
class RollingMetricPoint:
    """Data point in rolling trade metrics progression."""
    trade_index: int = 0
    ticket: int = 0
    win_rate: float = 0.0
    expectancy_r: float = 0.0
    profit_factor: Optional[float] = None
    avg_r: float = 0.0
    max_drawdown_r: float = 0.0


@dataclass
class RollingAnalyticsResult:
    """Rolling metrics across a sliding window of trades."""
    window_size: int = 20
    points: List[RollingMetricPoint] = field(default_factory=list)
    edge_stability_verdict: str = "INSUFFICIENT_DATA"
    stability_score: float = 0.0  # 0.0 (erratic/decaying) to 1.0 (highly consistent)
    current_expectancy_trend: str = "STABLE"


@dataclass
class BootstrapConfidenceIntervals:
    """Bootstrap 95% confidence intervals for statistical significance."""
    sample_size: int = 0
    confidence_level: float = 0.95
    win_rate_ci: tuple[float, float] = (0.0, 0.0)
    expectancy_ci: tuple[float, float] = (0.0, 0.0)
    profit_factor_ci: tuple[float, float] = (0.0, 0.0)
    avg_r_ci: tuple[float, float] = (0.0, 0.0)
    is_statistically_significant: bool = False
    warnings: List[str] = field(default_factory=list)


@dataclass
class QuantResearchResult:
    """Master container aggregating all quantitative risk and statistical research results."""
    monte_carlo: MonteCarloResult = field(default_factory=MonteCarloResult)
    risk_of_ruin: RiskOfRuinAnalysis = field(default_factory=RiskOfRuinAnalysis)
    rolling_analytics: dict[int, RollingAnalyticsResult] = field(default_factory=dict)
    confidence_intervals: BootstrapConfidenceIntervals = field(default_factory=BootstrapConfidenceIntervals)
    total_trades_analyzed: int = 0
    trades_with_r_count: int = 0


