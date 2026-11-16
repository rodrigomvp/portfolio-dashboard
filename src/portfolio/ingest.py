"""Download daily prices from Yahoo Finance (yfinance) into SQLite."""

from __future__ import annotations

import logging

import pandas as pd

import yfinance as yf

from portfolio.config import Settings

from portfolio.db import get_connection, init_db, last_date_per_ticker, upsert_prices

logger = logging.getLogger(__name__)

COLUMNS = ["ticker", "date", "open", "high", "low", "close", "volume"]


def fetch_prices(tickers: list[str], start: str, end: str | None = None) -> pd.DataFrame:
    raw = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        group_by="ticker",
        progress=False,
    )
    if raw.empty:
        logger.warning("No data returned for %s", tickers)
        return pd.DataFrame(columns=COLUMNS)

    long = raw.stack(level=0, future_stack=True).reset_index()
    long.columns = ["date", "ticker", *[str(c).lower() for c in long.columns[2:]]]
    long = long.dropna(subset=["close"])

    for ticker in sorted(set(tickers) - set(long["ticker"])):
        logger.warning("No data for %s (check the symbol on Yahoo Finance)", ticker)

    return long[COLUMNS].reset_index(drop=True)


def update_database(settings: Settings) -> dict[str, int]:
    """Incremental update. Returns {ticker: rows written}."""

    conn = get_connection(settings.database_path)
    try:
        init_db(conn)
        last_dates = last_date_per_ticker(conn)
        written = {}

        for ticker in settings.all_symbols:
            start = last_dates.get(ticker, settings.start_date)
            df = fetch_prices([ticker], start=start, end=settings.end_date)
            written[ticker] = upsert_prices(conn, df)
            logger.info("%s: %d rows written (from %s)", ticker, written[ticker], start)
    finally:
        conn.close()

    return written
