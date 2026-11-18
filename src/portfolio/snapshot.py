"""Text snapshot of the price database: data/prices.csv.

The SQLite file is not committed to git; this CSV is. A daily GitHub Action
refreshes it, and the deployed app rebuilds its database from it, so the app
never has to call Yahoo Finance itself.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from portfolio.db import get_connection, init_db, upsert_prices

COLUMNS = ["ticker", "date", "open", "high", "low", "close", "volume"]


def export_csv(db_path: Path | str, csv_path: Path | str) -> int:
    """Write every stored price to `csv_path`, sorted by ticker and date. Returns the row count.

    Sorting keeps the daily git diff small: new rows land at the end of each
    ticker's block instead of reshuffling the file.
    """
    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(f"SELECT {', '.join(COLUMNS)} FROM prices ORDER BY ticker, date", conn)
    finally:
        conn.close()
    df.to_csv(csv_path, index=False, float_format="%.6f")
    return len(df)


def sync_from_csv(db_path: Path | str, csv_path: Path | str) -> bool:
    """Load the CSV into the database when the database is missing or older than the CSV.

    Returns True when rows were loaded. Safe to call on every start: an
    up-to-date database is left alone.
    """
    db_path, csv_path = Path(db_path), Path(csv_path)
    if not csv_path.exists():
        return False
    if db_path.exists() and db_path.stat().st_mtime >= csv_path.stat().st_mtime:
        return False

    conn = get_connection(db_path)
    try:
        init_db(conn)
        upsert_prices(conn, pd.read_csv(csv_path))
    finally:
        conn.close()
    return True