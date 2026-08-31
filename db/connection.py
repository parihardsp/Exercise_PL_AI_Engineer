"""
SQLite Connection Manager.

Manages physical connection lifecycle, foreign key enforcement, and transactions.
"""

from pathlib import Path
import sqlite3
from typing import Any, Optional

from utils.config import DB_PATH, DB_READ_ONLY
from utils.logger import logger



class Connection:
    """
    SQLite Connection Manager with Role-Based Read/Write Isolation.

    - Lazily initialized: opens connection on first access.
    - Enables foreign key enforcement (PRAGMA foreign_keys = ON).
    - Configures dictionary-style row access (sqlite3.Row).
    - Read-Only Mode: Mounts via URI 'file:...db?mode=ro' with PRAGMA query_only=ON (Kernel lock).
    - Read-Write Mode: Standard connection with foreign key enforcement.
    """

    def __init__(self, db_path: Optional[Path] = None, read_only: Optional[bool] = None):
        self._db_path = db_path or DB_PATH
        self._read_only = DB_READ_ONLY if read_only is None else read_only
        self._conn: Optional[Any] = None


    def connect(self) -> Any:
        """Open physical database connection with role enforcement."""
        if self._conn is not None:
            return self._conn

        if not self._db_path.exists():
            raise FileNotFoundError(
                f"Database not found at '{self._db_path}'. Run 'python -m db.loader' first."
            )

        try:
            if self._read_only:
                self._conn = sqlite3.connect(f"file:{self._db_path.resolve()}?mode=ro", uri=True)
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA query_only = ON;")
                logger.info(f"[DB] Connected to {self._db_path.name} (mode=ro)")
            else:
                self._conn = sqlite3.connect(str(self._db_path))
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA foreign_keys = ON;")
                self._conn.commit()
                logger.info(f"[DB] Connected to {self._db_path.name} (mode=rw)")
            return self._conn
        except sqlite3.Error as e:
            raise ConnectionError(f"Failed to connect to '{self._db_path}': {e}") from e


    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        """Execute parameterized SQL on active connection."""
        conn = self.connect()
        return conn.execute(sql, params)

    def executemany(self, sql: str, params_list: list[tuple[Any, ...]]) -> Any:
        """Bulk execute parameterized SQL."""
        conn = self.connect()
        return conn.executemany(sql, params_list)

    def commit(self) -> None:
        """Commit active transaction."""
        if self._conn:
            self._conn.commit()

    def rollback(self) -> None:
        """Rollback active transaction."""
        if self._conn:
            self._conn.rollback()

    def close(self) -> None:
        """Close connection and reset state."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("[DB] Connection closed")

    def __enter__(self) -> "Connection":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        self.close()
        return False
