"""Unit tests for the multi-market helpers in portfolio.metrics and portfolio.config."""

import numpy as np
import pandas as pd
import pytest

from portfolio import metrics
from portfolio.config import load_settings


def test_align_fills_a_one_day_holiday():
    prices = pd.DataFrame(
        {"LISBON": [10.0, 11.0, 12.0], "NEW_YORK": [100.0, np.nan, 102.0]},
        index=pd.date_range("2024-07-03", periods=3),
    )
    aligned = metrics.align_calendars(prices)
    assert len(aligned) == 3
    assert aligned.loc["2024-07-04", "NEW_YORK"] == 100.0  # last price carried forward


def test_align_drops_dates_before_every_series_starts():
    prices = pd.DataFrame(
        {"OLD": [1.0, 2.0, 3.0], "NEW": [np.nan, np.nan, 5.0]},
        index=pd.date_range("2024-01-01", periods=3),
    )
    aligned = metrics.align_calendars(prices)
    assert list(aligned.index) == [pd.Timestamp("2024-01-03")]


def test_align_does_not_fill_long_gaps():
    prices = pd.DataFrame(
        {"A": [1.0] * 6, "B": [1.0, np.nan, np.nan, np.nan, np.nan, 1.0]},
        index=pd.date_range("2024-01-01", periods=6),
    )
    aligned = metrics.align_calendars(prices, max_gap=3)
    assert pd.Timestamp("2024-01-05") not in aligned.index  # 4th missing day in a row
    assert len(aligned) == 5


def test_align_drops_days_when_no_market_traded():
    prices = pd.DataFrame(
        {"A": [1.0, np.nan, 2.0], "B": [5.0, np.nan, 6.0]},
        index=pd.date_range("2024-12-24", periods=3),
    )
    aligned = metrics.align_calendars(prices)
    assert pd.Timestamp("2024-12-25") not in aligned.index


def test_periods_per_year_for_business_days():
    index = pd.bdate_range("2020-01-01", "2023-12-31")
    assert metrics.periods_per_year(index) == pytest.approx(261, abs=1)


def test_weekly_prices_keep_last_price_of_each_week():
    prices = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], index=pd.bdate_range("2024-01-01", periods=6))
    weekly = metrics.weekly_prices(prices)
    assert list(weekly.index) == [pd.Timestamp("2024-01-05"), pd.Timestamp("2024-01-12")]
    assert list(weekly) == [5.0, 6.0]


def _write(tmp_path, text):
    path = tmp_path / "settings.yaml"
    path.write_text(text, encoding="utf-8")
    return path


BASE = 'tickers: [A.LS, NVDA]\nstart_date: "2018-01-01"\n'


def test_config_reads_benchmarks_currencies_and_fx(tmp_path):
    settings = load_settings(_write(tmp_path, BASE + (
        "benchmarks: [PSI20.LS, ^GSPC]\n"
        "currencies: {NVDA: USD, ^GSPC: USD}\n"
        "fx_symbols: {USD: EURUSD=X}\n"
    )))
    assert settings.benchmarks == ["PSI20.LS", "^GSPC"]
    assert settings.currency("NVDA") == "USD"
    assert settings.currency("A.LS") == "EUR"
    assert settings.all_symbols == ["A.LS", "NVDA", "PSI20.LS", "^GSPC", "EURUSD=X"]


def test_config_still_accepts_a_single_benchmark(tmp_path):
    settings = load_settings(_write(tmp_path, BASE + "benchmark: PSI20.LS\n"))
    assert settings.benchmarks == ["PSI20.LS"]


def test_config_requires_an_exchange_rate_for_each_currency(tmp_path):
    with pytest.raises(ValueError):
        load_settings(_write(tmp_path, BASE + "benchmarks: [PSI20.LS]\ncurrencies: {NVDA: USD}\n"))
