"""
Advanced Breakdown Analytics service for TradeAudit.
Provides detailed performance breakdowns across multiple trade attributes:
- Symbol
- Direction (BUY / SELL)
- Trading Session (Asia, London, New York, Overlap, Off-hours)
- Weekday (Monday - Sunday)
- Hourly distribution (00:00 - 23:00)
- Contextual sequence (Post-Win, Post-Loss)
- Win/Loss Streak length
- Emotional Tags (CALM, FOMO, REVENGE, etc.)
"""

from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field

from tradeaudit.domain.models import Trade
from tradeaudit.domain.analytics import PerformanceMetrics
from tradeaudit.app.services.performance_analyzer import PerformanceAnalyzer


@dataclass
class AdvancedBreakdownResults:
    """Aggregated container holding all breakdown dimensions for a set of trades."""
    by_symbol: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    by_direction: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    by_session: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    by_weekday: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    by_hour: Dict[int, PerformanceMetrics] = field(default_factory=dict)
    by_context: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    by_streak: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    by_emotion: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    by_strategy: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    by_duration: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    by_compliance: Dict[str, PerformanceMetrics] = field(default_factory=dict)


class BreakdownAnalyzer:
    """Service for computing multi-dimensional breakdown performance analytics."""

    WEEKDAY_NAMES = [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ]

    SESSION_NAMES = ["ASIA", "LONDON", "NEW_YORK", "OVERLAP", "OFF_HOURS"]

    @classmethod
    def analyze_by_symbol(cls, trades: List[Trade]) -> Dict[str, PerformanceMetrics]:
        """Group trades by symbol and compute metrics for each symbol."""
        symbols_map: Dict[str, List[Trade]] = {}
        for t in trades:
            sym = t.symbol.upper() if t.symbol else "UNKNOWN"
            if sym not in symbols_map:
                symbols_map[sym] = []
            symbols_map[sym].append(t)

        return {sym: PerformanceAnalyzer.analyze(sym_trades) for sym, sym_trades in sorted(symbols_map.items())}

    @classmethod
    def analyze_by_direction(cls, trades: List[Trade]) -> Dict[str, PerformanceMetrics]:
        """Group trades by direction (BUY vs SELL) and compute metrics."""
        buy_trades = [t for t in trades if t.direction and t.direction.upper() == "BUY"]
        sell_trades = [t for t in trades if t.direction and t.direction.upper() == "SELL"]

        return {
            "BUY": PerformanceAnalyzer.analyze(buy_trades),
            "SELL": PerformanceAnalyzer.analyze(sell_trades)
        }

    @classmethod
    def get_trade_sessions(cls, trade: Trade) -> List[str]:
        """
        Determine which trading session(s) a trade belongs to based on open_time hour (UTC).
        - ASIA: 00:00 - 07:59
        - LONDON: 07:00 - 14:59
        - NEW_YORK: 13:00 - 20:59
        - OVERLAP: 13:00 - 14:59 (London & NY Overlap)
        """
        if not trade.open_time:
            return ["OFF_HOURS"]

        hour = trade.open_time.hour
        sessions = []

        if 0 <= hour < 8:
            sessions.append("ASIA")
        if 7 <= hour < 15:
            sessions.append("LONDON")
        if 13 <= hour < 21:
            sessions.append("NEW_YORK")
        if 13 <= hour < 15:
            sessions.append("OVERLAP")

        if not sessions:
            sessions.append("OFF_HOURS")

        return sessions

    @classmethod
    def analyze_by_session(cls, trades: List[Trade]) -> Dict[str, PerformanceMetrics]:
        """Group trades by trading session (ASIA, LONDON, NEW_YORK, OVERLAP, OFF_HOURS)."""
        session_map: Dict[str, List[Trade]] = {s: [] for s in cls.SESSION_NAMES}

        for t in trades:
            sessions = cls.get_trade_sessions(t)
            for s in sessions:
                session_map[s].append(t)

        return {s: PerformanceAnalyzer.analyze(session_map[s]) for s in cls.SESSION_NAMES}

    @classmethod
    def analyze_by_weekday(cls, trades: List[Trade]) -> Dict[str, PerformanceMetrics]:
        """Group trades by day of the week (Monday..Sunday)."""
        weekday_map: Dict[str, List[Trade]] = {day: [] for day in cls.WEEKDAY_NAMES}

        for t in trades:
            if t.open_time is not None:
                day_name = cls.WEEKDAY_NAMES[t.open_time.weekday()]
                weekday_map[day_name].append(t)
            else:
                weekday_map["Monday"].append(t)

        return {day: PerformanceAnalyzer.analyze(weekday_map[day]) for day in cls.WEEKDAY_NAMES}

    @classmethod
    def analyze_by_hour(cls, trades: List[Trade]) -> Dict[int, PerformanceMetrics]:
        """Group trades by entry hour (0..23)."""
        hour_map: Dict[int, List[Trade]] = {h: [] for h in range(24)}

        for t in trades:
            if t.open_time is not None:
                hour_map[t.open_time.hour].append(t)

        return {h: PerformanceAnalyzer.analyze(hour_map[h]) for h in range(24)}

    @classmethod
    def analyze_by_context(cls, trades: List[Trade]) -> Dict[str, PerformanceMetrics]:
        """
        Group trades by contextual sequence:
        - POST_WIN: Trade opened immediately following a winning trade.
        - POST_LOSS: Trade opened immediately following a losing trade.
        - INITIAL_OR_BE: First trade or trade following a breakeven outcome.
        """
        closed_trades = [t for t in trades if t.status and t.status.upper() == "CLOSED"]
        closed_trades.sort(key=lambda t: t.close_time or t.open_time or datetime.min)

        context_map: Dict[str, List[Trade]] = {
            "POST_WIN": [],
            "POST_LOSS": [],
            "INITIAL_OR_BE": []
        }

        prev_result: str = "INITIAL"

        for t in closed_trades:
            if prev_result == "WIN":
                context_map["POST_WIN"].append(t)
            elif prev_result == "LOSS":
                context_map["POST_LOSS"].append(t)
            else:
                context_map["INITIAL_OR_BE"].append(t)

            if t.net_profit > 0:
                prev_result = "WIN"
            elif t.net_profit < 0:
                prev_result = "LOSS"
            else:
                prev_result = "BE"

        return {ctx: PerformanceAnalyzer.analyze(context_map[ctx]) for ctx in ["POST_WIN", "POST_LOSS", "INITIAL_OR_BE"]}

    @classmethod
    def analyze_by_streak(cls, trades: List[Trade]) -> Dict[str, PerformanceMetrics]:
        """
        Group trades by preceding win/loss streak count before trade entry:
        - STREAK_0: Initial trade / no active streak
        - WIN_STREAK_1, WIN_STREAK_2, WIN_STREAK_3_PLUS
        - LOSS_STREAK_1, LOSS_STREAK_2, LOSS_STREAK_3_PLUS
        """
        closed_trades = [t for t in trades if t.status and t.status.upper() == "CLOSED"]
        closed_trades.sort(key=lambda t: t.close_time or t.open_time or datetime.min)

        streak_categories = [
            "STREAK_0",
            "WIN_STREAK_1",
            "WIN_STREAK_2",
            "WIN_STREAK_3_PLUS",
            "LOSS_STREAK_1",
            "LOSS_STREAK_2",
            "LOSS_STREAK_3_PLUS"
        ]

        streak_map: Dict[str, List[Trade]] = {cat: [] for cat in streak_categories}

        curr_win_streak = 0
        curr_loss_streak = 0

        for t in closed_trades:
            if curr_win_streak == 1:
                streak_map["WIN_STREAK_1"].append(t)
            elif curr_win_streak == 2:
                streak_map["WIN_STREAK_2"].append(t)
            elif curr_win_streak >= 3:
                streak_map["WIN_STREAK_3_PLUS"].append(t)
            elif curr_loss_streak == 1:
                streak_map["LOSS_STREAK_1"].append(t)
            elif curr_loss_streak == 2:
                streak_map["LOSS_STREAK_2"].append(t)
            elif curr_loss_streak >= 3:
                streak_map["LOSS_STREAK_3_PLUS"].append(t)
            else:
                streak_map["STREAK_0"].append(t)

            # Update streak state after current trade outcome
            if t.net_profit > 0:
                curr_win_streak += 1
                curr_loss_streak = 0
            elif t.net_profit < 0:
                curr_loss_streak += 1
                curr_win_streak = 0
            else:
                curr_win_streak = 0
                curr_loss_streak = 0

        return {cat: PerformanceAnalyzer.analyze(streak_map[cat]) for cat in streak_categories}

    @classmethod
    def analyze_by_emotion(cls, trades: List[Trade]) -> Dict[str, PerformanceMetrics]:
        """Group trades by emotional tag (CALM, FOMO, REVENGE, etc.)."""
        emotion_map: Dict[str, List[Trade]] = {}

        for t in trades:
            tag = t.emotion_tag.upper() if t.emotion_tag else "UNTAGGED"
            if tag not in emotion_map:
                emotion_map[tag] = []
            emotion_map[tag].append(t)

        return {tag: PerformanceAnalyzer.analyze(emotion_map[tag]) for tag in sorted(emotion_map.keys())}

    @classmethod
    def analyze_by_strategy(
        cls, trades: List[Trade], strategies: Optional[Dict[int, str]] = None
    ) -> Dict[str, PerformanceMetrics]:
        """Group trades by assigned strategy name."""
        strategy_names = strategies or {}
        strat_map: Dict[str, List[Trade]] = {}

        for t in trades:
            if t.strategy_id is not None:
                name = strategy_names.get(t.strategy_id, f"Strategy #{t.strategy_id}")
            else:
                name = "Unassigned"
            if name not in strat_map:
                strat_map[name] = []
            strat_map[name].append(t)

        return {k: PerformanceAnalyzer.analyze(v) for k, v in sorted(strat_map.items())}

    DURATION_BUCKETS = [
        "SCALP_UNDER_5M",      # < 5 minutes
        "INTRADAY_5M_TO_1H",    # 5m to 60m
        "INTRADAY_1H_TO_4H",    # 1h to 4h
        "SESSION_4H_TO_1D",     # 4h to 24h
        "SWING_OVER_1D"         # > 24h
    ]

    @classmethod
    def get_duration_bucket(cls, trade: Trade) -> Optional[str]:
        """Categorize a closed trade into holding duration brackets."""
        if not trade.open_time or not trade.close_time or trade.close_time < trade.open_time:
            return None
        mins = (trade.close_time - trade.open_time).total_seconds() / 60.0
        if mins < 5:
            return "SCALP_UNDER_5M"
        elif mins < 60:
            return "INTRADAY_5M_TO_1H"
        elif mins < 240:
            return "INTRADAY_1H_TO_4H"
        elif mins <= 1440:
            return "SESSION_4H_TO_1D"
        else:
            return "SWING_OVER_1D"

    @classmethod
    def analyze_by_duration(cls, trades: List[Trade]) -> Dict[str, PerformanceMetrics]:
        """Group closed trades by holding duration brackets and compute metrics."""
        duration_map: Dict[str, List[Trade]] = {bucket: [] for bucket in cls.DURATION_BUCKETS}
        closed_trades = [t for t in trades if t.status and t.status.upper() == "CLOSED"]

        for t in closed_trades:
            bucket = cls.get_duration_bucket(t)
            if bucket and bucket in duration_map:
                duration_map[bucket].append(t)

        return {bucket: PerformanceAnalyzer.analyze(duration_map[bucket]) for bucket in cls.DURATION_BUCKETS}

    COMPLIANCE_STATUSES = ["COMPLIANT", "DEVIATION", "PARTIAL", "UNCHECKED"]

    @classmethod
    def analyze_by_compliance(cls, trades: List[Trade]) -> Dict[str, PerformanceMetrics]:
        """Group closed trades by strategy compliance status and compute performance metrics."""
        compliance_map: Dict[str, List[Trade]] = {cat: [] for cat in cls.COMPLIANCE_STATUSES}
        closed_trades = [t for t in trades if t.status and t.status.upper() == "CLOSED"]

        for t in closed_trades:
            status = (t.compliance_status or "UNCHECKED").upper().strip()
            if status not in compliance_map:
                compliance_map[status] = []
            compliance_map[status].append(t)

        return {
            k: PerformanceAnalyzer.analyze(compliance_map[k])
            for k in cls.COMPLIANCE_STATUSES
            if len(compliance_map[k]) > 0 or k in ("COMPLIANT", "DEVIATION")
        }

    @classmethod
    def analyze_all(
        cls, trades: List[Trade], strategies: Optional[Dict[int, str]] = None
    ) -> AdvancedBreakdownResults:
        """Run all breakdown analytics on a given list of trades."""
        return AdvancedBreakdownResults(
            by_symbol=cls.analyze_by_symbol(trades),
            by_direction=cls.analyze_by_direction(trades),
            by_session=cls.analyze_by_session(trades),
            by_weekday=cls.analyze_by_weekday(trades),
            by_hour=cls.analyze_by_hour(trades),
            by_context=cls.analyze_by_context(trades),
            by_streak=cls.analyze_by_streak(trades),
            by_emotion=cls.analyze_by_emotion(trades),
            by_strategy=cls.analyze_by_strategy(trades, strategies=strategies),
            by_duration=cls.analyze_by_duration(trades),
            by_compliance=cls.analyze_by_compliance(trades)
        )
