import numpy as np
import pandas as pd

from portfolio import risk


def _sample_returns():
    rng = np.random.default_rng(1)
    return pd.Series(rng.normal(0.0005, 0.015, size=1000))


def test_var_is_positive_loss():
    assert risk.historical_var(_sample_returns(), 0.95) > 0


def test_cvar_at_least_var():
    r = _sample_returns()
    assert risk.historical_cvar(r, 0.95) >= risk.historical_var(r, 0.95)


def test_higher_confidence_means_higher_var():
    r = _sample_returns()
    assert risk.historical_var(r, 0.99) > risk.historical_var(r, 0.95)


def test_parametric_close_to_historical_for_normal_data():
    r = _sample_returns()
    assert abs(risk.parametric_var(r) - risk.historical_var(r)) < 0.005
