"""
Core Performance Analytics service for TradeAudit.
Calculates statistical performance metrics, win/loss rates, R-multiples, expectancy, drawdowns, and streaks.
"""

from typing import List, Optional
import statistics
from datetime import datetime

from tradeaudit.domain.models import Trade
from tradeaudit.domain.analytics import PerformanceMetrics, ProfitabilityVerdict


class PerformanceAnalyzer:
    """Service for computing trading statistics, performance analytics, and profitability edge verdicts."""

    @staticmethod
    def analyze(trades: List[Trade], min_sample_size: int = 30) -> PerformanceMetrics:
        """
        Analyze a list of trades and compute complete performance metrics.

        Args:
            trades: List of Trade entities (open or closed).
            min_sample_size: Minimum closed trade sample size required for valid statistical verdicts.

        Returns:
            PerformanceMetrics dataclass populated with computed statistics.
        """
        # Filter and sort closed trades chronologically
        closed_trades = [t for t in trades if t.status and t.status.upper() == "CLOSED"]
        closed_trades.sort(
            key=lambda t: t.close_time or t.open_time or datetime.min
        )

        total_trades = len(closed_trades)
        is_sample_sufficient = total_trades >= min_sample_size

        if total_trades == 0:
            return PerformanceMetrics(
                total_trades=0,
                min_sample_size=min_sample_size,
                is_sample_sufficient=False,
                verdict=ProfitabilityVerdict.INSUFFICIENT_DATA
            )

        winning_trades = [t for t in closed_trades if t.net_profit > 0]
        losing_trades = [t for t in closed_trades if t.net_profit < 0]
        breakeven_trades = [t for t in closed_trades if t.net_profit == 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        be_count = len(breakeven_trades)

        win_rate = round(win_count / total_trades, 4)
        loss_rate = round(loss_count / total_trades, 4)

        net_profit = round(sum(t.net_profit for t in closed_trades), 2)
        gross_profit = round(sum(t.net_profit for t in winning_trades), 2)
        gross_loss = round(sum(abs(t.net_profit) for t in losing_trades), 2)

        profit_factor: Optional[float] = None
        if gross_loss > 0:
            profit_factor = round(gross_profit / gross_loss, 4)

        avg_win_monetary = round(gross_profit / win_count, 2) if win_count > 0 else 0.0
        avg_loss_monetary = round(gross_loss / loss_count, 2) if loss_count > 0 else 0.0
        expectancy_monetary = round(net_profit / total_trades, 2)

        durations = [
            (t.close_time - t.open_time).total_seconds() / 60.0
            for t in closed_trades
            if t.open_time is not None and t.close_time is not None and t.close_time >= t.open_time
        ]

        # R-Multiple metrics
        trades_with_r_list = [t for t in closed_trades if t.realized_r is not None]
        trades_with_r = len(trades_with_r_list)
        net_r = round(sum(t.realized_r for t in trades_with_r_list), 4)

        winning_r_list = [t.realized_r for t in trades_with_r_list if t.realized_r is not None and t.realized_r > 0]
        losing_r_list = [abs(t.realized_r) for t in trades_with_r_list if t.realized_r is not None and t.realized_r < 0]

        avg_win_r = round(sum(winning_r_list) / len(winning_r_list), 4) if winning_r_list else 0.0
        avg_loss_r = round(sum(losing_r_list) / len(losing_r_list), 4) if losing_r_list else 0.0

        if trades_with_r > 0:
            expectancy_r = round(net_r / trades_with_r, 4)
        else:
            expectancy_r = 0.0

        # Cumulative and Drawdown series
        cumulative_monetary_series: List[float] = []
        cumulative_r_series: List[float] = []
        drawdown_r_series: List[float] = []

        curr_monetary = 0.0
        curr_r = 0.0

        peak_monetary = 0.0
        max_drawdown_monetary = 0.0

        peak_r = 0.0
        max_drawdown_r = 0.0

        for t in closed_trades:
            curr_monetary += t.net_profit
            cum_mon_rounded = round(curr_monetary, 2)
            cumulative_monetary_series.append(cum_mon_rounded)

            if cum_mon_rounded > peak_monetary:
                peak_monetary = cum_mon_rounded
            dd_mon = peak_monetary - cum_mon_rounded
            if dd_mon > max_drawdown_monetary:
                max_drawdown_monetary = dd_mon

            if t.realized_r is not None:
                curr_r += t.realized_r
            cum_r_rounded = round(curr_r, 4)
            cumulative_r_series.append(cum_r_rounded)

            if cum_r_rounded > peak_r:
                peak_r = cum_r_rounded
            dd_r = round(peak_r - cum_r_rounded, 4)
            drawdown_r_series.append(dd_r)
            if dd_r > max_drawdown_r:
                max_drawdown_r = dd_r

        # Consecutive Win / Loss Streaks
        max_consecutive_wins = 0
        curr_consecutive_wins = 0

        max_consecutive_losses = 0
        curr_consecutive_losses = 0

        for t in closed_trades:
            if t.net_profit > 0:
                curr_consecutive_wins += 1
                if curr_consecutive_wins > max_consecutive_wins:
                    max_consecutive_wins = curr_consecutive_wins
                curr_consecutive_losses = 0
            elif t.net_profit < 0:
                curr_consecutive_losses += 1
                if curr_consecutive_losses > max_consecutive_losses:
                    max_consecutive_losses = curr_consecutive_losses
                curr_consecutive_wins = 0
            else:
                curr_consecutive_wins = 0
                curr_consecutive_losses = 0

        avg_r = round(net_r / trades_with_r, 4) if trades_with_r > 0 else 0.0

        # Risk Percentage
        trades_with_risk = [t for t in closed_trades if t.risk_percentage is not None]
        avg_risk_percentage = (
            round(sum(t.risk_percentage for t in trades_with_risk) / len(trades_with_risk), 2)
            if trades_with_risk else 0.0
        )

        # Verdict calculation
        if not is_sample_sufficient:
            verdict = ProfitabilityVerdict.INSUFFICIENT_DATA
        else:
            eval_val = expectancy_r if trades_with_r > 0 else expectancy_monetary
            threshold_high = 0.05 if trades_with_r > 0 else 0.01
            threshold_low = -0.05 if trades_with_r > 0 else -0.01

            if eval_val > threshold_high:
                verdict = ProfitabilityVerdict.POSITIVE_EXPECTANCY
            elif eval_val < threshold_low:
                verdict = ProfitabilityVerdict.NEGATIVE_EXPECTANCY
            else:
                verdict = ProfitabilityVerdict.BREAK_EVEN

        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            breakeven_trades=be_count,
            win_rate=win_rate,
            loss_rate=loss_rate,
            net_profit=net_profit,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=profit_factor,
            net_r=net_r,
            trades_with_r=trades_with_r,
            avg_win_monetary=avg_win_monetary,
            avg_loss_monetary=avg_loss_monetary,
            avg_win_r=avg_win_r,
            avg_loss_r=avg_loss_r,
            avg_r=avg_r,
            avg_risk_percentage=avg_risk_percentage,
            expectancy_r=expectancy_r,
            expectancy_monetary=expectancy_monetary,
            max_drawdown_r=round(max_drawdown_r, 4),
            max_drawdown_monetary=round(max_drawdown_monetary, 2),
            recovery_factor=(
                round(net_profit / max_drawdown_monetary, 4)
                if max_drawdown_monetary > 0 else None
            ),
            avg_duration_minutes=(round(sum(durations) / len(durations), 2) if durations else None),
            median_duration_minutes=(round(statistics.median(durations), 2) if durations else None),
            trades_with_duration=len(durations),
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            verdict=verdict,
            min_sample_size=min_sample_size,
            is_sample_sufficient=is_sample_sufficient,
            cumulative_r_series=cumulative_r_series,
            drawdown_r_series=drawdown_r_series,
            cumulative_monetary_series=cumulative_monetary_series,
        )

    @classmethod
    def analyze_by_symbol(cls, trades: List[Trade]) -> dict:
        """Group trades by symbol and compute metrics for each symbol."""
        symbols_map = {}
        for t in trades:
            sym = t.symbol.upper() if t.symbol else "UNKNOWN"
            if sym not in symbols_map:
                symbols_map[sym] = []
            symbols_map[sym].append(t)

        result = {}
        for sym, sym_trades in symbols_map.items():
            result[sym] = cls.analyze(sym_trades)
        return result

    @classmethod
    def analyze_by_direction(cls, trades: List[Trade]) -> dict:
        """Group trades by direction (BUY vs SELL) and compute metrics."""
        buy_trades = [t for t in trades if t.direction and t.direction.upper() == "BUY"]
        sell_trades = [t for t in trades if t.direction and t.direction.upper() == "SELL"]

        return {
            "BUY": cls.analyze(buy_trades),
            "SELL": cls.analyze(sell_trades)
        }

