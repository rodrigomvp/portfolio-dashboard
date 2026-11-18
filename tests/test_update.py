"""Unit tests for portfolio.ingest.update_database (Phase 1).

fetch_prices is replaced by a fake that records every call, so the tests
run offline and can check which dates were requested.
"""

import sqlite3

import pandas as pd
import pytest

from portfolio import ingest
from portfolio.config import Market, Settings

LAST_AVAILABLE_DAY = "2024-01-05"


def make_settings(tmp_path, tickers=("AAA", "BBB")) -> Settings:
    """One test market, no exchange rates, a temporary database."""
    return Settings(
        markets={"TEST": Market(name="Test", currency="EUR", tickers=list(tickers), benchmarks=["IDX"])},
        start_date="2024-01-01",
        end_date=None,
        database_path=tmp_path / "test.db",
    )


@pytest.fixture
def settings(tmp_path):
    return make_settings(tmp_path)


@pytest.fixture
def calls(monkeypatch):
    """Replace fetch_prices; return the list of (ticker, start) it was called with."""
    recorded = []

    def fake_fetch_prices(tickers, start, end=None):
        recorded.extend((t, start) for t in tickers)
        dates = pd.bdate_range(start, LAST_AVAILABLE_DAY)
        rows = [
            {"ticker": t, "date": d, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 100}
            for t in tickers
            if t != "BAD"
            for d in dates
        ]
        return pd.DataFrame(rows, columns=ingest.COLUMNS)

    monkeypatch.setattr(ingest, "fetch_prices", fake_fetch_prices)
    return recorded


def _count_rows(settings) -> int:
    with sqlite3.connect(settings.database_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]


def test_first_run_starts_at_start_date(settings, calls):
    ingest.update_database(settings)
    assert sorted(calls) == [("AAA", "2024-01-01"), ("BBB", "2024-01-01"), ("IDX", "2024-01-01")]


def test_first_run_fills_database(settings, calls):
    ingest.update_database(settings)
    assert _count_rows(settings) == 3 * 5  # 3 symbols x 5 business days


def test_returns_rows_written_per_symbol(settings, calls):
    written = ingest.update_database(settings)
    assert written == {"AAA": 5, "BBB": 5, "IDX": 5}


def test_second_run_starts_at_last_stored_date(settings, calls):
    ingest.update_database(settings)
    calls.clear()
    ingest.update_database(settings)
    assert sorted(calls) == [("AAA", LAST_AVAILABLE_DAY), ("BBB", LAST_AVAILABLE_DAY), ("IDX", LAST_AVAILABLE_DAY)]


def test_second_run_does_not_duplicate(settings, calls):
    ingest.update_database(settings)
    ingest.update_database(settings)
    assert _count_rows(settings) == 3 * 5


def test_symbol_without_data_does_not_stop_the_others(settings, calls):
    settings = make_settings(settings.database_path.parent, tickers=("AAA", "BAD"))
    written = ingest.update_database(settings)
    assert written == {"AAA": 5, "BAD": 0, "IDX": 5}
