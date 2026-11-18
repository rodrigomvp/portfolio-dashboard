"""Load project settings from config/settings.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"


@dataclass(frozen=True)
class Market:
    """One stock market: its assets, the indices they are compared with, and its currency."""

    name: str
    currency: str
    tickers: list[str]
    benchmarks: list[str]


@dataclass(frozen=True)
class Settings:
    markets: dict[str, Market]
    start_date: str
    end_date: str | None
    database_path: Path
    trading_days_per_year: int = 252
    base_currency: str = "EUR"
    risk_free_rates: dict[str, float] = field(default_factory=dict)
    fx_symbols: dict[str, str] = field(default_factory=dict)
    display_names: dict[str, str] = field(default_factory=dict)

    def label(self, symbol: str) -> str:
        """Name shown in the dashboard; falls back to the ticker symbol."""
        return self.display_names.get(symbol, symbol)

    def currency(self, symbol: str) -> str:
        """Currency of the market that lists `symbol` (the base currency if none does)."""
        for market in self.markets.values():
            if symbol in market.tickers or symbol in market.benchmarks:
                return market.currency
        return self.base_currency

    def risk_free_rate_for(self, currency: str) -> float:
        """Annual risk-free rate for returns measured in `currency`."""
        return self.risk_free_rates.get(currency, 0.0)

    @property
    def risk_free_rate(self) -> float:
        """Risk-free rate of the base currency (kept for the Phase 1-2 notebooks)."""
        return self.risk_free_rate_for(self.base_currency)

    @property
    def tickers(self) -> list[str]:
        return [t for m in self.markets.values() for t in m.tickers]

    @property
    def benchmarks(self) -> list[str]:
        return [b for m in self.markets.values() for b in m.benchmarks]

    @property
    def all_symbols(self) -> list[str]:
        """Everything to download: tickers and benchmarks of every market, plus exchange rates."""
        return [*self.tickers, *self.benchmarks, *self.fx_symbols.values()]


def load_settings(path: Path | str = DEFAULT_CONFIG_PATH) -> Settings:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    base_currency = raw.get("base_currency", "EUR")
    markets = {
        key: Market(
            name=m.get("name", key),
            currency=m.get("currency", base_currency),
            tickers=list(m["tickers"]),
            benchmarks=list(m["benchmarks"]),
        )
        for key, m in raw["markets"].items()
    }
    fx_symbols = dict(raw.get("fx_symbols") or {})

    missing = {m.currency for m in markets.values() if m.currency != base_currency} - set(fx_symbols)
    if missing:
        raise ValueError(f"No exchange rate in `fx_symbols` for: {sorted(missing)}")

    return Settings(
        markets=markets,
        start_date=str(raw["start_date"]),
        end_date=raw.get("end_date"),
        database_path=PROJECT_ROOT / raw.get("database_path", "data/prices.db"),
        trading_days_per_year=int(raw.get("trading_days_per_year", 252)),
        base_currency=base_currency,
        risk_free_rates={k: float(v) for k, v in (raw.get("risk_free_rates") or {}).items()},
        fx_symbols=fx_symbols,
        display_names=dict(raw.get("display_names") or {}),
    )