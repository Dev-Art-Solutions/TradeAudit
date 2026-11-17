"""
Service for managing strategies and running compliance evaluation over trades.
"""

import json
import logging
from typing import List, Optional, Sequence

from tradeaudit.domain.models import Strategy, Trade, ComplianceStatus, ComplianceResult
from tradeaudit.infrastructure.repositories.strategy_repository import StrategyRepository
from tradeaudit.infrastructure.repositories.trade_repository import TradeRepository
from tradeaudit.app.services.strategy_compliance_engine import StrategyComplianceEngine

logger = logging.getLogger("tradeaudit.app.services.strategy_service")


class StrategyService:
    """Application service for strategy CRUD operations and trade compliance processing."""

    def __init__(
        self,
        strategy_repo: StrategyRepository,
        trade_repo: TradeRepository,
        compliance_engine: Optional[StrategyComplianceEngine] = None
    ):
        self.strategy_repo = strategy_repo
        self.trade_repo = trade_repo
        self.compliance_engine = compliance_engine or StrategyComplianceEngine()

    def create_strategy(self, strategy: Strategy) -> Strategy:
        """Create a new strategy."""
        return self.strategy_repo.save_strategy(strategy)

    def update_strategy(self, strategy: Strategy) -> Strategy:
        """Update an existing strategy."""
        if not strategy.id:
            raise ValueError("Strategy ID required for update.")
        return self.strategy_repo.save_strategy(strategy)

    def delete_strategy(self, strategy_id: int) -> bool:
        """Delete a strategy by ID."""
        return self.strategy_repo.delete_strategy(strategy_id)

    def get_strategy(self, strategy_id: int) -> Optional[Strategy]:
        """Fetch a single strategy by ID."""
        return self.strategy_repo.get_strategy(strategy_id)

    def get_all_strategies(self, only_active: bool = False) -> List[Strategy]:
        """Fetch all stored strategies."""
        return self.strategy_repo.get_all_strategies(only_active=only_active)

    def assign_strategy_to_trade(
        self,
        account_id: int,
        trade_id: int,
        strategy_id: Optional[int],
        deviation_reason: Optional[str] = None
    ) -> Optional[Trade]:
        """
        Assign a strategy to a trade and run compliance evaluation.

        :param account_id: Account ID owning the trade.
        :param trade_id: Trade ID.
        :param strategy_id: Strategy ID to assign (or None to unassign).
        :param deviation_reason: Optional manual note/reason for deviation.
        :return: Updated Trade object or None if trade not found.
        """
        all_trades = self.trade_repo.get_trades(account_id)
        target_trade = next((t for t in all_trades if t.id == trade_id), None)
        if not target_trade:
            logger.warning("Trade ID %s not found for account %s", trade_id, account_id)
            return None

        target_trade.strategy_id = strategy_id
        if deviation_reason is not None:
            target_trade.deviation_reason = deviation_reason

        if strategy_id is not None:
            strategy = self.strategy_repo.get_strategy(strategy_id)
            if strategy:
                comp_result = self.compliance_engine.evaluate(target_trade, strategy, all_trades)
                target_trade.compliance_status = comp_result.status.value
                details_dict = {
                    "passed": comp_result.passed_rules,
                    "violations": [
                        {"rule": v.rule_name, "message": v.message, "expected": v.expected, "actual": v.actual}
                        for v in comp_result.violations
                    ]
                }
                target_trade.compliance_details = json.dumps(details_dict)
            else:
                target_trade.compliance_status = ComplianceStatus.UNCHECKED.value
                target_trade.compliance_details = None
        else:
            target_trade.compliance_status = ComplianceStatus.UNCHECKED.value
            target_trade.compliance_details = None

        self.trade_repo.save_trades(account_id, [target_trade])
        logger.info("Assigned strategy ID %s to trade ID %s (Compliance: %s)", strategy_id, trade_id, target_trade.compliance_status)
        return target_trade

    def bulk_assign_strategy_to_trades(
        self,
        account_id: int,
        trade_ids: Sequence[int],
        strategy_id: Optional[int]
    ) -> List[Trade]:
        """
        Assign or unassign a strategy to multiple trades and evaluate compliance in a single batch.

        :param account_id: Account ID owning the trades.
        :param trade_ids: Collection of trade IDs to update.
        :param strategy_id: Strategy ID to assign (or None to unassign).
        :return: List of updated Trade objects.
        """
        if not trade_ids:
            return []

        trade_ids_set = set(trade_ids)
        all_trades = self.trade_repo.get_trades(account_id)
        target_trades = [t for t in all_trades if t.id in trade_ids_set]
        if not target_trades:
            return []

        strategy = self.strategy_repo.get_strategy(strategy_id) if strategy_id is not None else None

        for trade in target_trades:
            trade.strategy_id = strategy_id
            if strategy:
                comp_result = self.compliance_engine.evaluate(trade, strategy, all_trades)
                trade.compliance_status = comp_result.status.value
                details_dict = {
                    "passed": comp_result.passed_rules,
                    "violations": [
                        {"rule": v.rule_name, "message": v.message, "expected": v.expected, "actual": v.actual}
                        for v in comp_result.violations
                    ]
                }
                trade.compliance_details = json.dumps(details_dict)
            else:
                trade.compliance_status = ComplianceStatus.UNCHECKED.value
                trade.compliance_details = None

        self.trade_repo.save_trades(account_id, target_trades)
        logger.info("Bulk assigned strategy ID %s to %d trades on account %s", strategy_id, len(target_trades), account_id)
        return target_trades

    def reevaluate_account_compliance(self, account_id: int) -> int:
        """
        Re-evaluate compliance for all trades of an account that have assigned strategies.

        :param account_id: Account ID.
        :return: Count of trades evaluated.
        """
        all_trades = self.trade_repo.get_trades(account_id)
        strategies = {s.id: s for s in self.strategy_repo.get_all_strategies() if s.id is not None}

        evaluated_count = 0
        for trade in all_trades:
            if trade.strategy_id and trade.strategy_id in strategies:
                strategy = strategies[trade.strategy_id]
                comp_result = self.compliance_engine.evaluate(trade, strategy, all_trades)
                trade.compliance_status = comp_result.status.value
                details_dict = {
                    "passed": comp_result.passed_rules,
                    "violations": [
                        {"rule": v.rule_name, "message": v.message, "expected": v.expected, "actual": v.actual}
                        for v in comp_result.violations
                    ]
                }
                trade.compliance_details = json.dumps(details_dict)
                evaluated_count += 1

        if all_trades:
            self.trade_repo.save_trades(account_id, all_trades)

        logger.info("Re-evaluated compliance for %d trades on account %s", evaluated_count, account_id)
        return evaluated_count
