"""
Database backup and restore service for TradeAudit.
"""

import logging
import os
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from tradeaudit.app.config import Settings
from tradeaudit.infrastructure.database.connection import DatabaseManager

logger = logging.getLogger("tradeaudit.backup")


@dataclass
class BackupInfo:
    """Metadata representing a database backup artifact."""
    filename: str
    path: Path
    size_bytes: int
    created_at: datetime
    tag: Optional[str] = None


@dataclass(frozen=True)
class BackupProtectionResult:
    """Outcome of enforcing the automatic safety-backup policy."""
    path: Path
    created: bool
    pruned: int = 0


class BackupService:
    """Provides atomic SQLite backups, restorations, and backup lifecycle management."""

    def __init__(self, settings: Settings, db_manager: Optional[DatabaseManager] = None):
        self.settings = settings
        self.db_manager = db_manager
        self.backup_dir = settings.backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _get_sqlite_db_path(self) -> Optional[Path]:
        """Extract filesystem path from sqlite database_url."""
        url = self.settings.database_url
        if not url.startswith("sqlite"):
            return None
        
        # Strip sqlite:/// prefix
        if url.startswith("sqlite:///"):
            path_str = url[len("sqlite:///"):]
            return Path(path_str)
        return None

    def create_backup(self, tag: Optional[str] = None) -> Path:
        """
        Create a reliable, timestamped SQLite backup in the configured backups directory.
        Uses SQLite online backup API to ensure ACID safety while the application is active.
        """
        db_path = self._get_sqlite_db_path()
        if not db_path:
            raise ValueError(f"Unsupported database URL for SQLite backup: {self.settings.database_url}")

        now = datetime.now()
        # Microseconds prevent two explicit backup operations in the same
        # second from silently targeting the same file.
        timestamp_str = now.strftime("%Y%m%d_%H%M%S%f")
        sanitized_tag = f"_{tag.strip().replace(' ', '_')}" if tag else ""
        backup_filename = f"tradeaudit_backup_{timestamp_str}{sanitized_tag}.db"
        dest_path = self.backup_dir / backup_filename

        if not db_path.exists():
            # If DB file doesn't exist yet, create empty SQLite DB
            logger.warning("Database file %s does not exist yet. Creating an empty backup file.", db_path)
            conn = sqlite3.connect(dest_path)
            conn.close()
            return dest_path

        src_conn = None
        dest_conn = None
        try:
            # Perform atomic SQLite online backup
            src_conn = sqlite3.connect(str(db_path))
            dest_conn = sqlite3.connect(str(dest_path))
            src_conn.backup(dest_conn)
            logger.info("Successfully created database backup at: %s", dest_path)
            return dest_path
        except Exception as err:
            logger.error("Failed to create online backup, falling back to copy: %s", err)
            try:
                shutil.copy2(db_path, dest_path)
                return dest_path
            except Exception as copy_err:
                logger.error("Backup creation failed completely: %s", copy_err)
                raise RuntimeError(f"Backup creation failed: {copy_err}") from copy_err
        finally:
            if dest_conn is not None:
                try:
                    dest_conn.close()
                except Exception:
                    pass
            if src_conn is not None:
                try:
                    src_conn.close()
                except Exception:
                    pass

    def list_backups(self) -> List[BackupInfo]:
        """List all available database backups ordered from newest to oldest."""
        if not self.backup_dir.exists():
            return []

        backups: List[BackupInfo] = []
        for file in self.backup_dir.glob("*.db"):
            try:
                stat = file.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                
                # Extract tag from filename if present
                # Standard format: tradeaudit_backup_YYYYMMDD_HHMMSS[_tag].db
                tag = None
                stem = file.stem
                if stem.startswith("tradeaudit_backup_"):
                    # e.g. ["tradeaudit", "backup", "20260831", "205220", "tag"]
                    parts = stem.split("_", 4)
                    if len(parts) > 4:
                        tag = parts[4]

                backups.append(
                    BackupInfo(
                        filename=file.name,
                        path=file,
                        size_bytes=stat.st_size,
                        created_at=mtime,
                        tag=tag
                    )
                )
            except Exception as err:
                logger.warning("Could not read backup file %s: %s", file, err)

        # Sort descending by created_at
        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups

    def restore_backup(self, backup_path: Path) -> bool:
        """
        Restore the database from a given backup file.
        Creates a temporary safety copy of the current database before restoring.
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        db_path = self._get_sqlite_db_path()
        if not db_path:
            raise ValueError(f"Cannot restore non-SQLite database: {self.settings.database_url}")

        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Dispose active connections if db_manager is present
        if self.db_manager:
            self.db_manager.close()

        # Step 1: Create safety snapshot of current DB if exists
        safety_path = self.backup_dir / "tradeaudit_pre_restore_safety.db"
        if db_path.exists():
            try:
                shutil.copy2(db_path, safety_path)
            except Exception as err:
                logger.warning("Could not create pre-restore safety copy: %s", err)

        # Step 2: Restore from backup
        src_conn = None
        dest_conn = None
        try:
            src_conn = sqlite3.connect(str(backup_path))
            dest_conn = sqlite3.connect(str(db_path))
            src_conn.backup(dest_conn)
            logger.info("Database successfully restored from %s", backup_path)

            if self.db_manager:
                self.db_manager.init_db()

            return True
        except Exception as err:
            logger.error("Database restore failed: %s", err)
            # Try to restore safety backup if available
            if safety_path.exists():
                try:
                    shutil.copy2(safety_path, db_path)
                except Exception:
                    pass
            raise RuntimeError(f"Database restoration failed: {err}") from err
        finally:
            if dest_conn is not None:
                try:
                    dest_conn.close()
                except Exception:
                    pass
            if src_conn is not None:
                try:
                    src_conn.close()
                except Exception:
                    pass

    def clean_old_backups(self, keep_count: int = 10) -> int:
        """
        Delete old backups keeping only the most recent `keep_count` backups.
        Returns the number of deleted files.
        """
        backups = self.list_backups()
        if len(backups) <= keep_count:
            return 0

        to_delete = backups[keep_count:]
        deleted_count = 0
        for backup in to_delete:
            try:
                if backup.path.exists():
                    backup.path.unlink()
                    deleted_count += 1
                    logger.info("Deleted old backup: %s", backup.filename)
            except Exception as err:
                logger.warning("Failed to delete old backup %s: %s", backup.filename, err)

        return deleted_count

    def ensure_recent_backup(
        self,
        *,
        tag: str = "pre_sync",
        max_age_hours: int = 24,
        keep_count: int = 10,
    ) -> BackupProtectionResult:
        """Create a safety snapshot only when no sufficiently recent backup exists.

        This is designed for high-frequency operations such as history sync:
        it provides a recovery point without producing an unbounded backup per
        click. Retention is enforced immediately after creating a new snapshot.
        """
        if max_age_hours < 1:
            raise ValueError("max_age_hours must be at least 1")
        if keep_count < 1:
            raise ValueError("keep_count must be at least 1")

        backups = self.list_backups()
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        if backups and backups[0].created_at >= cutoff:
            return BackupProtectionResult(path=backups[0].path, created=False)

        path = self.create_backup(tag=tag)
        pruned = self.clean_old_backups(keep_count=keep_count)
        return BackupProtectionResult(path=path, created=True, pruned=pruned)
