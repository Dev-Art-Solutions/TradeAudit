"""
Quantitative Risk Research and Advanced Statistical Analytics Engine.

Provides:
- Monte Carlo Resampling Simulations (trajectory envelopes, MDD distribution, ruin probability)
- Risk of Ruin Analysis (formulaic Brownian approximation & empirical simulation)
- Rolling Window Performance & Edge Stability Analytics
- Bootstrap 95% Confidence Intervals & Statistical Significance
"""

import math
import random
import statistics
from typing import Sequence, List, Dict, Optional, Tuple

from tradeaudit.domain.models import Trade
from tradeaudit.domain.analytics import (
    MonteCarloResult,
    RuinRiskLevel,
    RiskOfRuinAnalysis,
    RollingMetricPoint,
    RollingAnalyticsResult,
    BootstrapConfidenceIntervals,
    QuantResearchResult
)


class QuantResearchAnalyzer:
    """Quantitative risk research and statistical simulation service."""

    @staticmethod
    def _extract_closed_r_multiples(trades: Sequence[Trade]) -> List[float]:
        """Extract list of realized R multiples from closed trades with valid R."""
        return [
            float(t.realized_r)
            for t in trades
            if t.status and t.status.upper() == "CLOSED" and t.realized_r is not None
        ]

    def run_monte_carlo(
        self,
        trades: Sequence[Trade],
        num_simulations: int = 1000,
        horizon_trades: Optional[int] = None,
        ruin_threshold_r: float = 10.0,
        target_r: float = 20.0,
        random_seed: Optional[int] = None
    ) -> MonteCarloResult:
        """
        Execute Monte Carlo trade sequence resampling simulations.

        Args:
            trades: List of trade objects.
            num_simulations: Number of resampled path iterations (default: 1000).
            horizon_trades: Length of simulated trade sequence (default: sample length).
            ruin_threshold_r: Max drawdown / loss threshold in R units to measure ruin probability.
            target_r: Target cumulative profit in R units to measure achievement probability.
            random_seed: Optional RNG seed for deterministic reproducibility in tests.

        Returns:
            MonteCarloResult with percentile paths, drawdown distribution, and probabilities.
        """
        r_list = self._extract_closed_r_multiples(trades)
        if not r_list:
            return MonteCarloResult(
                simulations_count=num_simulations,
                horizon_trades=horizon_trades or 0
            )

        rng = random.Random(random_seed)
        n_trades = len(r_list)
        horizon = horizon_trades if horizon_trades and horizon_trades > 0 else n_trades
        num_sims = max(10, num_simulations)

        # Store cumulative curves: paths[step][sim_idx]
        # Step 0 is starting point 0.0 R
        paths_by_step: List[List[float]] = [[0.0] * num_sims for _ in range(horizon + 1)]
        
        sim_final_rs: List[float] = []
        sim_max_dds: List[float] = []
        sim_worst_losing_streaks: List[int] = []
        ruin_hit_count = 0
        target_hit_count = 0

        for s in range(num_sims):
            cum_r = 0.0
            peak_r = 0.0
            max_dd = 0.0
            current_loss_streak = 0
            worst_loss_streak = 0
            hit_ruin = False
            hit_target = False

            # Draw the whole path's resampled R-values in one batched call.
            # random.choices() (uniform, with replacement) is dramatically faster than
            # calling random.choice() per step - the latter's rejection-sampling internals
            # dominated runtime on real accounts (15M+ calls, ~15-20s on a 5k-trade sync).
            path_r_values = rng.choices(r_list, k=horizon)

            for step in range(1, horizon + 1):
                trade_r = path_r_values[step - 1]
                cum_r += trade_r
                paths_by_step[step][s] = cum_r

                if cum_r > peak_r:
                    peak_r = cum_r
                dd = peak_r - cum_r
                if dd > max_dd:
                    max_dd = dd

                # Losing streak tracking
                if trade_r < 0:
                    current_loss_streak += 1
                    if current_loss_streak > worst_loss_streak:
                        worst_loss_streak = current_loss_streak
                else:
                    current_loss_streak = 0

                if dd >= ruin_threshold_r or cum_r <= -ruin_threshold_r:
                    hit_ruin = True
                if cum_r >= target_r:
                    hit_target = True

            sim_final_rs.append(cum_r)
            sim_max_dds.append(max_dd)
            sim_worst_losing_streaks.append(worst_loss_streak)
            if hit_ruin:
                ruin_hit_count += 1
            if hit_target:
                target_hit_count += 1

        # Calculate percentile curves at each step
        p5_curve: List[float] = []
        p25_curve: List[float] = []
        p50_curve: List[float] = []
        p75_curve: List[float] = []
        p95_curve: List[float] = []

        for step in range(horizon + 1):
            values = sorted(paths_by_step[step])
            p5_curve.append(self._percentile(values, 5))
            p25_curve.append(self._percentile(values, 25))
            p50_curve.append(self._percentile(values, 50))
            p75_curve.append(self._percentile(values, 75))
            p95_curve.append(self._percentile(values, 95))

        sorted_final_rs = sorted(sim_final_rs)
        sorted_max_dds = sorted(sim_max_dds)
        sorted_loss_streaks = sorted(sim_worst_losing_streaks)

        return MonteCarloResult(
            simulations_count=num_sims,
            horizon_trades=horizon,
            percentile_5th_r=p5_curve,
            percentile_25th_r=p25_curve,
            percentile_50th_r=p50_curve,
            percentile_75th_r=p75_curve,
            percentile_95th_r=p95_curve,
            final_r_median=round(self._percentile(sorted_final_rs, 50), 2),
            final_r_5th=round(self._percentile(sorted_final_rs, 5), 2),
            final_r_95th=round(self._percentile(sorted_final_rs, 95), 2),
            max_drawdown_median=round(self._percentile(sorted_max_dds, 50), 2),
            max_drawdown_95th=round(self._percentile(sorted_max_dds, 95), 2),
            max_drawdown_worst=round(max(sim_max_dds), 2),
            probability_of_ruin_threshold=round((ruin_hit_count / num_sims) * 100, 1),
            probability_of_target_r=round((target_hit_count / num_sims) * 100, 1),
            worst_consecutive_losses_95th=int(self._percentile(sorted_loss_streaks, 95))
        )

    def calculate_risk_of_ruin(
        self,
        trades: Sequence[Trade],
        max_drawdown_tolerance_r: float = 20.0,
        risk_per_trade_pct: float = 1.0,
        num_simulations: int = 2000,
        random_seed: Optional[int] = None
    ) -> RiskOfRuinAnalysis:
        """
        Compute formulaic and empirical Risk of Ruin.

        Uses Brownian drift-diffusion equation:
            P(Ruin) = exp( -2 * mu_R * U / sigma_R^2 )
        for positive expectancy, and 100% for non-positive expectancy.
        """
        r_list = self._extract_closed_r_multiples(trades)
        if len(r_list) < 5:
            return RiskOfRuinAnalysis(
                max_drawdown_tolerance_r=max_drawdown_tolerance_r,
                risk_per_trade_pct=risk_per_trade_pct,
                risk_level=RuinRiskLevel.INSUFFICIENT_DATA,
                summary_verdict="Insufficient trade sample for risk of ruin calculation (minimum 5 trades required).",
                recommendations=["Accumulate more trading data with recorded stop-losses to evaluate ruin risk."]
            )

        mean_r = statistics.mean(r_list)
        std_r = statistics.stdev(r_list) if len(r_list) > 1 else 0.0
        u_tolerance = max(1.0, max_drawdown_tolerance_r)

        # Empirical simulation
        mc = self.run_monte_carlo(
            trades=trades,
            num_simulations=num_simulations,
            horizon_trades=len(r_list) * 3,
            ruin_threshold_r=u_tolerance,
            random_seed=random_seed
        )
        empirical_prob = mc.probability_of_ruin_threshold / 100.0

        # Formulaic calculation
        if mean_r <= 0 or std_r <= 1e-6:
            formulaic_prob = 1.0
            risk_level = RuinRiskLevel.GUARANTEED_RUIN
            verdict = "Guaranteed Ruin: Negative or zero expectancy guarantees capital exhaustion over time."
            recommendations = [
                "Halt live trading and review strategy edge.",
                "Verify entry criteria and stop-loss placement rules.",
                "Eliminate unauthorized deviation trades."
            ]
        else:
            # Continuous diffusion ruin approximation
            exponent = -2.0 * mean_r * u_tolerance / (std_r ** 2)
            # Avoid overflow in math.exp
            if exponent > 0:
                formulaic_prob = 1.0
            else:
                formulaic_prob = math.exp(exponent)
            
            formulaic_prob = max(0.0, min(1.0, formulaic_prob))

            # Determine composite risk level based on conservative max of empirical and formulaic
            effective_prob = max(formulaic_prob, empirical_prob)
            if effective_prob < 0.01:
                risk_level = RuinRiskLevel.MINIMAL_RISK
                verdict = f"Minimal Risk of Ruin ({effective_prob*100:.1f}%): Edge is robust against {u_tolerance:.0f}R drawdown."
                recommendations = ["Maintain current risk discipline and consistent position sizing."]
            elif effective_prob < 0.05:
                risk_level = RuinRiskLevel.LOW_RISK
                verdict = f"Low Risk of Ruin ({effective_prob*100:.1f}%): Sustainable edge with healthy margin of safety."
                recommendations = ["Continue following strategy rules. Keep max risk per trade <= 1-2%."]
            elif effective_prob < 0.15:
                risk_level = RuinRiskLevel.MODERATE_RISK
                verdict = f"Moderate Risk of Ruin ({effective_prob*100:.1f}%): Elevated probability of hitting {u_tolerance:.0f}R drawdown."
                recommendations = [
                    "Consider reducing risk per trade by 25-50%.",
                    "Audit losing streaks to identify setup flaws."
                ]
            elif effective_prob < 0.35:
                risk_level = RuinRiskLevel.HIGH_RISK
                verdict = f"High Risk of Ruin ({effective_prob*100:.1f}%): Strategy variance poses significant capital risk."
                recommendations = [
                    "Reduce position size to lower volatility.",
                    "Review win rate vs risk-reward ratio."
                ]
            else:
                risk_level = RuinRiskLevel.CRITICAL_RISK
                verdict = f"Critical Risk of Ruin ({effective_prob*100:.1f}%): Strategy parameters create severe risk of drawdown."
                recommendations = [
                    "Strategy requires immediate optimization before scaling.",
                    "Enforce strict stop-losses on all setups."
                ]

        return RiskOfRuinAnalysis(
            empirical_ruin_probability=round(empirical_prob * 100, 1),
            formulaic_ruin_probability=round(formulaic_prob * 100, 1),
            max_drawdown_tolerance_r=u_tolerance,
            risk_per_trade_pct=risk_per_trade_pct,
            risk_level=risk_level,
            summary_verdict=verdict,
            recommendations=recommendations
        )

    def calculate_rolling_metrics(
        self,
        trades: Sequence[Trade],
        window_sizes: Sequence[int] = (20, 50, 100)
    ) -> Dict[int, RollingAnalyticsResult]:
        """
        Calculate rolling sliding window metrics across historical trade sequence.
        """
        closed_trades = [t for t in trades if t.status and t.status.upper() == "CLOSED" and t.realized_r is not None]
        results: Dict[int, RollingAnalyticsResult] = {}

        for w in window_sizes:
            if len(closed_trades) < w:
                results[w] = RollingAnalyticsResult(
                    window_size=w,
                    points=[],
                    edge_stability_verdict="INSUFFICIENT_DATA",
                    stability_score=0.0,
                    current_expectancy_trend="INSUFFICIENT_DATA"
                )
                continue

            points: List[RollingMetricPoint] = []
            expectancies: List[float] = []

            for i in range(w, len(closed_trades) + 1):
                window = closed_trades[i - w : i]
                current_trade = window[-1]

                r_vals = [float(t.realized_r) for t in window if t.realized_r is not None]
                profits = [float(t.profit) for t in window if t.profit is not None]

                win_count = sum(1 for r in r_vals if r > 0)
                loss_count = sum(1 for r in r_vals if r < 0)
                win_rate = (win_count / len(r_vals)) * 100 if r_vals else 0.0

                wins_r = [r for r in r_vals if r > 0]
                losses_r = [r for r in r_vals if r < 0]
                # sum()/len() instead of statistics.mean(): identical result, but mean()'s
                # exact-arithmetic internals made this the dominant cost of this loop
                # (called per-window across ~6.8k window positions - ~20s on a real account).
                avg_win_r = (sum(wins_r) / len(wins_r)) if wins_r else 0.0
                avg_loss_r = abs(sum(losses_r) / len(losses_r)) if losses_r else 0.0

                p_win = win_count / len(r_vals) if r_vals else 0.0
                p_loss = loss_count / len(r_vals) if r_vals else 0.0
                expectancy_r = (p_win * avg_win_r) - (p_loss * avg_loss_r)
                expectancies.append(expectancy_r)

                gross_profit = sum(p for p in profits if p > 0)
                gross_loss = abs(sum(p for p in profits if p < 0))
                profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.9 if gross_profit > 0 else 0.0)

                # Drawdown in window
                cum_r = 0.0
                peak = 0.0
                max_dd = 0.0
                for r in r_vals:
                    cum_r += r
                    if cum_r > peak:
                        peak = cum_r
                    dd = peak - cum_r
                    if dd > max_dd:
                        max_dd = dd

                ticket_id = getattr(current_trade, "position_id", 0) or getattr(current_trade, "id", 0) or 0
                points.append(RollingMetricPoint(
                    trade_index=i,
                    ticket=ticket_id,
                    win_rate=round(win_rate, 1),
                    expectancy_r=round(expectancy_r, 3),
                    profit_factor=round(profit_factor, 2) if profit_factor is not None else None,
                    avg_r=round(sum(r_vals) / len(r_vals), 3) if r_vals else 0.0,
                    max_drawdown_r=round(max_dd, 2)
                ))

            # Evaluate edge stability and trend
            positive_windows = sum(1 for exp in expectancies if exp > 0)
            prop_positive = positive_windows / len(expectancies) if expectancies else 0.0
            
            exp_std = statistics.stdev(expectancies) if len(expectancies) > 1 else 0.0
            exp_mean = statistics.mean(expectancies) if expectancies else 0.0

            # Stability score: reward high proportion of positive windows and low coefficient of variation
            cv = (exp_std / abs(exp_mean)) if abs(exp_mean) > 1e-4 else 2.0
            stability_score = max(0.0, min(1.0, prop_positive * (1.0 / (1.0 + 0.5 * cv))))

            # Trend direction: compare last 20% of windows with first 20%
            if len(expectancies) >= 5:
                k = max(2, len(expectancies) // 5)
                recent_avg = statistics.mean(expectancies[-k:])
                early_avg = statistics.mean(expectancies[:k])
                diff = recent_avg - early_avg
                if diff > 0.15:
                    trend = "IMPROVING"
                elif diff < -0.15:
                    trend = "DECAYING"
                else:
                    trend = "STABLE"
            else:
                trend = "STABLE"

            if prop_positive >= 0.85 and stability_score >= 0.7:
                verdict = "HIGHLY_STABLE_EDGE"
            elif prop_positive >= 0.65:
                verdict = "MODERATE_STABILITY_EDGE"
            elif prop_positive >= 0.40:
                verdict = "INCONSISTENT_VOLATILE_EDGE"
            else:
                verdict = "PERSISTENT_NEGATIVE_EDGE"

            results[w] = RollingAnalyticsResult(
                window_size=w,
                points=points,
                edge_stability_verdict=verdict,
                stability_score=round(stability_score, 2),
                current_expectancy_trend=trend
            )

        return results

    def calculate_bootstrap_confidence_intervals(
        self,
        trades: Sequence[Trade],
        num_resamples: int = 2000,
        confidence_level: float = 0.95,
        random_seed: Optional[int] = None
    ) -> BootstrapConfidenceIntervals:
        """
        Calculate bootstrap confidence intervals for key performance metrics.
        """
        closed_trades = [t for t in trades if t.status and t.status.upper() == "CLOSED" and t.realized_r is not None]
        n_samples = len(closed_trades)
        warnings: List[str] = []

        if n_samples < 5:
            return BootstrapConfidenceIntervals(
                sample_size=n_samples,
                confidence_level=confidence_level,
                is_statistically_significant=False,
                warnings=["Insufficient sample size for bootstrap inference (minimum 5 trades required)."]
            )

        if n_samples < 30:
            warnings.append(f"Small sample size ({n_samples} trades). Results have wide confidence intervals.")
        elif n_samples < 50:
            warnings.append(f"Moderate sample size ({n_samples} trades). 50+ trades recommended for high statistical power.")

        rng = random.Random(random_seed)
        alpha = (1.0 - confidence_level) / 2.0
        lower_p = alpha * 100
        upper_p = (1.0 - alpha) * 100

        resampled_win_rates: List[float] = []
        resampled_expectancies: List[float] = []
        resampled_profit_factors: List[float] = []
        resampled_avg_rs: List[float] = []

        for _ in range(num_resamples):
            resample = rng.choices(closed_trades, k=n_samples)
            r_vals = [float(t.realized_r) for t in resample if t.realized_r is not None]
            profits = [float(t.profit) for t in resample if t.profit is not None]

            # Win Rate
            win_count = sum(1 for r in r_vals if r > 0)
            loss_count = sum(1 for r in r_vals if r < 0)
            wr = (win_count / len(r_vals)) * 100 if r_vals else 0.0
            resampled_win_rates.append(wr)

            # Avg R (sum()/len() instead of statistics.mean(): same result, far less overhead
            # across num_resamples iterations each processing the full n_samples resample)
            avg_r = (sum(r_vals) / len(r_vals)) if r_vals else 0.0
            resampled_avg_rs.append(avg_r)

            # Expectancy
            wins_r = [r for r in r_vals if r > 0]
            losses_r = [r for r in r_vals if r < 0]
            avg_win_r = (sum(wins_r) / len(wins_r)) if wins_r else 0.0
            avg_loss_r = abs(sum(losses_r) / len(losses_r)) if losses_r else 0.0
            p_win = win_count / len(r_vals) if r_vals else 0.0
            p_loss = loss_count / len(r_vals) if r_vals else 0.0
            exp_r = (p_win * avg_win_r) - (p_loss * avg_loss_r)
            resampled_expectancies.append(exp_r)

            # Profit Factor
            gp = sum(p for p in profits if p > 0)
            gl = abs(sum(p for p in profits if p < 0))
            pf = (gp / gl) if gl > 0 else (99.9 if gp > 0 else 0.0)
            resampled_profit_factors.append(pf)

        resampled_win_rates.sort()
        resampled_expectancies.sort()
        resampled_profit_factors.sort()
        resampled_avg_rs.sort()

        win_rate_ci = (
            round(self._percentile(resampled_win_rates, lower_p), 1),
            round(self._percentile(resampled_win_rates, upper_p), 1)
        )
        expectancy_ci = (
            round(self._percentile(resampled_expectancies, lower_p), 3),
            round(self._percentile(resampled_expectancies, upper_p), 3)
        )
        pf_ci = (
            round(self._percentile(resampled_profit_factors, lower_p), 2),
            round(self._percentile(resampled_profit_factors, upper_p), 2)
        )
        avg_r_ci = (
            round(self._percentile(resampled_avg_rs, lower_p), 3),
            round(self._percentile(resampled_avg_rs, upper_p), 3)
        )

        # Statistical significance: 95% lower bound of Expectancy > 0 and sample size >= 20
        is_significant = (expectancy_ci[0] > 0.0) and (n_samples >= 20)
        if not is_significant and expectancy_ci[0] <= 0.0:
            warnings.append("Expectancy 95% CI includes zero or negative values: Trading edge is not yet statistically significant.")

        return BootstrapConfidenceIntervals(
            sample_size=n_samples,
            confidence_level=confidence_level,
            win_rate_ci=win_rate_ci,
            expectancy_ci=expectancy_ci,
            profit_factor_ci=pf_ci,
            avg_r_ci=avg_r_ci,
            is_statistically_significant=is_significant,
            warnings=warnings
        )

    def analyze_quant_research(
        self,
        trades: Sequence[Trade],
        num_simulations: int = 1000,
        horizon_trades: Optional[int] = None,
        ruin_threshold_r: float = 10.0,
        target_r: float = 20.0,
        max_drawdown_tolerance_r: float = 20.0,
        rolling_windows: Sequence[int] = (20, 50, 100),
        random_seed: Optional[int] = None
    ) -> QuantResearchResult:
        """
        Execute full comprehensive quantitative risk research analytics.
        """
        closed_with_r = [t for t in trades if t.status and t.status.upper() == "CLOSED" and t.realized_r is not None]

        mc = self.run_monte_carlo(
            trades=trades,
            num_simulations=num_simulations,
            horizon_trades=horizon_trades,
            ruin_threshold_r=ruin_threshold_r,
            target_r=target_r,
            random_seed=random_seed
        )

        ror = self.calculate_risk_of_ruin(
            trades=trades,
            max_drawdown_tolerance_r=max_drawdown_tolerance_r,
            num_simulations=num_simulations,
            random_seed=random_seed
        )

        rolling = self.calculate_rolling_metrics(
            trades=trades,
            window_sizes=rolling_windows
        )

        ci = self.calculate_bootstrap_confidence_intervals(
            trades=trades,
            num_resamples=num_simulations,
            random_seed=random_seed
        )

        return QuantResearchResult(
            monte_carlo=mc,
            risk_of_ruin=ror,
            rolling_analytics=rolling,
            confidence_intervals=ci,
            total_trades_analyzed=len(trades),
            trades_with_r_count=len(closed_with_r)
        )

    @staticmethod
    def _percentile(sorted_values: List[float], percentile: float) -> float:
        """Calculate percentile from a pre-sorted list of floats."""
        if not sorted_values:
            return 0.0
        if len(sorted_values) == 1:
            return sorted_values[0]
        p = max(0.0, min(100.0, percentile))
        idx = (p / 100.0) * (len(sorted_values) - 1)
        lower = int(math.floor(idx))
        upper = int(math.ceil(idx))
        if lower == upper:
            return sorted_values[lower]
        weight = idx - lower
        return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight
