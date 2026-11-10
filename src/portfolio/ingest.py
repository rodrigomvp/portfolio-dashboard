"""Download daily prices from Yahoo Finance (yfinance) into SQLite."""

from __future__ import annotations

import logging

import pandas as pd

from portfolio.config import Settings

logger = logging.getLogger(__name__)


def fetch_prices(tickers: list[str], start: str, end: str | None = None) -> pd.DataFrame:
    """Download OHLCV data and return it in long format.

    Output columns: ticker, date, open, high, low, close, volume.

    TODO (Phase 1):
      - `yf.download(tickers, start=start, end=end, auto_adjust=True,
        group_by="ticker", progress=False)`.
        With auto_adjust=True, "Close" is already adjusted for dividends
        and splits (there is no separate "Adj Close" column).
      - Reshape from wide (MultiIndex columns) to long:
        `.stack(level=0)` or loop per ticker, then `reset_index()`.
      - Rename columns to lowercase and drop rows where close is NaN.
      - Log a warning for any ticker that returned no data
        (usually a wrong symbol).
    """
    raise NotImplementedError


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
