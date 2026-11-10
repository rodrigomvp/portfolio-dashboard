"""Portfolio Risk Dashboard — Streamlit app.

Run with:  streamlit run app/streamlit_app.py

Rule: this file only handles layout and charts. Every number shown here
must come from a tested function in src/portfolio/.
"""

import streamlit as st

from portfolio.config import load_settings

st.set_page_config(page_title="Portfolio Risk Dashboard", page_icon="📈", layout="wide")

settings = load_settings()


# --------------------------------------------------------------------------
# Data loading (Phase 3)
# --------------------------------------------------------------------------
@st.cache_data(ttl=60 * 60)
def get_prices(tickers: tuple[str, ...], start: str, end: str | None):
    """TODO: open the DB and return db.load_close_prices(...)."""
    return None


# --------------------------------------------------------------------------
# Sidebar — user inputs
# --------------------------------------------------------------------------
st.sidebar.header("Portfolio")
selected = st.sidebar.multiselect("Assets", settings.tickers, default=settings.tickers)

st.sidebar.subheader("Weights")
weights = {}
for ticker in selected:
    weights[ticker] = st.sidebar.slider(ticker, 0.0, 1.0, round(1 / max(len(selected), 1), 2), 0.01)
# TODO: show a warning if weights do not sum to 1, or add a "normalise" button.

risk_free = st.sidebar.number_input("Risk-free rate (annual)", value=settings.risk_free_rate, step=0.005, format="%.3f")
# TODO: date range selector (st.sidebar.date_input).


# --------------------------------------------------------------------------
# Main page
# --------------------------------------------------------------------------
st.title("📈 Portfolio Risk Dashboard")
st.caption(f"Benchmark: {settings.benchmark} · Educational project, not investment advice.")

tab_overview, tab_risk, tab_corr, tab_opt = st.tabs(
    ["Overview", "Risk", "Correlation", "Optimisation"]
)

with tab_overview:
    st.info(
        "Phase 3 — KPI row (portfolio return, volatility, Sharpe, max drawdown) "
        "with st.metric; normalised price chart (base 100) vs benchmark; "
        "metrics.summary_table() as a formatted table."
    )

with tab_risk:
    st.info(
        "Phase 3/4 — drawdown chart (underwater plot); rolling 60-day volatility; "
        "histogram of daily returns with historical and parametric VaR lines."
    )

with tab_corr:
    st.info("Phase 3 — correlation heatmap of returns (Plotly imshow, diverging scale -1 to 1).")

with tab_opt:
    st.info(
        "Phase 4 — risk vs return scatter: Monte Carlo cloud coloured by Sharpe, "
        "efficient frontier line, individual assets, current portfolio, "
        "min-variance and max-Sharpe portfolios highlighted; table of suggested weights."
    )
