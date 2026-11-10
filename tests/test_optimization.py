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
