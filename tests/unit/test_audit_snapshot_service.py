import json
from datetime import datetime, timedelta, timezone

from tradeaudit.app.services.audit_snapshot_service import AuditSnapshotService
from tradeaudit.domain.models import Trade


def trade(position_id: int, hours: int, profit: float) -> Trade:
    opened = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=hours)
    return Trade(
        account_id=999999, position_id=position_id, symbol="EURUSD", direction="BUY",
        volume=0.1, open_time=opened, close_time=opened + timedelta(hours=1),
        open_price=1.1, close_price=1.11, initial_sl=1.09, initial_tp=1.12,
        profit=profit, realized_r=profit / 10, status="CLOSED",
        strategy_id=1, compliance_status="COMPLIANT", emotion_tag="CALM",
    )


def test_fingerprint_is_stable_across_input_order_and_identity_fields():
    first, second = trade(101, 0, 20), trade(102, 2, -10)
    one = AuditSnapshotService.build([first, second], "1.2.3")
    first.account_id = 123
    first.position_id = 888
    two = AuditSnapshotService.build([second, first], "1.2.3")

    assert one.dataset_sha256 == two.dataset_sha256
    assert len(one.dataset_sha256) == 64


def test_snapshot_contains_aggregate_evidence_without_identifiers():
    snapshot = AuditSnapshotService.build([trade(101, 0, 20)], "1.2.3").as_dict()
    serialized = json.dumps(snapshot).lower()

    assert snapshot["schema_version"] == 1
    assert snapshot["trade_count"] == 1
    assert snapshot["metrics"]["net_profit"] == 20
    assert snapshot["data_quality"]["score"] == 100
    assert "account_id" not in serialized
    assert "position_id" not in serialized


def test_changing_audited_value_changes_fingerprint():
    item = trade(101, 0, 20)
    before = AuditSnapshotService.build([item], "1.2.3").dataset_sha256
    item.realized_r = 3.0
    after = AuditSnapshotService.build([item], "1.2.3").dataset_sha256
    assert before != after
