# Portfolio Risk Dashboard

Interactive dashboard to analyse the risk and return of a stock portfolio: returns, volatility, correlations, drawdowns, risk-adjusted performance, Value-at-Risk and mean-variance optimisation.

> 🚧 Work in progress — see [ROADMAP.md](ROADMAP.md) for the development plan.

**Live demo:** _coming soon (Phase 5)_

<!-- Phase 5: add a screenshot or GIF of the dashboard here -->

## Why this project

Most portfolio dashboards stop at descriptive charts. This one aims to support a decision: *given these assets, how should I allocate, and what risk am I taking?*

## Features

| Area | Status |
|---|---|
| Daily price ingestion (yfinance → SQLite, incremental updates) | ⬜ Phase 1 |
| Returns, volatility, Sharpe, max drawdown, correlation, beta | ⬜ Phase 2 |
| Interactive Streamlit dashboard | ⬜ Phase 3 |
| Historical & parametric VaR / CVaR | ⬜ Phase 4 |
| Efficient frontier, min-variance & max-Sharpe portfolios | ⬜ Phase 4 |
| Deployment + scheduled data refresh | ⬜ Phase 5 |

## Project structure

```
portfolio-dashboard/
├── app/streamlit_app.py        # Dashboard (UI only, no business logic)
├── config/settings.yaml        # Tickers, benchmark, dates, risk-free rate
├── data/                       # Local SQLite database (git-ignored)
├── scripts/update_data.py      # CLI entry point to refresh prices
├── src/portfolio/
│   ├── config.py               # Loads settings.yaml
│   ├── db.py                   # SQLite schema and read/write helpers
│   ├── ingest.py               # Downloads prices from yfinance
│   ├── metrics.py              # Return and risk metrics
│   ├── risk.py                 # VaR / CVaR
│   └── optimization.py         # Mean-variance optimisation
└── tests/                      # pytest unit tests
```

Design principle: **all calculations live in `src/portfolio/` and are unit-tested; the Streamlit app only displays them.**

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .

python scripts/update_data.py    # download prices into data/prices.db
streamlit run app/streamlit_app.py
pytest
```

## Methodology

_To be written as each phase is completed: formulas used, annualisation conventions (252 trading days), choice of risk-free rate, VaR method._

## Limitations

_To be written: survivorship bias, past performance vs. future returns, normality assumption in parametric VaR, data quality of yfinance._

## Tech stack

Python · pandas · NumPy · SciPy · SQLite · Plotly · Streamlit · pytest · GitHub Actions

## Disclaimer

Educational project. Nothing here is investment advice.
