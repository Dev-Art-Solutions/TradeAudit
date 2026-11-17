"""
Service for managing behavioral metadata, tag updates, and running automated behavior analysis.
"""

import logging
from typing import List, Optional, Dict, Sequence

from tradeaudit.infrastructure.repositories.trade_repository import TradeRepository
from tradeaudit.app.services.strategy_service import StrategyService
from tradeaudit.app.services.behavior_analyzer import BehaviorAnalyzer
from tradeaudit.domain.models import (
    Trade,
    BehaviorFlag,
    UserBehaviorAction,
    EmotionTag
)

logger = logging.getLogger("tradeaudit.app.services.behavior_service")


class BehaviorService:
    """Orchestrates behavioral analysis execution, tag updates, and flag reviews."""

    def __init__(
        self,
        trade_repository: TradeRepository,
        strategy_service: Optional[StrategyService] = None,
        behavior_analyzer: Optional[BehaviorAnalyzer] = None
    ):
        self.trade_repository = trade_repository
        self.strategy_service = strategy_service
        self.behavior_analyzer = behavior_analyzer or BehaviorAnalyzer()

    def update_emotion_tag(
        self,
        trade_id: int,
        emotion_tag: Optional[str],
        behavior_notes: Optional[str] = None
    ) -> bool:
        """
        Set or update emotional tag and notes for a given trade.

        :param trade_id: ID of trade.
        :param emotion_tag: EmotionTag enum value string (e.g., 'CALM', 'FOMO', etc.) or None.
        :param behavior_notes: Optional user commentary notes.
        :return: True if successfully updated.
        """
        if emotion_tag is not None:
            # Validate emotion tag against Enum
            try:
                emotion_tag = EmotionTag(emotion_tag).value
            except ValueError:
                logger.warning("Invalid emotion tag string provided: %s", emotion_tag)
                return False

        return self.trade_repository.update_trade_behavior(
            trade_id=trade_id,
            emotion_tag=emotion_tag,
            behavior_notes=behavior_notes
        )

    def bulk_update_emotion_tags(
        self,
        trade_ids: Sequence[int],
        emotion_tag: Optional[str],
        clear_emotion: bool = False
    ) -> int:
        """
        Set or clear emotional tags for multiple trades in a batch.

        :param trade_ids: List of trade IDs to update.
        :param emotion_tag: EmotionTag enum value string or None.
        :param clear_emotion: True to clear the emotional tag.
        :return: Count of updated trades.
        """
        if not trade_ids:
            return 0

        valid_tag = None
        if not clear_emotion and emotion_tag:
            try:
                valid_tag = EmotionTag(emotion_tag).value
            except ValueError:
                logger.warning("Invalid emotion tag string provided for bulk update: %s", emotion_tag)
                return 0

        return self.trade_repository.update_trades_behavior_bulk(
            trade_ids=trade_ids,
            emotion_tag=valid_tag,
            clear_emotion=clear_emotion or (valid_tag is None and emotion_tag == "")
        )

    def confirm_behavior_flag(self, trade_id: int, notes: Optional[str] = None) -> bool:
        """Mark automatically detected behavioral flags as CONFIRMED by the user."""
        return self.trade_repository.update_trade_behavior(
            trade_id=trade_id,
            user_behavior_action=UserBehaviorAction.CONFIRMED.value,
            behavior_notes=notes
        )

    def reject_behavior_flag(self, trade_id: int, notes: Optional[str] = None) -> bool:
        """Mark automatically detected behavioral flags as REJECTED by the user."""
        return self.trade_repository.update_trade_behavior(
            trade_id=trade_id,
            user_behavior_action=UserBehaviorAction.REJECTED.value,
            behavior_notes=notes
        )

    def run_behavior_analysis_for_account(self, account_id: int) -> Dict[int, List[BehaviorFlag]]:
        """
        Fetch all trades for account, run BehaviorAnalyzer heuristics, and persist updated flags.

        :param account_id: Account number.
        :return: Mapping of trade_id to list of detected BehaviorFlag objects.
        """
        trades = self.trade_repository.get_trades(account_id)
        if not trades:
            return {}

        # Fetch strategies if strategy service is available
        strategy_map = {}
        if self.strategy_service:
            strategies = self.strategy_service.get_all_strategies()
            strategy_map = {s.id: s for s in strategies if s.id is not None}

        # Analyze trades
        analysis_map = self.behavior_analyzer.analyze_all_trades(trades, strategy_map)

        # Save flags back to repository
        for trade_id, flags in analysis_map.items():
            self.trade_repository.update_trade_behavior(
                trade_id=trade_id,
                auto_behavior_flags=flags
            )

        logger.info("Completed behavioral analysis for account %s across %d trades.", account_id, len(trades))
        return analysis_map
