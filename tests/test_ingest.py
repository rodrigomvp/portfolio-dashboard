"""Unit tests for portfolio.ingest.fetch_prices (Phase 1).

yf.download is replaced by a fake function, so these tests run offline
and always see the same data.
"""

import numpy as np
import pandas as pd
import pytest

from portfolio import ingest

FIELDS = ["Open", "High", "Low", "Close", "Volume"]


def _fake_download(tickers, **kwargs):
    """Mimic yf.download(..., group_by="ticker"): MultiIndex columns (Ticker, Price)."""
    dates = pd.DatetimeIndex(["2024-01-02", "2024-01-03"], name="Date")
    columns = pd.MultiIndex.from_product([tickers, FIELDS], names=["Ticker", "Price"])
    data = np.arange(len(dates) * len(columns), dtype=float).reshape(len(dates), -1) + 1
    df = pd.DataFrame(data, index=dates, columns=columns)
    if "BAD" in tickers:  # a wrong symbol comes back as all-NaN columns
        df.loc[:, "BAD"] = np.nan
    return df


@pytest.fixture(autouse=True)
def fake_yfinance(monkeypatch):
    monkeypatch.setattr(ingest.yf, "download", _fake_download)


def test_long_format_columns():
    df = ingest.fetch_prices(["AAA", "BBB"], start="2024-01-01")
    assert list(df.columns) == ["ticker", "date", "open", "high", "low", "close", "volume"]


def test_one_row_per_ticker_per_day():
    df = ingest.fetch_prices(["AAA", "BBB"], start="2024-01-01")
    assert len(df) == 4
    assert not df.duplicated(["ticker", "date"]).any()


def test_values_match_source():
    raw = _fake_download(["AAA", "BBB"])
    df = ingest.fetch_prices(["AAA", "BBB"], start="2024-01-01")
    row = df[(df["ticker"] == "BBB") & (df["date"] == pd.Timestamp("2024-01-03"))]
    assert row["close"].item() == raw.loc["2024-01-03", ("BBB", "Close")]


def test_single_ticker():
    df = ingest.fetch_prices(["AAA"], start="2024-01-01")
    assert len(df) == 2
    assert set(df["ticker"]) == {"AAA"}


def test_ticker_without_data_is_dropped():
    df = ingest.fetch_prices(["AAA", "BAD"], start="2024-01-01")
    assert set(df["ticker"]) == {"AAA"}
    assert df["close"].notna().all()


def test_ticker_without_data_logs_warning(caplog):
    ingest.fetch_prices(["AAA", "BAD"], start="2024-01-01")
    assert "BAD" in caplog.text
