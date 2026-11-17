"""Value-at-Risk and Expected Shortfall (CVaR).

Sign convention: VaR and CVaR are returned as POSITIVE numbers representing
losses. A 1-day 95% VaR of 0.021 means: "on 95% of days, the loss should not
exceed 2.1%".
"""

from __future__ import annotations

import pandas as pd

from scipy.stats import norm


def historical_var(returns: pd.Series, level: float = 0.95) -> float:
    """Empirical quantile: -quantile(returns, 1 - level)."""
    return float(-returns.quantile(1 - level))

def historical_cvar(returns: pd.Series, level: float = 0.95) -> float:
    """Average loss on the days that are worse than the VaR threshold."""
    threshold = returns.quantile(1 - level)
    return float(-returns[returns <= threshold].mean())


def parametric_var(returns: pd.Series, level: float = 0.95) -> float:
    """Gaussian VaR: -(mean + z * std), with z = scipy.stats.norm.ppf(1 - level).

    In the dashboard, compare it with historical VaR — the gap shows how far
    real returns are from a normal distribution (fat tails).
    """
    z = norm.ppf(1 - level)
    return float(-(returns.mean() + z * returns.std()))
