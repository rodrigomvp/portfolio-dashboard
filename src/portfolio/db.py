"""SQLite storage for daily prices.

Schema (long / "tidy" format, one row per ticker per day):

    prices(ticker TEXT, date TEXT, open REAL, high REAL, low REAL,
           close REAL, volume INTEGER, PRIMARY KEY (ticker, date))
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    ticker  TEXT    NOT NULL,
    date    TEXT    NOT NULL,   -- ISO format YYYY-MM-DD
    open    REAL,
    high    REAL,
    low     REAL,
    close   REAL    NOT NULL,   -- adjusted close (dividends and splits)
    volume  INTEGER,
    PRIMARY KEY (ticker, date)
);
"""


def get_connection(db_path: Path | str) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_prices(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    """Insert or replace rows in `prices`. Returns the number of rows written.

    `df` must have the columns: ticker, date, open, high, low, close, volume.

    TODO (Phase 1):
      - Validate that the required columns exist.
      - Convert `date` to 'YYYY-MM-DD' strings.
      - Use `INSERT OR REPLACE INTO prices ...` with `conn.executemany`
        so running the update twice does not create duplicates.
    """
    raise NotImplementedError


def last_date_per_ticker(conn: sqlite3.Connection) -> dict[str, str]:
    """Return {ticker: most recent date stored}. Used for incremental updates.

    TODO (Phase 1): SELECT ticker, MAX(date) FROM prices GROUP BY ticker
    """
    raise NotImplementedError


def load_close_prices(
    conn: sqlite3.Connection,
    tickers: list[str],
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Return a wide DataFrame of closing prices.

    Index: DatetimeIndex (dates). Columns: one per ticker.

    TODO (Phase 1):
      - Query the long table with a parameterised WHERE ticker IN (...).
      - `pivot(index="date", columns="ticker", values="close")`.
      - Convert the index to datetime and sort it.
    """
    raise NotImplementedError
