"""Convert prices quoted in other currencies into the base currency (EUR)."""

from __future__ import annotations

import pandas as pd


def to_base_currency(prices: pd.DataFrame, currencies: dict[str, str], fx_rates: pd.DataFrame) -> pd.DataFrame:
    """Return `prices` with every column expressed in the base currency.

    currencies: {symbol: currency} for the symbols NOT quoted in the base currency.
    fx_rates:   one column per currency (e.g. "USD") with the units of that currency
                per 1 unit of base currency, as in Yahoo's EURUSD=X.
                A price of 110 USD with EURUSD = 1.10 becomes 100 EUR.

    On a date without an exchange rate, the most recent earlier rate is used.
    """
    missing = {c for s, c in currencies.items() if s in prices.columns} - set(fx_rates.columns)
    if missing:
        raise ValueError(f"No exchange rate for: {sorted(missing)}")

    all_dates = fx_rates.index.union(prices.index)
    rates = fx_rates.reindex(all_dates).sort_index().ffill().reindex(prices.index)

    converted = prices.copy()
    for symbol, currency in currencies.items():
        if symbol in converted.columns:
            converted[symbol] = converted[symbol] / rates[currency]
    return converted