"""Mean-variance (Markowitz) portfolio optimisation.

Inputs are ANNUALISED expected returns (vector) and covariance matrix.
Constraints for this project: long-only (weights >= 0) and fully invested
(weights sum to 1).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

TRADING_DAYS = 252

def estimate_inputs(returns: pd.DataFrame, periods: int = TRADING_DAYS) -> tuple[np.ndarray, np.ndarray]:
    """Annualised expected returns (mean of daily returns x periods) and covariance (x periods)."""
    return returns.mean().to_numpy() * periods, returns.cov().to_numpy() * periods


def portfolio_performance(weights: np.ndarray, mean_returns: np.ndarray, cov: np.ndarray) -> tuple[float, float]:
    """Return (expected_return, volatility) for a weight vector.

    expected_return = w . mu
    volatility      = sqrt(w^T Σ w)
    """
    w = np.asarray(weights, dtype=float)
    return float(w @ mean_returns), float(np.sqrt(w @ cov @ w))


def random_portfolios(
    mean_returns: np.ndarray,
    cov: np.ndarray,
    n_portfolios: int = 5000,
    risk_free_rate: float = 0.0,
    seed: int = 42,
    asset_names: list[str] | None = None,
) -> pd.DataFrame:
    """Monte Carlo cloud of random long-only portfolios.

    Columns: return, volatility, sharpe, plus one weight column per asset.
    """
    rng = np.random.default_rng(seed)
    weights = rng.dirichlet(np.ones(len(mean_returns)), size=n_portfolios)
    rets = weights @ mean_returns
    vols = np.sqrt(((weights @ cov) * weights).sum(axis=1))  # w^T Σ w for every row

    names = asset_names or [f"w{i}" for i in range(len(mean_returns))]
    df = pd.DataFrame(weights, columns=names)
    df["return"] = rets
    df["volatility"] = vols
    df["sharpe"] = (rets - risk_free_rate) / vols
    return df


def _solve(objective, n: int, extra_constraints: tuple = ()) -> np.ndarray:
    """Minimise `objective` over long-only weights that sum to 1."""
    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1}, *extra_constraints]
    result = minimize(
        objective,
        x0=np.full(n, 1 / n),
        method="SLSQP",
        bounds=[(0, 1)] * n,
        constraints=constraints,
    )
    if not result.success:
        raise RuntimeError(f"Optimisation failed: {result.message}")
    w = np.clip(result.x, 0, None)  # remove tiny negative values like -1e-17
    return w / w.sum()


def min_variance_weights(cov: np.ndarray) -> np.ndarray:
    """Long-only minimum-variance portfolio."""
    return _solve(lambda w: w @ cov @ w, len(cov))


def max_sharpe_weights(mean_returns: np.ndarray, cov: np.ndarray, risk_free_rate: float = 0.0) -> np.ndarray:
    """Long-only tangency portfolio: minimise the NEGATIVE Sharpe ratio."""
    return _solve(lambda w: -(w @ mean_returns - risk_free_rate) / np.sqrt(w @ cov @ w), len(mean_returns))


def efficient_frontier(mean_returns: np.ndarray, cov: np.ndarray, n_points: int = 50) -> pd.DataFrame:
    """Minimum volatility for each target return, from the minimum-variance
    portfolio up to the best single asset. Columns: return, volatility.
    """
    w_min = min_variance_weights(cov)
    low = float(w_min @ mean_returns)
    high = float(np.max(mean_returns))

    rows = []
    for target in np.linspace(low, high, n_points):
        hit_target = {"type": "eq", "fun": lambda w, t=target: w @ mean_returns - t}
        w = _solve(lambda w: w @ cov @ w, len(mean_returns), (hit_target,))
        rows.append(portfolio_performance(w, mean_returns, cov))
    return pd.DataFrame(rows, columns=["return", "volatility"])



