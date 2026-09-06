"""
Database connection manager and session factory using SQLAlchemy.
"""

import logging
from typing import Generator
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session

from tradeaudit.app.config import Settings
from tradeaudit.app.exceptions import DatabaseInitializationError
from tradeaudit.infrastructure.database.models import Base

logger = logging.getLogger("tradeaudit.database")


class DatabaseManager:
    """Manages SQLAlchemy Engine, Session creation, and schema initialization."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.database_url = settings.database_url
        
        # Enable SQLite Foreign Keys & WAL mode for thread safety
        connect_args = {}
        if self.database_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        try:
            self.engine = create_engine(
                self.database_url,
                connect_args=connect_args,
                echo=self.settings.debug
            )
            if self.database_url.startswith("sqlite"):
                # The comment above claimed these were already on - they weren't.
                # WAL matters now that the web UI's uvicorn server can genuinely
                # serve concurrent requests (unlike the old single-threaded Qt UI),
                # and foreign_keys=ON makes SQLite actually enforce the ON DELETE
                # CASCADE/SET NULL constraints declared in models.py.
                @event.listens_for(self.engine, "connect")
                def _set_sqlite_pragmas(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        except Exception as err:
            logger.error("Failed to create SQLAlchemy engine: %s", err)
            raise DatabaseInitializationError(f"Database engine setup failed: {err}") from err

    def init_db(self) -> None:
        """Create all defined metadata tables in SQLite."""
        try:
            logger.info("Initializing database schema at %s...", self.database_url)
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database schema initialized successfully.")
        except Exception as err:
            logger.error("Failed to initialize database tables: %s", err)
            raise DatabaseInitializationError(f"Table creation failed: {err}") from err

    def check_connection(self) -> bool:
        """Execute simple test query to verify SQLite health."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
                return result == 1
        except Exception as err:
            logger.error("Database health check failed: %s", err)
            return False

    def get_session(self) -> Generator[Session, None, None]:
        """Provide a transactional database session."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def session_scope(self):
        """Context manager for DB session handling."""
        from contextlib import contextmanager
        @contextmanager
        def _scope():
            session = self.SessionLocal()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        return _scope()

    def close(self) -> None:
        """Dispose database engine connections to release file locks."""
        if hasattr(self, "engine") and self.engine:
            self.engine.dispose()
            logger.info("Database connection engine disposed.")

