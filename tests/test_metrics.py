"""Unit tests for portfolio.metrics.

These tests are the specification: implement each function in
src/portfolio/metrics.py until its test passes.
"""

import numpy as np
import pandas as pd
import pytest

from portfolio import metrics


def test_simple_returns():
    prices = pd.Series([100.0, 110.0, 99.0])
    r = metrics.simple_returns(prices)
    assert len(r) == 2
    np.testing.assert_allclose(r.values, [0.10, -0.10])


def test_log_returns():
    prices = pd.Series([100.0, 110.0])
    r = metrics.log_returns(prices)
    np.testing.assert_allclose(r.values, [np.log(1.1)])


def test_annualized_return_compounds():
    returns = pd.Series([0.01] * 12)
    assert metrics.annualized_return(returns, periods=12) == pytest.approx(1.01**12 - 1)


def test_annualized_volatility_of_constant_returns_is_zero():
    returns = pd.Series([0.005] * 50)
    assert metrics.annualized_volatility(returns) == pytest.approx(0.0)


def test_annualized_volatility_scaling():
    returns = pd.Series([0.01, -0.01, 0.01, -0.01])
    expected = returns.std() * np.sqrt(252)
    assert metrics.annualized_volatility(returns) == pytest.approx(expected)


def test_sharpe_ratio():
    returns = pd.Series([0.01, 0.03])
    # mean 0.02, sample std 0.014142 -> 1.4142 with periods=1 and rf=0
    assert metrics.sharpe_ratio(returns, risk_free_rate=0.0, periods=1) == pytest.approx(np.sqrt(2))


def test_drawdown_series():
    prices = pd.Series([100.0, 120.0, 90.0, 130.0])
    dd = metrics.drawdown_series(prices)
    np.testing.assert_allclose(dd.values, [0.0, 0.0, -0.25, 0.0])


def test_max_drawdown():
    prices = pd.Series([100.0, 120.0, 90.0, 130.0, 104.0])
    assert metrics.max_drawdown(prices) == pytest.approx(-0.25)


def test_correlation_matrix_diagonal_is_one():
    rng = np.random.default_rng(0)
    returns = pd.DataFrame(rng.normal(size=(100, 3)), columns=["A", "B", "C"])
    corr = metrics.correlation_matrix(returns)
    np.testing.assert_allclose(np.diag(corr.values), [1.0, 1.0, 1.0])


def test_portfolio_returns():
    returns = pd.DataFrame({"A": [0.10, 0.00], "B": [0.00, 0.20]})
    port = metrics.portfolio_returns(returns, {"A": 0.5, "B": 0.5})
    np.testing.assert_allclose(port.values, [0.05, 0.10])


def test_portfolio_returns_rejects_bad_weights():
    returns = pd.DataFrame({"A": [0.1], "B": [0.0]})
    with pytest.raises(ValueError):
        metrics.portfolio_returns(returns, {"A": 0.7, "B": 0.7})


def test_beta():
    bench = pd.Series([0.01, -0.02, 0.03, 0.00])
    asset = 2 * bench
    assert metrics.beta(asset, bench) == pytest.approx(2.0)


def test_summary_table():
    prices = pd.DataFrame(
        {"A": [100.0, 110.0, 99.0, 120.0], "B": [50.0, 51.0, 52.0, 50.0]},
        index=pd.date_range("2024-01-01", periods=4),
    )
    table = metrics.summary_table(prices, risk_free_rate=0.0)
    assert list(table.index) == ["A", "B"]
    assert list(table.columns) == ["Annual return", "Annual volatility", "Sharpe ratio", "Max drawdown"]
    returns = metrics.simple_returns(prices["A"])
    assert table.loc["A", "Annual volatility"] == pytest.approx(metrics.annualized_volatility(returns))
    assert table.loc["A", "Max drawdown"] == pytest.approx(-0.10)
