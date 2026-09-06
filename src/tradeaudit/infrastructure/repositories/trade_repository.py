import json
import logging
from typing import List, Optional
from datetime import datetime, timezone

from tradeaudit.infrastructure.database.connection import DatabaseManager
from tradeaudit.infrastructure.database.models import (
    AccountModel,
    TradeModel,
    TradeDealModel,
    SyncStateModel
)
from tradeaudit.domain.models import (
    TradeDeal,
    Trade,
    MT5AccountInfo,
    BehaviorFlag,
    BehaviorFlagType,
    ConfidenceLevel,
    UserBehaviorAction
)

logger = logging.getLogger("tradeaudit.infrastructure.repositories.trade_repository")


class TradeRepository:
    """Repository handling database operations for trades, deals, and sync states."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    @staticmethod
    def _ensure_account_stub(session, account_id: int) -> None:
        """
        Guarantee an accounts row exists before inserting anything that
        references it. save_account() (with full MT5AccountInfo) only runs
        when a live connection's account_info was actually fetched - with
        SQLite foreign_keys enforcement on, a sync where that fetch is
        skipped/fails would otherwise reject every trade/deal insert outright.
        A stub row here is later overwritten with real details by
        save_account() whenever account_info does become available.
        """
        exists = session.query(AccountModel.id).filter(AccountModel.id == account_id).first()
        if not exists:
            session.add(AccountModel(id=account_id))
            session.flush()

    def save_account(self, account_info: MT5AccountInfo) -> None:
        """Insert or update account record in database."""
        with self.db_manager.session_scope() as session:
            account = session.query(AccountModel).filter(AccountModel.id == account_info.login).first()
            if not account:
                account = AccountModel(id=account_info.login)
                session.add(account)

            account.name = account_info.name
            account.server = account_info.server
            account.company = account_info.company
            account.currency = account_info.currency
            account.leverage = account_info.leverage
            account.balance = account_info.balance
            account.equity = account_info.equity
            account.trade_mode = account_info.trade_mode
            logger.info("Saved/updated account info for login %s", account_info.login)

    def save_deals(self, deals: List[TradeDeal]) -> int:
        """
        Bulk save MT5 raw deals into trade_deals table. Skips already existing deal tickets.

        :param deals: List of TradeDeal domain models.
        :return: Count of newly inserted deals.
        """
        if not deals:
            return 0

        inserted_count = 0
        with self.db_manager.session_scope() as session:
            for account_id in {d.account_id for d in deals}:
                self._ensure_account_stub(session, account_id)

            existing_tickets = {
                row[0] for row in session.query(TradeDealModel.ticket).filter(
                    TradeDealModel.ticket.in_([d.ticket for d in deals])
                ).all()
            }

            for deal in deals:
                if deal.ticket in existing_tickets:
                    continue

                deal_model = TradeDealModel(
                    ticket=deal.ticket,
                    trade_id=None,
                    account_id=deal.account_id,
                    order_ticket=deal.order_ticket,
                    position_id=deal.position_id,
                    symbol=deal.symbol,
                    type=deal.type,
                    entry=deal.entry,
                    time=deal.time or datetime.now(timezone.utc),
                    volume=deal.volume,
                    price=deal.price,
                    profit=deal.profit,
                    swap=deal.swap,
                    commission=deal.commission,
                    fee=deal.fee,
                    sl=deal.sl,
                    tp=deal.tp,
                    comment=deal.comment,
                    magic=deal.magic
                )
                session.add(deal_model)
                inserted_count += 1

        logger.info("Saved %d new raw deals into database.", inserted_count)
        return inserted_count

    def save_trades(self, account_id: int, trades: List[Trade]) -> List[Trade]:
        """
        Save or update aggregated logical trades and link deals to trade IDs.

        :param account_id: MT5 account ID.
        :param trades: List of aggregated Trade domain models.
        :return: List of saved Trade domain models with assigned DB IDs.
        """
        if not trades:
            return []

        saved_trades: List[Trade] = []
        with self.db_manager.session_scope() as session:
            self._ensure_account_stub(session, account_id)

            for trade in trades:
                # Query existing trade by position_id and account_id
                trade_model = session.query(TradeModel).filter(
                    TradeModel.account_id == account_id,
                    TradeModel.position_id == trade.position_id
                ).first()

                if not trade_model:
                    trade_model = TradeModel(
                        account_id=account_id,
                        position_id=trade.position_id
                    )
                    session.add(trade_model)

                trade_model.symbol = trade.symbol
                trade_model.direction = trade.direction
                trade_model.volume = trade.volume
                trade_model.open_time = trade.open_time
                trade_model.close_time = trade.close_time
                trade_model.open_price = trade.open_price
                trade_model.close_price = trade.close_price
                trade_model.initial_sl = trade.initial_sl
                trade_model.initial_tp = trade.initial_tp
                trade_model.profit = trade.profit
                trade_model.swap = trade.swap
                trade_model.commission = trade.commission
                trade_model.fee = trade.fee
                trade_model.status = trade.status
                trade_model.price_risk = trade.price_risk
                trade_model.planned_reward = trade.planned_reward
                trade_model.planned_rr = trade.planned_rr
                trade_model.monetary_risk = trade.monetary_risk
                trade_model.realized_r = trade.realized_r
                trade_model.risk_percentage = trade.risk_percentage
                trade_model.is_valid_setup = trade.is_valid_setup
                trade_model.validation_error = trade.validation_error
                trade_model.strategy_id = trade.strategy_id
                trade_model.compliance_status = trade.compliance_status
                trade_model.compliance_details = trade.compliance_details
                trade_model.deviation_reason = trade.deviation_reason
                trade_model.emotion_tag = trade.emotion_tag
                trade_model.user_behavior_action = trade.user_behavior_action or UserBehaviorAction.UNREVIEWED.value
                trade_model.behavior_notes = trade.behavior_notes

                if trade.auto_behavior_flags:
                    flags_data = [
                        {
                            "flag_type": f.flag_type.value if hasattr(f.flag_type, "value") else str(f.flag_type),
                            "confidence": f.confidence.value if hasattr(f.confidence, "value") else str(f.confidence),
                            "reason": f.reason,
                            "metrics": f.metrics
                        }
                        for f in trade.auto_behavior_flags
                    ]
                    trade_model.auto_behavior_flags = json.dumps(flags_data)
                else:
                    trade_model.auto_behavior_flags = None

                session.flush()  # Ensures trade_model.id is populated

                # Link raw deals to trade_model.id
                session.query(TradeDealModel).filter(
                    TradeDealModel.account_id == account_id,
                    TradeDealModel.position_id == trade.position_id
                ).update({"trade_id": trade_model.id}, synchronize_session=False)

                trade.id = trade_model.id
                saved_trades.append(trade)

        logger.info("Successfully persisted/updated %d trades for account %s.", len(saved_trades), account_id)
        return saved_trades

    def get_trades(self, account_id: int) -> List[Trade]:
        """Fetch all stored trades for an account ordered by open_time descending."""
        result_trades: List[Trade] = []

        with self.db_manager.session_scope() as session:
            trade_models = session.query(TradeModel).filter(
                TradeModel.account_id == account_id
            ).order_by(TradeModel.open_time.desc()).all()

            # Fetch every deal for the account in one query and group by trade_id,
            # instead of issuing a separate query per trade (N+1 - was ~4s for 5k trades).
            all_deal_models = session.query(TradeDealModel).filter(
                TradeDealModel.account_id == account_id
            ).order_by(TradeDealModel.time.asc()).all()
            deals_by_trade_id: dict = {}
            for dm in all_deal_models:
                deals_by_trade_id.setdefault(dm.trade_id, []).append(dm)

            for tm in trade_models:
                deal_models = deals_by_trade_id.get(tm.id, [])

                deals = [
                    TradeDeal(
                        ticket=dm.ticket,
                        account_id=dm.account_id,
                        order_ticket=dm.order_ticket,
                        position_id=dm.position_id,
                        symbol=dm.symbol,
                        type=dm.type,
                        entry=dm.entry,
                        time=dm.time,
                        volume=dm.volume,
                        price=dm.price,
                        profit=dm.profit,
                        swap=dm.swap,
                        commission=dm.commission,
                        fee=dm.fee,
                        sl=dm.sl,
                        tp=dm.tp,
                        comment=dm.comment or "",
                        magic=dm.magic
                    )
                    for dm in deal_models
                ]

                parsed_flags: List[BehaviorFlag] = []
                if tm.auto_behavior_flags:
                    try:
                        raw_list = json.loads(tm.auto_behavior_flags)
                        for item in raw_list:
                            parsed_flags.append(BehaviorFlag(
                                flag_type=BehaviorFlagType(item["flag_type"]),
                                confidence=ConfidenceLevel(item["confidence"]),
                                reason=item.get("reason", ""),
                                metrics=item.get("metrics", {})
                            ))
                    except Exception as e:
                        logger.warning("Failed to parse auto_behavior_flags for trade %s: %s", tm.id, e)

                trade = Trade(
                    id=tm.id,
                    account_id=tm.account_id,
                    position_id=tm.position_id,
                    symbol=tm.symbol,
                    direction=tm.direction,
                    volume=tm.volume,
                    open_time=tm.open_time,
                    close_time=tm.close_time,
                    open_price=tm.open_price,
                    close_price=tm.close_price,
                    initial_sl=tm.initial_sl,
                    initial_tp=tm.initial_tp,
                    profit=tm.profit,
                    swap=tm.swap,
                    commission=tm.commission,
                    fee=tm.fee,
                    status=tm.status,
                    price_risk=tm.price_risk,
                    planned_reward=tm.planned_reward,
                    planned_rr=tm.planned_rr,
                    monetary_risk=tm.monetary_risk,
                    realized_r=tm.realized_r,
                    risk_percentage=tm.risk_percentage,
                    is_valid_setup=tm.is_valid_setup,
                    validation_error=tm.validation_error,
                    strategy_id=tm.strategy_id,
                    compliance_status=tm.compliance_status,
                    compliance_details=tm.compliance_details,
                    deviation_reason=tm.deviation_reason,
                    emotion_tag=tm.emotion_tag,
                    auto_behavior_flags=parsed_flags,
                    user_behavior_action=tm.user_behavior_action or UserBehaviorAction.UNREVIEWED.value,
                    behavior_notes=tm.behavior_notes,
                    deals=deals
                )
                result_trades.append(trade)

        return result_trades

    def update_trade_behavior(
        self,
        trade_id: int,
        emotion_tag: Optional[str] = None,
        auto_behavior_flags: Optional[List[BehaviorFlag]] = None,
        user_behavior_action: Optional[str] = None,
        behavior_notes: Optional[str] = None
    ) -> bool:
        """Update behavioral metadata for a specific trade."""
        with self.db_manager.session_scope() as session:
            trade_model = session.query(TradeModel).filter(TradeModel.id == trade_id).first()
            if not trade_model:
                logger.warning("Cannot update behavior for nonexistent trade ID %s", trade_id)
                return False

            if emotion_tag is not None:
                trade_model.emotion_tag = emotion_tag
            if user_behavior_action is not None:
                trade_model.user_behavior_action = user_behavior_action
            if behavior_notes is not None:
                trade_model.behavior_notes = behavior_notes

            if auto_behavior_flags is not None:
                flags_data = [
                    {
                        "flag_type": f.flag_type.value if hasattr(f.flag_type, "value") else str(f.flag_type),
                        "confidence": f.confidence.value if hasattr(f.confidence, "value") else str(f.confidence),
                        "reason": f.reason,
                        "metrics": f.metrics
                    }
                    for f in auto_behavior_flags
                ]
                trade_model.auto_behavior_flags = json.dumps(flags_data)

            logger.info("Updated behavioral metadata for trade ID %s", trade_id)
            return True

    def update_sync_state(self, account_id: int, sync_time: datetime, deals_count: int, trades_count: int) -> None:
        """Update synchronization metadata checkpoint."""
        with self.db_manager.session_scope() as session:
            sync_state = session.query(SyncStateModel).filter(SyncStateModel.account_id == account_id).first()
            if not sync_state:
                sync_state = SyncStateModel(account_id=account_id, last_sync_time=sync_time)
                session.add(sync_state)

            sync_state.last_sync_time = sync_time
            sync_state.deals_count = deals_count
            sync_state.trades_count = trades_count

            # Also update Account last_sync_at
            account = session.query(AccountModel).filter(AccountModel.id == account_id).first()
            if account:
                account.last_sync_at = sync_time

    def get_last_sync_time(self, account_id: int) -> Optional[datetime]:
        """Get the last synchronization timestamp for an account."""
        with self.db_manager.session_scope() as session:
            sync_state = session.query(SyncStateModel).filter(SyncStateModel.account_id == account_id).first()
            return sync_state.last_sync_time if sync_state else None
