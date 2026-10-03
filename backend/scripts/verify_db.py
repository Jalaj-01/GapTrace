"""Database connection verification script."""

import sys
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import create_engine, text
from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, get_logger
from backend.app.db.base import Base
from backend.app.db.session import engine, check_db_connection, normalize_db_url
import backend.app.models.paper  # noqa: F401

setup_logging("INFO", "text")
logger = get_logger("scripts.verify_db")


def verify() -> bool:
    print("=" * 65)
    print("Scientific Paper Gap Finder - Database Diagnostics")
    print("=" * 65)
    print(f"Target Database URL: {settings.DATABASE_URL}")

    # 1. Direct test of the target PostgreSQL URL
    print("\n[Step 1] Testing Target PostgreSQL Connection...")
    target_url = normalize_db_url(settings.DATABASE_URL)
    pg_ok = False
    try:
        connect_args = {"connect_timeout": 3} if not target_url.startswith("sqlite") else {}
        direct_engine = create_engine(target_url, pool_pre_ping=True, connect_args=connect_args)
        with direct_engine.connect() as conn:
            val = conn.execute(text("SELECT 1")).scalar()
            print(f"  -> PostgreSQL Server is ONLINE (SELECT 1 = {val})")
            pg_ok = True
    except Exception as exc:
        print(f"  -> Target PostgreSQL Server is OFFLINE / unreachable: {exc}")
        print("  -> Tip: Start PostgreSQL service or run `docker compose up -d postgres`")

    # 2. Check Application Engine & Fallback Status
    print("\n[Step 2] Testing Application Engine & Schema...")
    diag = check_db_connection()
    print(f"  Active Engine Dialect: {engine.dialect.name}")
    print(f"  Active Engine Host:    {engine.url.host}")
    print(f"  Active Engine DB:      {engine.url.database}")
    print(f"  Connection Status:     {diag.get('status')}")
    print(f"  Dev Fallback Active:   {diag.get('fallback_in_use')}")

    if diag.get("status") == "connected":
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
                print(f"  Query Verification:    SUCCESS (SELECT 1 = {result})")
            Base.metadata.create_all(bind=engine)
            print("  Table Schema Check:    SUCCESS (Base.metadata.create_all passed)")
            print("\n[SUMMARY] Application database layer is fully functional!")
            return True
        except Exception as e:
            print(f"  [ERROR] Query execution failed: {e}")
            return False
    else:
        print(f"\n[ERROR] Database connection failed: {diag.get('error')}")
        return False


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
