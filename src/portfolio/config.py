"""Load project settings from config/settings.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"


@dataclass(frozen=True)
class Settings:
    tickers: list[str]
    benchmarks: list[str]
    start_date: str
    end_date: str | None
    risk_free_rate: float
    trading_days_per_year: int
    database_path: Path
    display_names: dict[str, str] = field(default_factory=dict)
    base_currency: str = "EUR"
    currencies: dict[str, str] = field(default_factory=dict)
    fx_symbols: dict[str, str] = field(default_factory=dict)

    def label(self, symbol: str) -> str:
        """Name shown in the dashboard; falls back to the ticker symbol."""
        return self.display_names.get(symbol, symbol)

    def currency(self, symbol: str) -> str:
        """Quote currency of a symbol (the base currency unless listed under `currencies`)."""
        return self.currencies.get(symbol, self.base_currency)

    @property
    def all_symbols(self) -> list[str]:
        """Everything to download: portfolio tickers, benchmarks and exchange rates."""
        return [*self.tickers, *self.benchmarks, *self.fx_symbols.values()]


def load_settings(path: Path | str = DEFAULT_CONFIG_PATH) -> Settings:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Older config files had a single `benchmark`; newer ones list several.
    benchmarks = list(raw.get("benchmarks") or [raw["benchmark"]])
    base_currency = raw.get("base_currency", "EUR")
    currencies = dict(raw.get("currencies") or {})
    fx_symbols = dict(raw.get("fx_symbols") or {})

    missing = {c for c in currencies.values() if c != base_currency} - set(fx_symbols)
    if missing:
        raise ValueError(f"No exchange rate in `fx_symbols` for: {sorted(missing)}")

    return Settings(
        tickers=list(raw["tickers"]),
        benchmarks=benchmarks,
        start_date=str(raw["start_date"]),
        end_date=raw.get("end_date"),
        risk_free_rate=float(raw.get("risk_free_rate", 0.0)),
        trading_days_per_year=int(raw.get("trading_days_per_year", 252)),
        database_path=PROJECT_ROOT / raw.get("database_path", "data/prices.db"),
        display_names=dict(raw.get("display_names") or {}),
        base_currency=base_currency,
        currencies=currencies,
        fx_symbols=fx_symbols,
    )