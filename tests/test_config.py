"""Unit tests for portfolio.config (v1.2: one section per market)."""

import pytest

from portfolio.config import load_settings

CONFIG = """
markets:
  PT:
    name: Portugal
    currency: EUR
    tickers: [EDP.LS, GALP.LS]
    benchmarks: [PSI20.LS]
  US:
    name: United States
    currency: USD
    tickers: [NVDA, KO]
    benchmarks: [^GSPC, ^NDX]
base_currency: EUR
risk_free_rates: {EUR: 0.0278, USD: 0.043}
fx_symbols: {USD: EURUSD=X}
start_date: "2018-01-01"
"""


@pytest.fixture
def settings(tmp_path):
    path = tmp_path / "settings.yaml"
    path.write_text(CONFIG, encoding="utf-8")
    return load_settings(path)


def test_reads_each_market(settings):
    assert list(settings.markets) == ["PT", "US"]
    us = settings.markets["US"]
    assert us.name == "United States"
    assert us.currency == "USD"
    assert us.tickers == ["NVDA", "KO"]
    assert us.benchmarks == ["^GSPC", "^NDX"]


def test_currency_comes_from_the_market(settings):
    assert settings.currency("KO") == "USD"
    assert settings.currency("^NDX") == "USD"
    assert settings.currency("EDP.LS") == "EUR"
    assert settings.currency("UNKNOWN") == "EUR"  # falls back to the base currency


def test_risk_free_rate_per_currency(settings):
    assert settings.risk_free_rate_for("USD") == 0.043
    assert settings.risk_free_rate_for("EUR") == 0.0278
    assert settings.risk_free_rate == 0.0278  # base currency


def test_all_symbols_lists_every_market_and_the_fx_rate(settings):
    assert settings.all_symbols == [
        "EDP.LS", "GALP.LS", "NVDA", "KO", "PSI20.LS", "^GSPC", "^NDX", "EURUSD=X"
    ]


def test_requires_an_exchange_rate_for_each_foreign_market(tmp_path):
    path = tmp_path / "settings.yaml"
    path.write_text(CONFIG.replace("fx_symbols: {USD: EURUSD=X}", ""), encoding="utf-8")
    with pytest.raises(ValueError):
        load_settings(path)
