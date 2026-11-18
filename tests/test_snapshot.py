"""Unit tests for portfolio.snapshot (Phase 5: CSV snapshot for production)."""

import os

import pandas as pd
import pytest

from portfolio import db, snapshot


def _write_db(path, rows):
    conn = db.get_connection(path)
    db.init_db(conn)
    db.upsert_prices(conn, pd.DataFrame(rows))
    conn.close()


ROWS = {
    "ticker": ["BBB", "AAA", "AAA"],
    "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-02"]),
    "open": [1.0, 2.0, 3.0],
    "high": [1.0, 2.0, 3.0],
    "low": [1.0, 2.0, 3.0],
    "close": [20.0, 11.0, 10.0],
    "volume": [300, 200, 100],
}


@pytest.fixture
def paths(tmp_path):
    return tmp_path / "prices.db", tmp_path / "prices.csv"


def _count(path):
    conn = db.get_connection(path)
    n = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    conn.close()
    return n


def test_export_writes_every_row_sorted(paths):
    db_path, csv_path = paths
    _write_db(db_path, ROWS)
    assert snapshot.export_csv(db_path, csv_path) == 3
    df = pd.read_csv(csv_path)
    assert list(df.columns) == snapshot.COLUMNS
    assert list(zip(df["ticker"], df["date"])) == [
        ("AAA", "2024-01-02"), ("AAA", "2024-01-03"), ("BBB", "2024-01-02")
    ]


def test_round_trip_rebuilds_the_same_prices(paths, tmp_path):
    db_path, csv_path = paths
    _write_db(db_path, ROWS)
    snapshot.export_csv(db_path, csv_path)
    new_db = tmp_path / "rebuilt.db"
    assert snapshot.sync_from_csv(new_db, csv_path) is True
    conn = db.get_connection(new_db)
    prices = db.load_close_prices(conn, ["AAA", "BBB"])
    conn.close()
    assert prices.loc["2024-01-02", "AAA"] == 10.0
    assert prices.loc["2024-01-02", "BBB"] == 20.0


def test_sync_does_nothing_without_a_csv(paths):
    db_path, csv_path = paths
    assert snapshot.sync_from_csv(db_path, csv_path) is False
    assert not db_path.exists()


def test_sync_skips_an_up_to_date_database(paths):
    db_path, csv_path = paths
    _write_db(db_path, ROWS)
    snapshot.export_csv(db_path, csv_path)
    now = os.path.getmtime(csv_path)
    os.utime(db_path, (now + 10, now + 10))  # database newer than the CSV
    assert snapshot.sync_from_csv(db_path, csv_path) is False


def test_sync_loads_a_newer_csv(paths):
    db_path, csv_path = paths
    _write_db(db_path, {k: v[:1] for k, v in ROWS.items()})  # only one row
    pd.DataFrame(ROWS).assign(date=lambda d: d["date"].dt.strftime("%Y-%m-%d")).to_csv(csv_path, index=False)
    now = os.path.getmtime(db_path)
    os.utime(csv_path, (now + 10, now + 10))  # CSV newer, e.g. after a git pull
    assert snapshot.sync_from_csv(db_path, csv_path) is True
    assert _count(db_path) == 3
