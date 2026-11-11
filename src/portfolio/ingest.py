"""Download daily prices from Yahoo Finance (yfinance) into SQLite."""

from __future__ import annotations

import logging

import pandas as pd

import yfinance as yf

from portfolio.config import Settings

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


def update_database(settings: Settings) -> None:
    """Incremental update: only download what is not stored yet.

    TODO (Phase 1):
      1. Open connection + init_db.
      2. last_date_per_ticker() -> for each symbol, start from the day
         after the last stored date (or settings.start_date if new).
      3. fetch_prices() and upsert_prices().
      4. Log how many rows were written per ticker.
    """
    raise NotImplementedError
