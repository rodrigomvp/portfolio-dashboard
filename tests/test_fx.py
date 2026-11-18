"""Unit tests for portfolio.fx (multi-market version)."""

import numpy as np
import pandas as pd
import pytest

from portfolio import fx


@pytest.fixture
def prices():
    return pd.DataFrame(
        {"EUR_STOCK": [10.0, 11.0, 12.0], "US_STOCK": [110.0, 121.0, 132.0]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    )


def test_converts_usd_to_eur(prices):
    rates = pd.DataFrame({"USD": [1.10, 1.10, 1.20]}, index=prices.index)
    out = fx.to_base_currency(prices, {"US_STOCK": "USD"}, rates)
    np.testing.assert_allclose(out["US_STOCK"], [100.0, 110.0, 110.0])


def test_base_currency_columns_unchanged(prices):
    rates = pd.DataFrame({"USD": [1.10, 1.10, 1.20]}, index=prices.index)
    out = fx.to_base_currency(prices, {"US_STOCK": "USD"}, rates)
    pd.testing.assert_series_equal(out["EUR_STOCK"], prices["EUR_STOCK"])


def test_missing_rate_uses_previous_day(prices):
    rates = pd.DataFrame({"USD": [1.10, 1.25]}, index=pd.to_datetime(["2024-01-02", "2024-01-04"]))
    out = fx.to_base_currency(prices, {"US_STOCK": "USD"}, rates)
    assert out.loc["2024-01-03", "US_STOCK"] == pytest.approx(121.0 / 1.10)


def test_unknown_currency_raises(prices):
    rates = pd.DataFrame({"USD": [1.10, 1.10, 1.20]}, index=prices.index)
    with pytest.raises(ValueError):
        fx.to_base_currency(prices, {"US_STOCK": "GBP"}, rates)


def test_new_york_close_takes_the_next_days_value():
    dates = pd.to_datetime(["2022-11-09", "2022-11-10", "2022-11-11"])
    yahoo = pd.DataFrame({"USD": [1.008, 1.002, 1.019]}, index=dates)
    aligned = fx.to_new_york_close(yahoo)
    np.testing.assert_allclose(aligned["USD"], [1.002, 1.019, 1.019])  # last day keeps its own value


def test_new_york_close_skips_dates_without_a_rate():
    dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
    yahoo = pd.DataFrame({"USD": [1.10, np.nan, 1.12]}, index=dates)
    aligned = fx.to_new_york_close(yahoo)
    assert list(aligned.index) == [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-04")]
    np.testing.assert_allclose(aligned["USD"], [1.12, 1.12])
