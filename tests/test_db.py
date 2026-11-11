"""Unit tests for portfolio.db (Phase 1).

They use a temporary database file, so they never touch data/prices.db.
"""

import pandas as pd
import pytest

from portfolio import db


def _sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["AAA", "AAA", "BBB"],
            "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-02"]),
            "open": [1.0, 2.0, 3.0],
            "high": [1.0, 2.0, 3.0],
            "low": [1.0, 2.0, 3.0],
            "close": [10.0, 11.0, 20.0],
            "volume": [100, 200, 300],
        }
    )


@pytest.fixture
def conn(tmp_path):
    c = db.get_connection(tmp_path / "test.db")
    db.init_db(c)
    yield c
    c.close()


def _row_count(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]


def test_upsert_returns_rows_written(conn):
    assert db.upsert_prices(conn, _sample()) == 3
    assert _row_count(conn) == 3


def test_upsert_twice_does_not_duplicate(conn):
    db.upsert_prices(conn, _sample())
    db.upsert_prices(conn, _sample())
    assert _row_count(conn) == 3


def test_upsert_replaces_existing_values(conn):
    db.upsert_prices(conn, _sample())
    updated = _sample()
    updated.loc[0, "close"] = 99.0
    db.upsert_prices(conn, updated)
    close = conn.execute(
        "SELECT close FROM prices WHERE ticker = 'AAA' AND date = '2024-01-02'"
    ).fetchone()[0]
    assert close == 99.0


def test_upsert_rejects_missing_columns(conn):
    with pytest.raises(ValueError):
        db.upsert_prices(conn, _sample().drop(columns=["close"]))


def test_last_date_per_ticker(conn):
    db.upsert_prices(conn, _sample())
    assert db.last_date_per_ticker(conn) == {"AAA": "2024-01-03", "BBB": "2024-01-02"}


def test_last_date_per_ticker_empty_db(conn):
    assert db.last_date_per_ticker(conn) == {}


def test_load_close_prices_wide_format(conn):
    db.upsert_prices(conn, _sample())
    prices = db.load_close_prices(conn, ["AAA", "BBB"])
    assert isinstance(prices.index, pd.DatetimeIndex)
    assert sorted(prices.columns) == ["AAA", "BBB"]
    assert prices.loc["2024-01-02", "AAA"] == 10.0
    assert prices.loc["2024-01-02", "BBB"] == 20.0
    assert pd.isna(prices.loc["2024-01-03", "BBB"])


def test_load_close_prices_filters(conn):
    db.upsert_prices(conn, _sample())
    prices = db.load_close_prices(conn, ["AAA"], start="2024-01-03")
    assert list(prices.columns) == ["AAA"]
    assert len(prices) == 1
