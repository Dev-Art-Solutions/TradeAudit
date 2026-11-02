"""Runtime readiness diagnostics with a privacy-safe support payload."""

import platform
import shutil
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable


@dataclass(frozen=True)
class DiagnosticCheck:
    key: str
    label: str
    status: str
    detail: str


@dataclass(frozen=True)
class DiagnosticsReport:
    generated_at: str
    overall: str
    app_version: str
    environment: str
    runtime: dict
    checks: list[DiagnosticCheck]

    def as_dict(self) -> dict:
        return asdict(self)


class DiagnosticsService:
    """Build an operational health snapshot without credentials or account IDs."""

    MIN_FREE_BYTES = 100 * 1024 * 1024

    def __init__(self, *, app_version: str, environment: str, data_dir: Path,
                 database_check: Callable[[], bool], mt5_state: Callable[[], str],
                 backups: Callable[[], Iterable]):
        self.app_version = app_version
        self.environment = environment
        self.data_dir = data_dir
        self.database_check = database_check
        self.mt5_state = mt5_state
        self.backups = backups

    def collect(self) -> DiagnosticsReport:
        checks = [self._database(), self._storage(), self._disk_space(), self._backup(), self._mt5()]
        statuses = {check.status for check in checks}
        overall = "attention" if "fail" in statuses else "degraded" if "warning" in statuses else "ready"
        return DiagnosticsReport(
            generated_at=datetime.now(timezone.utc).isoformat(), overall=overall,
            app_version=self.app_version, environment=self.environment,
            runtime={"python": platform.python_version(), "platform": sys.platform,
                     "architecture": platform.machine() or "unknown"}, checks=checks,
        )

    def _database(self) -> DiagnosticCheck:
        try:
            healthy = self.database_check()
        except Exception:
            healthy = False
        detail = "SQLite connection and integrity check passed." if healthy else "Database check failed; review the application log."
        return DiagnosticCheck("database", "Database integrity", "pass" if healthy else "fail", detail)

    def _storage(self) -> DiagnosticCheck:
        probe = self.data_dir / f".tradeaudit-health-{uuid.uuid4().hex}.tmp"
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            probe.write_bytes(b"ok")
            return DiagnosticCheck("storage", "Application storage", "pass", "Data directory is writable.")
        except OSError:
            return DiagnosticCheck("storage", "Application storage", "fail", "Data directory is not writable.")
        finally:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass

    def _disk_space(self) -> DiagnosticCheck:
        try:
            free = shutil.disk_usage(self.data_dir).free
        except OSError:
            return DiagnosticCheck("disk", "Free disk space", "fail", "Free space could not be measured.")
        status = "pass" if free >= self.MIN_FREE_BYTES else "warning"
        return DiagnosticCheck("disk", "Free disk space", status, f"{round(free / (1024 * 1024)):,} MB available.")

    def _backup(self) -> DiagnosticCheck:
        try:
            items = list(self.backups())
        except Exception:
            return DiagnosticCheck("backup", "Database backups", "fail", "Backup inventory could not be read.")
        if not items:
            return DiagnosticCheck("backup", "Database backups", "warning", "No database backup has been created yet.")
        newest = max(item.created_at for item in items)
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=timezone.utc)
        age_days = max(0, (datetime.now(timezone.utc) - newest.astimezone(timezone.utc)).days)
        status = "pass" if age_days <= 7 else "warning"
        return DiagnosticCheck("backup", "Database backups", status, f"{len(items)} backup(s); newest is {age_days} day(s) old.")

    def _mt5(self) -> DiagnosticCheck:
        try:
            state = self.mt5_state()
        except Exception:
            state = "ERROR"
        if state == "CONNECTED":
            return DiagnosticCheck("mt5", "MT5 adapter", "pass", "Connected and ready to sync.")
        if state == "ERROR":
            return DiagnosticCheck("mt5", "MT5 adapter", "fail", "The last MT5 connection attempt failed.")
        return DiagnosticCheck("mt5", "MT5 adapter", "warning", f"Adapter state: {state.lower()}.")
