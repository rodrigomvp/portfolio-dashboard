"""Return and risk metrics.

Conventions used throughout:
  - `prices`: wide DataFrame (index = dates, columns = tickers) or a Series.
  - `returns`: simple daily returns, same shape, first NaN row removed.
  - Annualisation with `periods` = 252 trading days by default.
  - Volatility uses the sample standard deviation (ddof=1, pandas default).

Run `pytest tests/test_metrics.py` to check each function as you implement it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def simple_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """r_t = P_t / P_{t-1} - 1, dropping the first (NaN) row.

    TODO (Phase 2): pct_change() + dropna(how="all")
    """
    raise NotImplementedError


def log_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """r_t = ln(P_t / P_{t-1}), dropping the first (NaN) row."""
    raise NotImplementedError


def annualized_return(returns: pd.DataFrame | pd.Series, periods: int = TRADING_DAYS):
    """Geometric annualised return (CAGR).

    (prod(1 + r)) ** (periods / n) - 1, where n = number of observations.
    """
    raise NotImplementedError


def annualized_volatility(returns: pd.DataFrame | pd.Series, periods: int = TRADING_DAYS):
    """std(r) * sqrt(periods)."""
    raise NotImplementedError


def sharpe_ratio(
    returns: pd.DataFrame | pd.Series,
    risk_free_rate: float = 0.0,
    periods: int = TRADING_DAYS,
):
    """Annualised Sharpe ratio.

    rf_per_period = risk_free_rate / periods
    sharpe = mean(r - rf_per_period) / std(r) * sqrt(periods)
    """
    raise NotImplementedError


def drawdown_series(prices: pd.Series) -> pd.Series:
    """Drawdown at each date: P_t / running_max(P) - 1 (values <= 0).

    Hint: prices.cummax()
    """
    raise NotImplementedError


def max_drawdown(prices: pd.Series) -> float:
    """Most negative value of drawdown_series (e.g. -0.25 for a 25% fall)."""
    raise NotImplementedError


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation of returns (never of prices — explain why in the README)."""
    raise NotImplementedError


def portfolio_returns(returns: pd.DataFrame, weights: dict[str, float] | np.ndarray) -> pd.Series:
    """Daily portfolio return = returns @ weights (daily rebalancing assumption).

    Validate that weights sum to 1 (np.isclose) and raise ValueError otherwise.
    """
    raise NotImplementedError


def beta(asset_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """beta = cov(asset, benchmark) / var(benchmark), on aligned dates."""
    raise NotImplementedError


def summary_table(
    prices: pd.DataFrame,
    risk_free_rate: float = 0.0,
    periods: int = TRADING_DAYS,
) -> pd.DataFrame:
    """One row per ticker with: annual return, annual volatility, Sharpe, max drawdown.

    This is the main table shown at the top of the dashboard.
    """
    raise NotImplementedError
