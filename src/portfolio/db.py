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

REQUIRED_COLUMNS = ["ticker", "date", "open", "high", "low", "close", "volume"]


def get_connection(db_path: Path | str) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_prices(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    data = df[REQUIRED_COLUMNS].copy()
    data["date"] = pd.to_datetime(data["date"]).dt.strftime("%Y-%m-%d")
    data = data.astype(object).where(data.notna(), None)

    rows = list(data.itertuples(index=False, name=None))
    conn.executemany(
        "INSERT OR REPLACE INTO prices (ticker, date, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def last_date_per_ticker(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT ticker, MAX(date) FROM prices GROUP BY ticker").fetchall()

    return dict(rows)


def load_close_prices(
    conn: sqlite3.Connection,
    tickers: list[str],
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()

    placeholders = ", ".join("?" * len(tickers))
    query = f"SELECT date, ticker, close FROM prices WHERE ticker IN ({placeholders})"
    params = list(tickers)

    if start:
        query += " AND date >= ?"
        params.append(start)
    if end:
        query += " AND date <= ?"
        params.append(end)

    df = pd.read_sql_query(query, conn, params=params)
    wide = df.pivot(index="date", columns="ticker", values="close")
    wide.index = pd.to_datetime(wide.index)
    wide.columns.name = None
    return wide.sort_index()
