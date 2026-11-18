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
| Daily price ingestion (yfinance → SQLite, incremental updates) | ✅ Done |
| Returns, volatility, Sharpe, max drawdown, correlation, beta | ✅ Done |
| Interactive Streamlit dashboard | ✅ Done |
| Historical & parametric VaR / CVaR | ✅ Done |
| Efficient frontier, min-variance & max-Sharpe portfolios | ✅ Done |
| Two markets (Lisbon + New York) in euros, choice of benchmark (PSI, S&P 500, Nasdaq-100) | ✅ v1.1 |
| Market switch: Portugal vs PSI in EUR; 10 US stocks from 9 sectors vs S&P 500 / Nasdaq-100 in USD, with an option to show them in EUR | ✅ v1.2 |
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

## Design

The dashboard answers one question: *is this portfolio worth the risk it takes compared with the PSI index?*
The answer is written as a plain sentence at the top of the Overview, using the actual numbers; every chart below it supports that sentence.

- **Colour has one meaning.** Blue is the portfolio, and also the accent of every control that changes it. Orange is the PSI, and the index line is always dashed so the two series never depend on colour alone. Green and red appear only on deltas against the index, always with an arrow.
- **Contrast.** Text is at least 4.5:1 and chart lines at least 3:1 against the background, in both light and dark mode (tokens in `.streamlit/config.toml` and at the top of `app/streamlit_app.py`).
- **Every chart has a one-sentence summary** with real values (dates, percentages), so the main message does not depend on reading the chart.
- **One market at a time.** A segmented control switches between Portugal and the United States, so each portfolio is compared with its own index (comparing Nvidia with the PSI says nothing). Each market keeps its own assets, weights and benchmark when you switch back and forth. US figures are in dollars by default; *Show in euros* converts them to what an investor in euros would have earned.
- **Familiar controls.** Quick period ranges (1Y, 3Y, 5Y, Max) as in a stocks app, custom dates behind a toggle, weights as sliders with a one-click reset to equal weights, and assumptions (risk-free rate) tucked into an expander.
- **System font** (San Francisco on Apple devices, Segoe UI on Windows) and tabular figures so numbers do not jump while sliders move.

Guided by Apple's Human Interface Guidelines (accessibility, color, typography, charts).

## Methodology

### Data
- Source: Yahoo Finance via yfinance, adjusted daily closes (dividends and splits), Jan 2018 onwards.
- Currency: each market is shown in its own currency. With *Show in euros*, US prices are converted with the daily EUR/USD rate (`EURUSD=X`), so returns and volatility are those of a euro investor and include currency risk. Yahoo's daily rate is taken at the start of the London day, so each New York close uses Yahoo's next-day value (`fx.to_new_york_close`); without this, currency moves would land one day late (see `notebooks/03_us_data.ipynb`).
- Risk-free rate: one per currency, used in the Sharpe ratio — 3-month Euribor for EUR, 3-month US Treasury yield for USD (values and dates in `config/settings.yaml`). When US figures are shown in euros, the EUR rate is used.
- Quality checks: see `notebooks/01_data_quality.ipynb`.
- Missing data and calendars: in v1.0 (Lisbon only) the PSI index had no price on 12 of 2,272 dates (0.53%), and those dates were dropped. With two exchanges, Lisbon and New York close on different holidays, and dropping every incomplete date would remove about 4% of the data. Since v1.1 a closed market keeps its last price for up to 3 days, which is how funds value their holdings every day. Annualised figures use the number of observations per year actually in the data instead of a fixed 252.
- Outliers: 4 daily moves above 15% (COVID crash, Pfizer vaccine announcement, Galp's Namibia discovery, Jeronimo Martins H1 2024 results). All are real events and are kept, since removing them would understate risk.

## Limitations

- **Different closing times (v1.1 only).** Lisbon closes at 16:30 and New York at 21:00 (Lisbon time), so daily correlations between the two markets look lower than they are. Since v1.2 each market is analysed on its own, so this no longer affects the dashboard; it will matter again for a future mixed-market mode.
- **Small universes.** 6 Portuguese and 10 US stocks, chosen today: companies that were removed or went bankrupt since 2018 are not included (survivorship bias).
- **Price indices vs. adjusted prices.** Stock prices include dividends, but the PSI, S&P 500 and Nasdaq-100 are price indices. Comparisons with the index therefore favour the portfolio by roughly the index dividend yield.

_To be written: past performance vs. future returns, normality assumption in parametric VaR, data quality of yfinance._

## Tech stack

Python · pandas · NumPy · SciPy · SQLite · Plotly · Streamlit · pytest · GitHub Actions

## Disclaimer

Educational project. Nothing here is investment advice.
