"""Unit tests for the Phase 3 helpers in portfolio.metrics."""

import numpy as np
import pandas as pd
import pytest

from portfolio import metrics


@pytest.fixture
def prices():
    return pd.DataFrame(
        {"A": [100.0, 110.0, 121.0], "B": [50.0, 45.0, 45.0]},
        index=pd.date_range("2024-01-01", periods=3),
    )


def test_rebase_starts_at_100(prices):
    rebased = metrics.rebase(prices)
    np.testing.assert_allclose(rebased.iloc[0], [100.0, 100.0])
    np.testing.assert_allclose(rebased["A"], [100.0, 110.0, 121.0])


def test_portfolio_value_single_asset_follows_its_price(prices):
    value = metrics.portfolio_value(prices, {"A": 1.0, "B": 0.0})
    np.testing.assert_allclose(value.values, [100.0, 110.0, 121.0])


def test_portfolio_value_keeps_dates_and_name(prices):
    value = metrics.portfolio_value(prices, {"A": 0.5, "B": 0.5})
    assert list(value.index) == list(prices.index)
    assert value.name == "Portfolio"


def test_portfolio_value_daily_rebalancing(prices):
    # day 1: 0.5*10% + 0.5*(-10%) = 0%  -> 100
    # day 2: 0.5*10% + 0.5*0%    = 5%  -> 105
    value = metrics.portfolio_value(prices, {"A": 0.5, "B": 0.5})
    np.testing.assert_allclose(value.values, [100.0, 100.0, 105.0])


def test_rolling_volatility():
    returns = pd.Series([0.01, -0.01, 0.01, -0.01, 0.01])
    vol = metrics.rolling_volatility(returns, window=3)
    assert vol.iloc[:2].isna().all()
    assert vol.iloc[2] == pytest.approx(returns.iloc[:3].std() * np.sqrt(252))
