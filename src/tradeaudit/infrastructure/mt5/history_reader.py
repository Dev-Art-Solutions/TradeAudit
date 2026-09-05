"""
MetaTrader 5 history reader for fetching raw deal execution records.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    mt5 = None
    HAS_MT5 = False

from tradeaudit.domain.models import TradeDeal
from tradeaudit.app.exceptions import MT5Error, MT5ConnectionError

logger = logging.getLogger("tradeaudit.infrastructure.mt5.history_reader")


class MT5HistoryReader:
    """Service to query historical deals and orders directly from MetaTrader 5 terminal."""

    # MT5 Deal Types Mapping
    DEAL_TYPE_MAP = {
        0: "BUY",
        1: "SELL",
        2: "BALANCE",
        3: "CREDIT",
        4: "CHARGE",
        5: "CORRECTION",
        6: "BONUS",
        7: "COMMISSION",
        8: "COMMISSION_DAILY",
        9: "COMMISSION_MONTHLY",
        10: "COMMISSION_AGENT_DAILY",
        11: "COMMISSION_AGENT_MONTHLY",
        12: "INTEREST",
        13: "BUY_CANCELED",
        14: "SELL_CANCELED",
        15: "DIVIDEND",
        16: "DIVIDEND_FRANKED",
        17: "TAX"
    }

    # MT5 Deal Entry Mapping
    DEAL_ENTRY_MAP = {
        0: "IN",
        1: "OUT",
        2: "INOUT",
        3: "OUT_BY"
    }

    def fetch_deals(
        self,
        account_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[TradeDeal]:
        """
        Fetch raw deals from MT5 history within the specified date range.

        :param account_id: MT5 login account number.
        :param from_date: Start datetime (inclusive). Defaults to unix epoch if None.
        :param to_date: End datetime (inclusive). Defaults to current time if None.
        :return: List of normalized TradeDeal domain objects.
        """
        if not HAS_MT5 or mt5 is None:
            logger.warning("MetaTrader5 python package not available.")
            raise MT5ConnectionError("MetaTrader5 package is not available.")

        # Default date range handling
        if from_date is None:
            from_date = datetime(1970, 1, 1, tzinfo=timezone.utc)
        if to_date is None:
            to_date = datetime.now(timezone.utc)

        logger.info("Fetching MT5 deals for account %s from %s to %s", account_id, from_date, to_date)

        try:
            raw_deals = mt5.history_deals_get(from_date, to_date)
        except Exception as e:
            logger.error("Exception occurred while calling mt5.history_deals_get: %s", e)
            raise MT5Error(f"Failed to fetch MT5 history deals: {e}") from e

        if raw_deals is None:
            error_code, error_msg = mt5.last_error()
            logger.error("mt5.history_deals_get returned None (code %s): %s", error_code, error_msg)
            raise MT5Error(f"MT5 history_deals_get failed (code {error_code}): {error_msg}")

        # MT5 deals never carry SL/TP - only the order that generated the deal does.
        # Bulk-fetch orders for the same window and join on order ticket so initial_sl
        # can be resolved for the aggregator; entry deals with no matching order
        # (e.g. deposits/balance ops, or an opening order outside this window on an
        # incremental sync) fall back to a per-ticket lookup, then to 0.0/unknown.
        order_sltp_map = {}
        try:
            raw_orders = mt5.history_orders_get(from_date, to_date)
        except Exception as e:
            logger.warning("Failed to fetch MT5 history orders for SL/TP join: %s", e)
            raw_orders = None
        if raw_orders:
            for o in raw_orders:
                o_dict = o._asdict() if hasattr(o, "_asdict") else {}
                o_ticket = int(o_dict.get("ticket", getattr(o, "ticket", 0)))
                order_sltp_map[o_ticket] = (
                    float(o_dict.get("sl", getattr(o, "sl", 0.0))),
                    float(o_dict.get("tp", getattr(o, "tp", 0.0))),
                )

        trade_deals: List[TradeDeal] = []
        for d in raw_deals:
            deal_dict = d._asdict() if hasattr(d, "_asdict") else {}
            
            ticket = int(deal_dict.get("ticket", getattr(d, "ticket", 0)))
            order_ticket = int(deal_dict.get("order", getattr(d, "order", 0)))
            position_id = int(deal_dict.get("position_id", getattr(d, "position_id", 0)))
            symbol = str(deal_dict.get("symbol", getattr(d, "symbol", "")))
            
            raw_type = int(deal_dict.get("type", getattr(d, "type", 0)))
            type_str = self.DEAL_TYPE_MAP.get(raw_type, str(raw_type))
            
            raw_entry = int(deal_dict.get("entry", getattr(d, "entry", 0)))
            entry_str = self.DEAL_ENTRY_MAP.get(raw_entry, str(raw_entry))

            timestamp = int(deal_dict.get("time", getattr(d, "time", 0)))
            deal_time = datetime.fromtimestamp(timestamp, tz=timezone.utc) if timestamp > 0 else datetime.now(timezone.utc)

            volume = float(deal_dict.get("volume", getattr(d, "volume", 0.0)))
            price = float(deal_dict.get("price", getattr(d, "price", 0.0)))
            profit = float(deal_dict.get("profit", getattr(d, "profit", 0.0)))
            swap = float(deal_dict.get("swap", getattr(d, "swap", 0.0)))
            commission = float(deal_dict.get("commission", getattr(d, "commission", 0.0)))
            fee = float(deal_dict.get("fee", getattr(d, "fee", 0.0)))

            sl, tp = order_sltp_map.get(order_ticket, (0.0, 0.0))
            if order_ticket and order_ticket not in order_sltp_map:
                try:
                    single_order = mt5.history_orders_get(ticket=order_ticket)
                except Exception:
                    single_order = None
                if single_order:
                    od = single_order[0]._asdict() if hasattr(single_order[0], "_asdict") else {}
                    sl = float(od.get("sl", getattr(single_order[0], "sl", 0.0)))
                    tp = float(od.get("tp", getattr(single_order[0], "tp", 0.0)))

            comment = str(deal_dict.get("comment", getattr(d, "comment", "")))
            magic = int(deal_dict.get("magic", getattr(d, "magic", 0)))

            deal = TradeDeal(
                ticket=ticket,
                account_id=account_id,
                order_ticket=order_ticket,
                position_id=position_id,
                symbol=symbol,
                type=type_str,
                entry=entry_str,
                time=deal_time,
                volume=volume,
                price=price,
                profit=profit,
                swap=swap,
                commission=commission,
                fee=fee,
                sl=sl,
                tp=tp,
                comment=comment,
                magic=magic
            )
            trade_deals.append(deal)

        logger.info("Successfully fetched %d deals from MT5 for account %s.", len(trade_deals), account_id)
        return trade_deals
