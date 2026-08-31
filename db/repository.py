"""
Database Repository — Provides parameterized access to the portfolio database.

All tool and agent SQL queries are executed through this repository.
"""

import sqlite3
from typing import Any, Optional

from db.connection import Connection
from utils.logger import logger


class Repository:
    """
    Provides clean, parameterized read and write access to the database.

    - Wraps sqlite3 errors into clear RuntimeErrors with failing SQL context.
    - Ensures 100% parameter binding safety to prevent SQL injection.
    """

    def __init__(self, connection: Connection):
        self._conn = connection

    def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Run a SELECT query and return matching rows as a list of dicts."""
        try:
            cursor = self._conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as e:
            raise RuntimeError(f"Query failed: {e}\nSQL: {sql}\nParams: {params}") from e
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e

    def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> Optional[dict[str, Any]]:
        """Run a SELECT query and return the first matching row as a dict, or None."""
        try:
            cursor = self._conn.execute(sql, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.OperationalError as e:
            raise RuntimeError(f"Query failed: {e}\nSQL: {sql}\nParams: {params}") from e
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error: {e}") from e

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        """Run a single write statement (INSERT / UPDATE / DELETE) and commit."""
        try:
            cursor = self._conn.execute(sql, params)
            self._conn.commit()
            return cursor.rowcount
        except (sqlite3.IntegrityError, sqlite3.OperationalError) as e:
            self._conn.rollback()
            raise RuntimeError(f"Write failed: {e}\nSQL: {sql}") from e
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Database error: {e}") from e

    def executemany(self, sql: str, params_list: list[tuple[Any, ...]]) -> None:
        """Bulk write using executemany — used by loader for CSV inserts."""
        try:
            self._conn.executemany(sql, params_list)
            self._conn.commit()
        except sqlite3.IntegrityError as e:
            self._conn.rollback()
            raise RuntimeError(f"Bulk write integrity error: {e}") from e
        except sqlite3.Error as e:
            self._conn.rollback()
            raise RuntimeError(f"Bulk write failed: {e}") from e

    def get_schema_string(self) -> str:
        """Return CREATE TABLE DDL for all user tables to inject into Text-to-SQL prompts."""
        rows = self.fetch_all(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name;"
        )
        statements = [row["sql"] for row in rows if row.get("sql")]
        schema = "\n\n".join(statements)
        logger.info(f"[DB] Schema loaded ({len(statements)} tables)")
        return schema
