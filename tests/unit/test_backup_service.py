"""
Unit tests for BackupService (Phase 12).
"""

import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path
import pytest

from tradeaudit.app.config import Settings
from tradeaudit.app.services.backup_service import BackupService, BackupInfo
from tradeaudit.infrastructure.database.connection import DatabaseManager


def test_create_and_list_backups(temp_dir):
    """Test creating an atomic SQLite backup and listing available backups."""
    db_file = temp_dir / "database" / "tradeaudit.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize a sample database with a table and record
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, val TEXT);")
    conn.execute("INSERT INTO test_table (val) VALUES ('first_record');")
    conn.commit()
    conn.close()

    settings = Settings(
        data_dir=temp_dir,
        database_url=f"sqlite:///{db_file}"
    )
    service = BackupService(settings=settings)

    # 1. Create first backup
    b1_path = service.create_backup(tag="initial")
    assert b1_path.exists()
    assert b1_path.stat().st_size > 0
    assert "initial" in b1_path.name

    # 2. Create second backup
    b2_path = service.create_backup(tag="secondary")
    assert b2_path.exists()

    # 3. List backups (newest first)
    backups = service.list_backups()
    assert len(backups) == 2
    assert backups[0].path == b2_path
    assert backups[0].tag == "secondary"
    assert backups[1].path == b1_path
    assert backups[1].tag == "initial"


def test_restore_backup(temp_dir):
    """Test restoring a database from a backup file."""
    db_file = temp_dir / "database" / "tradeaudit.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)

    # State A: Insert 'original_data'
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, note TEXT);")
    conn.execute("INSERT INTO sample (note) VALUES ('original_data');")
    conn.commit()
    conn.close()

    settings = Settings(
        data_dir=temp_dir,
        database_url=f"sqlite:///{db_file}"
    )
    db_manager = DatabaseManager(settings)
    service = BackupService(settings=settings, db_manager=db_manager)

    # Create backup of State A
    backup_a = service.create_backup(tag="state_a")

    # State B: Modify database (insert corrupted/accidental record)
    conn2 = sqlite3.connect(str(db_file))
    conn2.execute("INSERT INTO sample (note) VALUES ('corrupted_data');")
    conn2.commit()
    conn2.close()

    # Verify State B has 2 records
    conn3 = sqlite3.connect(str(db_file))
    count = conn3.execute("SELECT COUNT(*) FROM sample;").fetchone()[0]
    conn3.close()
    assert count == 2

    # Restore back to State A
    res = service.restore_backup(backup_a)
    assert res is True

    # Verify State A is restored (only 1 record: 'original_data')
    conn4 = sqlite3.connect(str(db_file))
    rows = conn4.execute("SELECT note FROM sample;").fetchall()
    conn4.close()
    assert len(rows) == 1
    assert rows[0][0] == "original_data"

    db_manager.close()


def test_clean_old_backups(temp_dir):
    """Test retention management by deleting older backups exceeding keep_count."""
    db_file = temp_dir / "tradeaudit.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE t (id INT);")
    conn.commit()
    conn.close()

    settings = Settings(
        data_dir=temp_dir,
        database_url=f"sqlite:///{db_file}"
    )
    service = BackupService(settings=settings)

    # Create 5 dummy backup files
    for i in range(5):
        service.create_backup(tag=f"run_{i}")

    assert len(service.list_backups()) == 5

    # Retain only 2 most recent backups
    deleted = service.clean_old_backups(keep_count=2)
    assert deleted == 3
    assert len(service.list_backups()) == 2


def test_recent_backup_is_reused_for_pre_sync_protection(temp_dir):
    db_file = temp_dir / "tradeaudit.db"
    sqlite3.connect(db_file).close()
    service = BackupService(Settings(data_dir=temp_dir, database_url=f"sqlite:///{db_file}"))

    first = service.ensure_recent_backup()
    second = service.ensure_recent_backup()

    assert first.created is True
    assert second.created is False
    assert second.path == first.path
    assert len(service.list_backups()) == 1


def test_stale_backup_is_replaced_and_retention_is_enforced(temp_dir):
    db_file = temp_dir / "tradeaudit.db"
    sqlite3.connect(db_file).close()
    service = BackupService(Settings(data_dir=temp_dir, database_url=f"sqlite:///{db_file}"))
    old = service.create_backup(tag="old")
    stale = (datetime.now() - timedelta(days=2)).timestamp()
    os.utime(old, (stale, stale))

    result = service.ensure_recent_backup(max_age_hours=24, keep_count=1)

    assert result.created is True
    assert result.pruned == 1
    assert result.path.exists()
    assert old.exists() is False
    assert len(service.list_backups()) == 1
