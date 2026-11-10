"""Load project settings from config/settings.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "settings.yaml"


@dataclass(frozen=True)
class Settings:
    tickers: list[str]
    benchmark: str
    start_date: str
    end_date: str | None
    risk_free_rate: float
    trading_days_per_year: int
    database_path: Path

    @property
    def all_symbols(self) -> list[str]:
        """Portfolio tickers plus the benchmark."""
        return [*self.tickers, self.benchmark]


def load_settings(path: Path | str = DEFAULT_CONFIG_PATH) -> Settings:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return Settings(
        tickers=list(raw["tickers"]),
        benchmark=raw["benchmark"],
        start_date=str(raw["start_date"]),
        end_date=raw.get("end_date"),
        risk_free_rate=float(raw.get("risk_free_rate", 0.0)),
        trading_days_per_year=int(raw.get("trading_days_per_year", 252)),
        database_path=PROJECT_ROOT / raw.get("database_path", "data/prices.db"),
    )
