"""
Application configuration management.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
import os
import sys

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


def is_frozen() -> bool:
    """Check if the application is running in a frozen/packaged bundle (e.g. PyInstaller)."""
    return getattr(sys, "frozen", False)


def get_resource_path(relative_path: str = "") -> Path:
    """Get absolute path to a resource, supporting both development and PyInstaller bundles."""
    if hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = BASE_DIR
    return base / relative_path if relative_path else base


def get_default_data_dir() -> Path:
    """
    Determine default application data directory.
    - If TRADEAUDIT_DATA_DIR is set in env, use it.
    - If running frozen or in production mode, use %LOCALAPPDATA%/TradeAudit on Windows.
    - Otherwise (development/testing), use BASE_DIR.
    """
    custom_dir = os.getenv("TRADEAUDIT_DATA_DIR")
    if custom_dir:
        return Path(custom_dir)

    env = os.getenv("TRADEAUDIT_ENV", "development").lower()
    if is_frozen() or env == "production":
        if sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA")
            if local_appdata:
                return Path(local_appdata) / "TradeAudit"
            return Path.home() / "AppData" / "Local" / "TradeAudit"
        return Path.home() / ".tradeaudit"

    return BASE_DIR


def get_default_database_url(data_dir: Path) -> str:
    """Get database URL pointing to the structured database path."""
    custom_url = os.getenv("TRADEAUDIT_DATABASE_URL")
    if custom_url:
        return custom_url

    # In dev without subfolder, fallback to base DB if existing in root.
    # Skip this legacy fallback when TRADEAUDIT_DATA_DIR was explicitly set,
    # otherwise it silently overrides the caller's chosen data directory.
    if (
        not is_frozen()
        and not os.getenv("TRADEAUDIT_DATA_DIR")
        and os.getenv("TRADEAUDIT_ENV", "development").lower() != "production"
    ):
        root_db = BASE_DIR / "tradeaudit.db"
        if root_db.exists():
            return f"sqlite:///{root_db}"
    
    db_file = data_dir / "database" / "tradeaudit.db"
    return f"sqlite:///{db_file}"


if HAS_PYDANTIC:
    class Settings(BaseSettings):
        app_name: str = "TradeAudit"
        app_version: str = "1.0.0"
        env: str = "development"
        debug: bool = True

        data_dir: Path = Field(default_factory=get_default_data_dir)
        log_level: str = "INFO"
        log_file_name: str = "tradeaudit.log"
        database_url: str = ""

        def model_post_init(self, __context) -> None:
            if not self.database_url:
                self.database_url = get_default_database_url(self.data_dir)

        @property
        def database_dir(self) -> Path:
            return self.data_dir / "database"

        @property
        def log_dir(self) -> Path:
            return self.data_dir / "logs"

        @property
        def export_dir(self) -> Path:
            return self.data_dir / "exports"

        @property
        def backup_dir(self) -> Path:
            return self.data_dir / "backups"

        @property
        def config_dir(self) -> Path:
            return self.data_dir / "config"

        @property
        def screenshots_dir(self) -> Path:
            return self.data_dir / "screenshots"

        def ensure_directories(self) -> None:
            """Ensure all application data subdirectories exist."""
            for directory in (
                self.data_dir,
                self.database_dir,
                self.log_dir,
                self.export_dir,
                self.backup_dir,
                self.config_dir,
                self.screenshots_dir,
            ):
                directory.mkdir(parents=True, exist_ok=True)

        model_config = SettingsConfigDict(
            env_prefix="TRADEAUDIT_",
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore"
        )
else:
    @dataclass
    class Settings:
        app_name: str = "TradeAudit"
        app_version: str = "1.0.0"
        env: str = os.getenv("TRADEAUDIT_ENV", "development")
        debug: bool = os.getenv("TRADEAUDIT_DEBUG", "True").lower() in ("true", "1")

        data_dir: Path = field(default_factory=get_default_data_dir)
        log_level: str = os.getenv("TRADEAUDIT_LOG_LEVEL", "INFO")
        log_file_name: str = "tradeaudit.log"
        database_url: str = ""

        def __post_init__(self):
            if not self.database_url:
                self.database_url = get_default_database_url(self.data_dir)

        @property
        def database_dir(self) -> Path:
            return self.data_dir / "database"

        @property
        def log_dir(self) -> Path:
            return self.data_dir / "logs"

        @property
        def export_dir(self) -> Path:
            return self.data_dir / "exports"

        @property
        def backup_dir(self) -> Path:
            return self.data_dir / "backups"

        @property
        def config_dir(self) -> Path:
            return self.data_dir / "config"

        @property
        def screenshots_dir(self) -> Path:
            return self.data_dir / "screenshots"

        def ensure_directories(self) -> None:
            """Ensure all application data subdirectories exist."""
            for directory in (
                self.data_dir,
                self.database_dir,
                self.log_dir,
                self.export_dir,
                self.backup_dir,
                self.config_dir,
                self.screenshots_dir,
            ):
                directory.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Retrieve application settings instance and ensure directory hierarchy."""
    settings = Settings()
    settings.ensure_directories()
    return settings
