from dataclasses import dataclass
from datetime import datetime, timezone

from tradeaudit.app.services.diagnostics_service import DiagnosticsService


@dataclass
class Backup:
    created_at: datetime


def service(tmp_path, **overrides):
    defaults = dict(
        app_version="1.2.3", environment="testing", data_dir=tmp_path,
        database_check=lambda: True, mt5_state=lambda: "CONNECTED",
        backups=lambda: [Backup(datetime.now(timezone.utc))],
    )
    defaults.update(overrides)
    return DiagnosticsService(**defaults)


def test_ready_report_contains_only_operational_metadata(tmp_path):
    report = service(tmp_path).collect()
    assert report.overall == "ready"
    assert report.app_version == "1.2.3"
    assert {check.key for check in report.checks} == {"database", "storage", "disk", "backup", "mt5"}
    assert all(check.status == "pass" for check in report.checks)
    assert not list(tmp_path.glob(".tradeaudit-health-*.tmp"))


def test_disconnected_mt5_and_missing_backup_are_degraded_not_failed(tmp_path):
    report = service(tmp_path, mt5_state=lambda: "DISCONNECTED", backups=lambda: []).collect()
    assert report.overall == "degraded"
    assert {check.key for check in report.checks if check.status == "warning"} == {"backup", "mt5"}


def test_database_failure_requires_attention(tmp_path):
    report = service(tmp_path, database_check=lambda: False).collect()
    assert report.overall == "attention"
    assert next(check for check in report.checks if check.key == "database").status == "fail"
