"""
CSV → SQLite loader for Portfolio Analytics Agent.

Reads all 9 CSVs from the data/ directory and inserts them into
portfolio_database.db following the schema in database_schema.sql.

Run this once before starting the agent:
    python -m db.loader

Safe to re-run — uses INSERT OR IGNORE so existing rows are skipped.
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import DATA_DIR, DB_PATH, SCHEMA_PATH
from utils.logger import logger

# Load order respects FK dependencies:
# referenced tables must be populated before tables that reference them.
LOAD_ORDER = [
    ("sectors", "sectors.csv"),
    ("benchmarks", "benchmarks.csv"),
    ("portfolios", "portfolios.csv"),
    ("securities", "securities.csv"),
    ("holdings", "holdings.csv"),
    ("transactions", "transactions.csv"),
    ("historical_prices", "historical_prices.csv"),
    ("portfolio_performance", "portfolio_performance.csv"),
    ("risk_metrics", "risk_metrics.csv"),
]


def _apply_schema(conn: sqlite3.Connection) -> None:
    """Execute database_schema.sql to create tables and indices."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()
    logger.info(f"[LOADER] Schema applied from {SCHEMA_PATH.name}")


def _load_table(conn: sqlite3.Connection, table: str, csv_file: Path) -> int:
    """
    Load a single CSV file into the given table.

    - NaN values from pandas are converted to None (→ SQL NULL).
    - Uses INSERT OR IGNORE so re-running the loader is safe.
    - Returns the number of rows inserted.
    """
    if not csv_file.exists():
        logger.warning(f"[LOADER] CSV not found, skipping: {csv_file.name}")
        return 0

    df = pd.read_csv(csv_file)

    # Replace NaN/NaT with None so sqlite3 stores them as NULL
    # pyrefly: ignore [bad-argument-type]
    df = df.where(pd.notnull(df), None)

    columns = ", ".join(df.columns)
    placeholders = ", ".join(["?" for _ in df.columns])
    sql = f"INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})"

    rows = [tuple(row) for row in df.itertuples(index=False, name=None)]

    try:
        conn.executemany(sql, rows)
        conn.commit()
        inserted = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        logger.info(f"[LOADER] {table:<25} -> {inserted:>4} rows")
        return inserted
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"[LOADER] Failed to load {table}: {e}")
        raise


def run_loader() -> None:
    """
    Main entry point. Creates the DB file, applies the schema,
    and loads all 9 CSVs in FK-safe order.
    """
    logger.info(f"[LOADER] Initialising database at: {DB_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON;")

    try:
        _apply_schema(conn)

        total_rows = 0
        for table, csv_name in LOAD_ORDER:
            csv_path = DATA_DIR / csv_name
            total_rows += _load_table(conn, table, csv_path)

        logger.info(f"[LOADER] Done. {total_rows} total rows loaded into {DB_PATH.name}")

    except Exception as e:
        logger.error(f"[LOADER] Load failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_loader()
