"""
Database session factory — mirrors FastAPI's get_db() / yield-db pattern.

Usage:
    from db.session import get_db

    with get_db() as repo:
        rows = repo.fetch_all("SELECT * FROM portfolios")

Configured directly via DB_READ_ONLY in .env:
  - DB_READ_ONLY=true  -> Read-Only Mode (URI mode=ro, PRAGMA query_only=ON)
  - DB_READ_ONLY=false -> Read-Write Mode (URI mode=rw, PRAGMA foreign_keys=ON)
"""

from contextlib import contextmanager
from typing import Generator, Optional

from db.connection import Connection
from db.repository import Repository


@contextmanager
def get_db(read_only: Optional[bool] = None) -> Generator[Repository, None, None]:
    """
    Open a database session managed directly via DB_READ_ONLY in .env.

    Each call produces an independent connection — safe for multi-threaded requests,
    CLI scripts, or long-lived agent tools.

    Args:
        read_only: Optional boolean override. When omitted (None), defaults
                   to DB_READ_ONLY from .env / utils.config.

    Example:
        with get_db() as repo:
            rows = repo.fetch_all("SELECT * FROM portfolios")
    """
    conn = Connection(read_only=read_only)
    conn.connect()
    try:
        yield Repository(conn)
    finally:
        conn.close()
