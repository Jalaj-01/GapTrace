"""Database session management and connection utilities."""

from typing import Any, Dict, Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger("app.db")


def normalize_db_url(url: str) -> str:
    """Normalize database URL for SQLAlchemy compatibility."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def create_configured_engine():
    """Initializes primary database engine with fallback handling for local development."""
    primary_url = normalize_db_url(settings.DATABASE_URL)
    is_sqlite = primary_url.startswith("sqlite")
    if is_sqlite:
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {"connect_timeout": 3}

    try:
        primary_engine = create_engine(
            primary_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        # Attempt immediate probe to confirm server reachability
        with primary_engine.connect() as probe_conn:
            probe_conn.execute(text("SELECT 1"))
        logger.info(f"Connected to primary database ({primary_engine.dialect.name}) at {primary_engine.url.host or 'local'}")
        return primary_engine, False
    except Exception as exc:
        if settings.ALLOW_SQLITE_DEV_FALLBACK and not is_sqlite:
            logger.warning(
                f"Primary PostgreSQL database unreachable ({exc}). "
                f"Falling back to development SQLite ({settings.SQLITE_FALLBACK_URL})."
            )
            fallback_engine = create_engine(
                settings.SQLITE_FALLBACK_URL,
                connect_args={"check_same_thread": False},
            )
            return fallback_engine, True
        else:
            logger.error(f"Failed to connect to database: {exc}")
            # Still return primary_engine so operational errors can be caught gracefully
            return primary_engine, False


engine, is_using_fallback = create_configured_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to yield database sessions with safe teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> Dict[str, Any]:
    """Tests the database connection and returns connection diagnostics."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "dialect": engine.dialect.name,
            "host": str(engine.url.host) if engine.url.host else "local_sqlite",
            "database": str(engine.url.database),
            "fallback_in_use": is_using_fallback,
        }
    except Exception as exc:
        logger.warning(f"Database connection check failed: {exc}")
        return {
            "status": "disconnected",
            "dialect": engine.dialect.name,
            "error": str(exc),
            "fallback_in_use": is_using_fallback,
        }
