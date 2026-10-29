"""
Application logging configuration.
"""

import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from tradeaudit.app.config import Settings


class SensitiveDataFilter(logging.Filter):
    """Redact common credentials and prevent forged multiline log entries."""

    _key_value = re.compile(
        r"(?i)(password|passwd|pwd|api[_-]?key|access[_-]?token|authorization)"
        r"(\s*[:=]\s*)([^\s,;]+)"
    )
    _bearer = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "_tradeaudit_redacted", False):
            return True
        message = record.getMessage()
        message = self._key_value.sub(r"\1\2[REDACTED]", message)
        message = self._bearer.sub(r"\1[REDACTED]", message)
        record.msg = message.replace("\r", "\\r").replace("\n", "\\n")
        record.args = ()
        record._tradeaudit_redacted = True
        return True


def setup_logging(settings: Settings) -> logging.Logger:
    """Configure console and file logging for TradeAudit."""
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = settings.log_dir / settings.log_file_name

    logger = logging.getLogger("tradeaudit")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # Avoid duplicate handlers if setup_logging is called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.addFilter(SensitiveDataFilter())
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.addHandler(console_handler)

    # Rotating File Handler (5 MB max, up to 3 backups)
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.addFilter(SensitiveDataFilter())
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.addHandler(file_handler)

    logger.info("Logging initialized. Output file: %s", log_file_path)
    return logger


def close_logging(logger: logging.Logger = None) -> None:
    """Close and detach all file handlers to release file locks on Windows."""
    if logger is None:
        logger = logging.getLogger("tradeaudit")
    
    handlers = logger.handlers[:]
    for handler in handlers:
        handler.close()
        logger.removeHandler(handler)

