import numpy as np

from portfolio import optimization


def test_min_variance_two_uncorrelated_assets():
    # Variances 0.01 and 0.04, no correlation -> weights proportional to 1/var -> [0.8, 0.2]
    cov = np.diag([0.01, 0.04])
    w = optimization.min_variance_weights(cov)
    np.testing.assert_allclose(w, [0.8, 0.2], atol=1e-4)


def test_max_sharpe_weights_are_valid():
    mu = np.array([0.08, 0.12, 0.10])
    cov = np.array([[0.04, 0.01, 0.00], [0.01, 0.09, 0.02], [0.00, 0.02, 0.06]])
    w = optimization.max_sharpe_weights(mu, cov, risk_free_rate=0.02)
    assert np.isclose(w.sum(), 1.0)
    assert (w >= -1e-8).all()


def test_random_portfolios_weights_sum_to_one():
    mu = np.array([0.08, 0.12])
    cov = np.diag([0.04, 0.09])
    df = optimization.random_portfolios(mu, cov, n_portfolios=100)
    weight_cols = [c for c in df.columns if c not in ("return", "volatility", "sharpe")]
    np.testing.assert_allclose(df[weight_cols].sum(axis=1), 1.0)


def test_estimate_inputs_annualises():
    import pandas as pd

    returns = pd.DataFrame({"A": [0.01, 0.03], "B": [0.02, 0.00]})
    mu, cov = optimization.estimate_inputs(returns, periods=252)
    np.testing.assert_allclose(mu, [0.02 * 252, 0.01 * 252])
    np.testing.assert_allclose(cov, returns.cov().to_numpy() * 252)


def test_portfolio_performance():
    mu = np.array([0.10, 0.20])
    cov = np.diag([0.04, 0.09])
    ret, vol = optimization.portfolio_performance(np.array([0.5, 0.5]), mu, cov)
    np.testing.assert_allclose([ret, vol], [0.15, np.sqrt(0.25 * 0.04 + 0.25 * 0.09)])


def test_efficient_frontier_shape():
    mu = np.array([0.08, 0.12, 0.10])
    cov = np.array([[0.04, 0.01, 0.00], [0.01, 0.09, 0.02], [0.00, 0.02, 0.06]])
    frontier = optimization.efficient_frontier(mu, cov, n_points=20)
    assert list(frontier.columns) == ["return", "volatility"]
    assert len(frontier) == 20
    # more return always costs more (or equal) risk along the frontier
    assert (frontier["volatility"].diff().dropna() >= -1e-6).all()
    # the first point is the minimum-variance portfolio
    w_min = optimization.min_variance_weights(cov)
    _, vol_min = optimization.portfolio_performance(w_min, mu, cov)
    assert abs(frontier["volatility"].iloc[0] - vol_min) < 1e-4
