"""
Unit tests for BehaviorService.
"""

from datetime import datetime, timezone, timedelta
import pytest

from tradeaudit.infrastructure.database.connection import DatabaseManager
from tradeaudit.infrastructure.repositories.trade_repository import TradeRepository
from tradeaudit.app.services.behavior_service import BehaviorService
from tradeaudit.domain.models import (
    Trade,
    EmotionTag,
    UserBehaviorAction,
    BehaviorFlag,
    BehaviorFlagType,
    ConfidenceLevel
)


@pytest.fixture
def repository(test_db_manager):
    return TradeRepository(test_db_manager)


@pytest.fixture
def behavior_service(repository):
    return BehaviorService(repository)


def test_update_emotion_tag(behavior_service, repository):
    account_id = 12345
    trade = Trade(
        account_id=account_id,
        position_id=101,
        symbol="EURUSD",
        direction="BUY",
        open_time=datetime.now(timezone.utc)
    )

    saved = repository.save_trades(account_id, [trade])
    trade_id = saved[0].id

    # Set valid emotion tag
    success = behavior_service.update_emotion_tag(trade_id, "FOMO", "Felt rushed")
    assert success is True

    # Retrieve trade and check emotion tag
    trades = repository.get_trades(account_id)
    assert trades[0].emotion_tag == EmotionTag.FOMO.value
    assert trades[0].behavior_notes == "Felt rushed"


def test_invalid_emotion_tag(behavior_service, repository):
    account_id = 12345
    trade = Trade(
        account_id=account_id,
        position_id=102,
        symbol="GBPUSD",
        direction="SELL",
        open_time=datetime.now(timezone.utc)
    )
    saved = repository.save_trades(account_id, [trade])
    trade_id = saved[0].id

    success = behavior_service.update_emotion_tag(trade_id, "INVALID_TAG")
    assert success is False


def test_confirm_and_reject_behavior_flags(behavior_service, repository):
    account_id = 12345
    trade = Trade(
        account_id=account_id,
        position_id=103,
        symbol="XAUUSD",
        direction="BUY",
        open_time=datetime.now(timezone.utc)
    )
    saved = repository.save_trades(account_id, [trade])
    trade_id = saved[0].id

    # Confirm
    behavior_service.confirm_behavior_flag(trade_id, "Confirmed revenge trade")
    trades = repository.get_trades(account_id)
    assert trades[0].user_behavior_action == UserBehaviorAction.CONFIRMED.value
    assert trades[0].behavior_notes == "Confirmed revenge trade"

    # Reject
    behavior_service.reject_behavior_flag(trade_id, "False alarm")
    trades = repository.get_trades(account_id)
    assert trades[0].user_behavior_action == UserBehaviorAction.REJECTED.value
    assert trades[0].behavior_notes == "False alarm"


def test_run_behavior_analysis_for_account(behavior_service, repository):
    account_id = 99999
    base_time = datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc)

    # Trade 1: losing trade
    trade1 = Trade(
        account_id=account_id,
        position_id=201,
        symbol="EURUSD",
        direction="BUY",
        volume=1.0,
        open_time=base_time,
        close_time=base_time + timedelta(minutes=10),
        profit=-200.0,
        status="CLOSED",
        monetary_risk=200.0
    )

    # Trade 2: revenge trade 5 min later with 2x volume
    trade2 = Trade(
        account_id=account_id,
        position_id=202,
        symbol="EURUSD",
        direction="BUY",
        volume=2.0,
        open_time=base_time + timedelta(minutes=15),
        profit=0.0,
        status="OPEN",
        monetary_risk=400.0
    )

    repository.save_trades(account_id, [trade1, trade2])

    analysis_map = behavior_service.run_behavior_analysis_for_account(account_id)

    # Check retrieved trades from repository
    trades = repository.get_trades(account_id)
    trade2_fetched = next(t for t in trades if t.position_id == 202)

    assert len(trade2_fetched.auto_behavior_flags) > 0
    flag_types = [f.flag_type for f in trade2_fetched.auto_behavior_flags]
    assert BehaviorFlagType.POSSIBLE_REVENGE_TRADE in flag_types


def test_bulk_update_emotion_tags(behavior_service, repository):
    account_id = 999
    trade1 = Trade(account_id=account_id, position_id=301, open_time=datetime.now(timezone.utc), profit=10.0, status="CLOSED")
    trade2 = Trade(account_id=account_id, position_id=302, open_time=datetime.now(timezone.utc), profit=-10.0, status="CLOSED")
    saved = repository.save_trades(account_id, [trade1, trade2])
    t1_id, t2_id = saved[0].id, saved[1].id

    # Bulk update to FOMO
    count = behavior_service.bulk_update_emotion_tags([t1_id, t2_id], emotion_tag="FOMO")
    assert count == 2

    trades = {t.id: t for t in repository.get_trades(account_id)}
    assert trades[t1_id].emotion_tag == "FOMO"
    assert trades[t2_id].emotion_tag == "FOMO"

    # Bulk clear emotion
    count_clear = behavior_service.bulk_update_emotion_tags([t1_id, t2_id], emotion_tag=None, clear_emotion=True)
    assert count_clear == 2

    trades_after = {t.id: t for t in repository.get_trades(account_id)}
    assert trades_after[t1_id].emotion_tag is None
    assert trades_after[t2_id].emotion_tag is None

    # Invalid tag returns 0
    bad_count = behavior_service.bulk_update_emotion_tags([t1_id, t2_id], emotion_tag="NOT_AN_EMOTION")
    assert bad_count == 0
