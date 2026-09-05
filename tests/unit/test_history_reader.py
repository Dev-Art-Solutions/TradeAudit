"""
Unit tests for MT5HistoryReader infrastructure service.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from tradeaudit.infrastructure.mt5.history_reader import MT5HistoryReader


def test_fetch_deals_joins_sl_tp_from_originating_order():
    """
    Real MT5 deal records (mt5.history_deals_get) do not carry sl/tp fields -
    only the order that generated the deal does (mt5.history_orders_get).
    fetch_deals must join on order ticket to resolve initial SL/TP, otherwise
    every trade's initial_sl silently comes back as 0.0/unknown.
    """
    reader = MT5HistoryReader()

    mock_deal = MagicMock()
    mock_deal._asdict.return_value = {
        "ticket": 5001,
        "order": 9001,
        "position_id": 9001,
        "symbol": "EURUSD",
        "type": 0,  # BUY
        "entry": 0,  # IN
        "time": 1700000000,
        "volume": 0.1,
        "price": 1.0850,
        "profit": 0.0,
        "swap": 0.0,
        "commission": -1.0,
        "fee": 0.0,
        "comment": "",
        "magic": 0,
        # no "sl" / "tp" keys - matches the real MT5 TradeDeal structure
    }

    mock_order = MagicMock()
    mock_order._asdict.return_value = {
        "ticket": 9001,
        "sl": 1.0800,
        "tp": 1.0950,
    }

    with patch("tradeaudit.infrastructure.mt5.history_reader.mt5") as mock_mt5, \
         patch("tradeaudit.infrastructure.mt5.history_reader.HAS_MT5", True):
        mock_mt5.history_deals_get.return_value = (mock_deal,)
        mock_mt5.history_orders_get.return_value = (mock_order,)

        deals = reader.fetch_deals(
            account_id=123456,
            from_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            to_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        )

        assert len(deals) == 1
        assert deals[0].sl == 1.0800
        assert deals[0].tp == 1.0950


def test_fetch_deals_falls_back_to_per_ticket_order_lookup():
    """
    On an incremental sync, the opening order can fall outside the requested
    deal window. fetch_deals should still resolve sl/tp via a direct
    history_orders_get(ticket=...) lookup rather than defaulting to 0.0.
    """
    reader = MT5HistoryReader()

    mock_deal = MagicMock()
    mock_deal._asdict.return_value = {
        "ticket": 5002,
        "order": 9002,
        "position_id": 9002,
        "symbol": "GBPUSD",
        "type": 1,  # SELL
        "entry": 1,  # OUT
        "time": 1700000500,
        "volume": 0.1,
        "price": 1.2650,
        "profit": 12.5,
        "swap": 0.0,
        "commission": -1.0,
        "fee": 0.0,
        "comment": "",
        "magic": 0,
    }

    mock_order = MagicMock()
    mock_order._asdict.return_value = {
        "ticket": 9002,
        "sl": 1.2700,
        "tp": 1.2550,
    }

    def history_orders_get_side_effect(*args, **kwargs):
        if kwargs.get("ticket") == 9002:
            return (mock_order,)
        return ()  # bulk window fetch misses this order

    with patch("tradeaudit.infrastructure.mt5.history_reader.mt5") as mock_mt5, \
         patch("tradeaudit.infrastructure.mt5.history_reader.HAS_MT5", True):
        mock_mt5.history_deals_get.return_value = (mock_deal,)
        mock_mt5.history_orders_get.side_effect = history_orders_get_side_effect

        deals = reader.fetch_deals(
            account_id=123456,
            from_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            to_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        )

        assert len(deals) == 1
        assert deals[0].sl == 1.2700
        assert deals[0].tp == 1.2550


def test_fetch_deals_deposit_without_order_defaults_to_zero():
    """Balance/deposit deals have no originating order (order ticket 0) - should not error."""
    reader = MT5HistoryReader()

    mock_deal = MagicMock()
    mock_deal._asdict.return_value = {
        "ticket": 1,
        "order": 0,
        "position_id": 0,
        "symbol": "",
        "type": 2,  # BALANCE
        "entry": 0,
        "time": 1700000000,
        "volume": 0.0,
        "price": 0.0,
        "profit": 100000.0,
        "swap": 0.0,
        "commission": 0.0,
        "fee": 0.0,
        "comment": "Deposit",
        "magic": 0,
    }

    with patch("tradeaudit.infrastructure.mt5.history_reader.mt5") as mock_mt5, \
         patch("tradeaudit.infrastructure.mt5.history_reader.HAS_MT5", True):
        mock_mt5.history_deals_get.return_value = (mock_deal,)
        mock_mt5.history_orders_get.return_value = ()

        deals = reader.fetch_deals(
            account_id=123456,
            from_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            to_date=datetime(2024, 12, 31, tzinfo=timezone.utc),
        )

        assert len(deals) == 1
        assert deals[0].sl == 0.0
        assert deals[0].tp == 0.0
        assert deals[0].type == "BALANCE"
