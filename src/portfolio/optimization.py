"""Mean-variance (Markowitz) portfolio optimisation.

Inputs are ANNUALISED expected returns (vector) and covariance matrix.
Constraints for this project: long-only (weights >= 0) and fully invested
(weights sum to 1).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def portfolio_performance(weights: np.ndarray, mean_returns: np.ndarray, cov: np.ndarray) -> tuple[float, float]:
    """Return (expected_return, volatility) for a weight vector.

    expected_return = w . mu
    volatility      = sqrt(w^T Σ w)
    """
    raise NotImplementedError


def random_portfolios(
    mean_returns: np.ndarray,
    cov: np.ndarray,
    n_portfolios: int = 5000,
    risk_free_rate: float = 0.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Monte Carlo cloud of random long-only portfolios.

    Columns: return, volatility, sharpe, plus one weight column per asset.
    Hint: rng.dirichlet(np.ones(n_assets), size=n_portfolios) gives weights
    that are already >= 0 and sum to 1.
    """
    raise NotImplementedError


def min_variance_weights(cov: np.ndarray) -> np.ndarray:
    """Long-only minimum-variance portfolio.

    Use scipy.optimize.minimize with method="SLSQP",
    bounds=[(0, 1)] * n and constraint sum(w) == 1.
    """
    raise NotImplementedError


def max_sharpe_weights(mean_returns: np.ndarray, cov: np.ndarray, risk_free_rate: float = 0.0) -> np.ndarray:
    """Long-only tangency portfolio: minimise the NEGATIVE Sharpe ratio."""
    raise NotImplementedError


def efficient_frontier(mean_returns: np.ndarray, cov: np.ndarray, n_points: int = 50) -> pd.DataFrame:
    """For each target return between min and max asset return, find the
    minimum-volatility portfolio. Columns: return, volatility.
    """
    raise NotImplementedError
