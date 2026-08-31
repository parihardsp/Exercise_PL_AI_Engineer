"""
Database package — public interface.

Provides the session context manager get_db() and Repository access.

Usage:
    from db import get_db

    with get_db() as repo:
        rows = repo.fetch_all("SELECT * FROM portfolios;")
"""

from db.connection import Connection
from db.repository import Repository
from db.session import get_db

__all__ = [
    "get_db",
    "Repository",
    "Connection",
]
