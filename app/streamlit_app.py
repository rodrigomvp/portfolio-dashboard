"""Portfolio Risk Dashboard — Streamlit app.

Run with:  streamlit run app/streamlit_app.py

Rule: this file only handles inputs, layout and charts. Every number shown
here comes from a tested function in src/portfolio/.

Design: the screen answers one question — is this portfolio worth the risk
it takes compared with its market's index? The answer is written as a plain
sentence at the top of the page; everything else supports it.

Data: prices come from data/prices.csv, refreshed every weekday by a GitHub
Action. The app loads it into SQLite on start and never calls Yahoo itself.
Theme colours live in .streamlit/config.toml; chart colours are below.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Streamlit Community Cloud installs requirements.txt but not this package
# (`pip install -e .`), so make src/ importable when it isn't installed.
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from portfolio import fx, metrics, optimization, risk
from portfolio.config import load_settings
from portfolio.db import get_connection, load_close_prices
from portfolio.snapshot import sync_from_csv

st.set_page_config(page_title="Portfolio Risk Dashboard", page_icon="📈", layout="wide")

settings = load_settings()
CURRENCY_SIGNS = {"EUR": "€", "USD": "$", "GBP": "£"}
CURRENCY_NAMES = {"EUR": "euros", "USD": "dollars", "GBP": "pounds"}
RISK_FREE_SOURCES = {"EUR": "3-month Euribor", "USD": "3-month US Treasury yield"}

# Streamlit forgets the state of widgets that are not on screen. Re-saving these keys on
# every run keeps each market's choices (assets, weights, benchmark…) when switching markets.
for _key in list(st.session_state):
    if _key.startswith(("weight_", "assets_", "bench_", "in_base_", "rf_")):
        st.session_state[_key] = st.session_state[_key]
name = settings.label  # ticker -> name people recognise ("JMT.LS" -> "Jerónimo Martins")

ROLLING_WINDOW = 60  # trading days (~3 months)
MIN_DAYS = 60
PERIODS = {"1Y": 1, "3Y": 3, "5Y": 5, "Max": None}  # quick ranges, as in Apple's Stocks app

# --------------------------------------------------------------------------
# Design tokens — blue is always the portfolio, orange is always the index.
# Each colour has a light and a dark step with at least 3:1 contrast on its
# background (4.5:1 where it is used as text).
# --------------------------------------------------------------------------
TOKENS = {
    "light": {
        "portfolio": "#0A66C2",  # 5.7:1 on white
        "index": "#EB6834",      # 3.2:1 on white (lines only, never text)
        "ink": "#1D1D1F",
        "secondary": "#636366",  # 6.0:1 on white
        "grid": "#E5E5EA",
        "surface": "#FFFFFF",
        "negative": "#D70015",
        "neutral": "#F2F2F7",
        "cloud": "#C7C7CC",      # random portfolios (background texture, not data identity)
        # Glass (context bar only): translucent fill, hairline border, specular top edge
        "glass_fill": "rgba(255, 255, 255, 0.82)",
        "glass_border": "rgba(0, 0, 0, 0.08)",
        "glass_highlight": "rgba(255, 255, 255, 0.9)",
        "glass_shadow": "0 8px 28px rgba(0, 0, 0, 0.08)",
        "area": "rgba(10, 102, 194, 0.14)",
    },
    "dark": {
        "portfolio": "#4C9AF0",  # 5.8:1 on #1C1C1E
        "index": "#F07A45",      # 6.1:1 on #1C1C1E
        "ink": "#F5F5F7",
        "secondary": "#AEAEB2",  # 7.7:1 on #1C1C1E
        "grid": "#38383A",
        "surface": "#1C1C1E",
        "negative": "#FF6961",
        "neutral": "#3A3A3C",
        "cloud": "#48484A",
        "glass_fill": "rgba(44, 44, 46, 0.80)",
        "glass_border": "rgba(255, 255, 255, 0.10)",
        "glass_highlight": "rgba(255, 255, 255, 0.10)",
        "glass_shadow": "0 8px 28px rgba(0, 0, 0, 0.45)",
        "area": "rgba(76, 154, 240, 0.20)",
    },
}
MODE = "dark" if st.context.theme.type == "dark" else "light"
T = TOKENS[MODE]
CHART_CONFIG = {"displayModeBar": False}  # no floating toolbar over the legend
FONT = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif"

TABLE_FORMAT = {
    "Annual return": "{:.1%}",
    "Annual volatility": "{:.1%}",
    "Sharpe ratio": "{:.2f}",
    "Max drawdown": "{:.1%}",
}

# Dark mode: dark text on the blue asset chips (white would be 2.9:1, this is 6.0:1)
CHIP_CSS = (
    '[data-testid="stMultiSelectTagsContainer"] span { color: #0B1A2E !important; }' if MODE == "dark" else ""
)

st.html(
    f"""
    <style>
      [data-testid="stMetricValue"], [data-testid="stDataFrame"] {{ font-variant-numeric: tabular-nums; }}
      [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color: {T["secondary"]}; opacity: 1; }}
      [data-testid="stMainBlockContainer"] {{ padding-top: 1.5rem; }}
      /* Type scale: the verdict is the largest text on the page; the app name defers to it */
      [data-testid="stMarkdownContainer"] p.app-name {{ font-size: 0.9375rem; font-weight: 600; color: {T["secondary"]};
                  margin: 0 0 0.5rem 0.25rem; }}
      [data-testid="stMarkdownContainer"] p.verdict {{ font-size: 1.75rem; line-height: 1.35; font-weight: 400; color: {T["ink"]};
                  max-width: 46rem; margin: 1.5rem 0 1.25rem 0; letter-spacing: -0.01em; }}
      [data-testid="stMetricValue"] {{ font-size: 1.75rem; }}
      [data-testid="stMarkdownContainer"] p.bar-label {{ font-size: 0.8125rem; font-weight: 500; color: {T["ink"]};
                  margin: 0 0 0.25rem 0; }}
      [data-testid="stMarkdownContainer"] p.bar-value {{ font-size: 0.9375rem; color: {T["ink"]}; margin: 0.375rem 0 0.5rem 0; }}

      /* Liquid Glass, functional layer only: the floating context bar.
         Content (charts, tables, text) never gets glass. */
      /* Sticky on the wrapper Streamlit puts around the container, so the bar stays while content scrolls under it */
      [data-testid="stLayoutWrapper"]:has(> .st-key-context_bar) {{ position: sticky; top: 0.75rem; z-index: 990; }}
      /* Scroll edge: a short fade above the bar so content never peeks out between the bar and the window edge */
      [data-testid="stLayoutWrapper"]:has(> .st-key-context_bar)::before {{
          content: ""; position: absolute; left: -1rem; right: -1rem; top: -0.75rem; height: 1.5rem; z-index: -1;
          background: linear-gradient({T["surface"]} 55%, transparent); pointer-events: none;
      }}
      .st-key-context_bar {{
          padding: 0.875rem 1.25rem 0.5rem 1.25rem; border-radius: 1.25rem;
          background: {T["glass_fill"]};
          -webkit-backdrop-filter: blur(24px) saturate(1.4); backdrop-filter: blur(24px) saturate(1.4);
          border: 1px solid {T["glass_border"]};
          box-shadow: {T["glass_shadow"]}, inset 0 1px 0 {T["glass_highlight"]};
      }}
      /* Accessibility states: opaque surface, stronger edge */
      @media (prefers-reduced-transparency: reduce) {{
          .st-key-context_bar {{ background: {T["surface"]}; -webkit-backdrop-filter: none; backdrop-filter: none; }}
      }}
      @media (prefers-contrast: more) {{
          .st-key-context_bar {{ background: {T["surface"]}; -webkit-backdrop-filter: none; backdrop-filter: none;
                                 border: 1px solid {T["secondary"]}; }}
      }}
      /* On narrow screens the bar stacks into several rows: let it scroll away instead of covering the page */
      @media (max-width: 640px) {{
          [data-testid="stLayoutWrapper"]:has(> .st-key-context_bar) {{ position: static; }}
          [data-testid="stLayoutWrapper"]:has(> .st-key-context_bar)::before {{ display: none; }}
          [data-testid="stMainBlockContainer"] {{ padding-top: 3.75rem; }}
          [data-testid="stMarkdownContainer"] p.verdict {{ font-size: 1.375rem; }}
      }}
      [data-testid="stMarkdownContainer"] p.verdict strong {{ font-weight: 600; }}
      [data-testid="stMarkdownContainer"] p.chart-title {{ font-size: 1.0625rem; font-weight: 600; color: {T["ink"]}; margin: 1.25rem 0 0.125rem 0; }}
      {CHIP_CSS}
      [data-testid="stMarkdownContainer"] p.chart-summary {{ font-size: 0.9375rem; color: {T["secondary"]}; margin: 0 0 0.25rem 0; }}
    </style>
    """
)


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------
CSV_PATH = settings.database_path.with_suffix(".csv")


@st.cache_data(ttl=60 * 60)
def get_prices(symbols: tuple[str, ...], snapshot_version: float) -> tuple[pd.DataFrame, list[str]]:
    """Load every price, in its own currency, cached across reruns.

    `snapshot_version` is the CSV's modification time: when the daily Action
    commits new prices, it changes and the cache is rebuilt.
    Returns the prices and the list of symbols that have no data yet.
    """
    sync_from_csv(settings.database_path, CSV_PATH)
    conn = get_connection(settings.database_path)
    try:
        raw = load_close_prices(conn, list(symbols))
    finally:
        conn.close()
    return raw, [s for s in symbols if s not in raw.columns]


def market_prices(raw: pd.DataFrame, market, in_base_currency: bool) -> pd.DataFrame:
    """Prices of one market (tickers + benchmarks), optionally converted to the base currency."""
    symbols = market.tickers + market.benchmarks
    prices = raw[symbols]
    if in_base_currency and market.currency != settings.base_currency:
        fx_symbol = settings.fx_symbols[market.currency]
        # Yahoo's daily rate is taken at the start of the London day: shift it to the New York close
        rates = fx.to_new_york_close(raw[[fx_symbol]].rename(columns={fx_symbol: market.currency}))
        prices = fx.to_base_currency(prices, {s: market.currency for s in symbols}, rates)
    # Fills the odd day an index has no price (e.g. 12 days of the PSI since 2018).
    return metrics.align_calendars(prices)


raw_prices, missing_symbols = get_prices(
    tuple(settings.all_symbols), CSV_PATH.stat().st_mtime if CSV_PATH.exists() else 0.0
)
if missing_symbols:
    st.error(
        f"No prices yet for {', '.join(missing_symbols)}. "
        "Run `python scripts/update_data.py` and reload this page."
    )
    st.stop()
if raw_prices.empty:
    st.error("There is no price data yet. Run `python scripts/update_data.py` and reload this page.")
    st.stop()


# --------------------------------------------------------------------------
# Presentation helpers (no calculations)
# --------------------------------------------------------------------------
def fmt_date(d: date | pd.Timestamp) -> str:
    """'2 Jan 2018' — unambiguous and works on every OS."""
    return f"{d.day} {d:%b %Y}"


def equal_weights(n: int) -> list[int]:
    """Integer percentages that add up to exactly 100 (e.g. 6 assets -> 17,17,17,17,16,16)."""
    base, extra = divmod(100, n)
    return [base + 1 if i < extra else base for i in range(n)]


def reset_weights(tickers: list[str]) -> None:
    for t, w in zip(tickers, equal_weights(len(tickers))):
        st.session_state[f"weight_{t}"] = w


def pct(x: float, decimals: int = 1) -> str:
    """Percentage with a true minus sign (−40.2%), which reads better than a hyphen."""
    return f"{x:.{decimals}%}".replace("-", "\u2212")


def pp(diff: float) -> str:
    """Difference between two percentages, in percentage points."""
    return f"{diff * 100:+.1f} pp vs {name(BENCH)}"


def chart_header(title: str, summary: str) -> None:
    """Title plus a one-sentence summary of what the chart shows, using actual values."""
    st.markdown(f'<p class="chart-title">{title}</p><p class="chart-summary">{summary}</p>', unsafe_allow_html=True)


def line_chart(
    series: dict[str, pd.Series], percent: bool = False, area: bool = False, end_labels: str | None = None
) -> go.Figure:
    """Portfolio vs index. Colour AND line style tell them apart (index is dashed).

    area: fill the portfolio down to zero (used for drawdowns, the "underwater" view).
    end_labels: format for a direct label at the last value of each line, e.g. "€{:,.0f}".
    """
    styles = {
        "Portfolio": {"color": T["portfolio"], "width": 2.5},
        name(BENCH): {"color": T["index"], "width": 2, "dash": "dash"},
    }
    value_format = "%{y:.1%}" if percent else "%{y:.1f}"
    fig = go.Figure()
    for label, s in series.items():
        fill = {"fill": "tozeroy", "fillcolor": T["area"]} if area and label == "Portfolio" else {}
        fig.add_trace(
            go.Scatter(x=s.index, y=s.values, name=label, mode="lines",
                       line=styles[label], hovertemplate=value_format, **fill)
        )
    if end_labels:
        # Direct labels at the end of each line answer the chart's question without the legend
        ends = sorted(series.items(), key=lambda kv: kv[1].iloc[-1], reverse=True)
        for rank, (label, s) in enumerate(ends):
            fig.add_annotation(
                x=s.index[-1], y=s.iloc[-1], text=f"<b>{end_labels.format(s.iloc[-1])}</b> {label}",
                showarrow=False, xanchor="right", yanchor="bottom" if rank == 0 else "top",
                yshift=8 if rank == 0 else -8, font={"color": T["ink"], "size": 13},
                bgcolor=T["surface"], borderpad=2,
            )
    fig.update_layout(
        font={"family": FONT, "size": 13, "color": T["secondary"]},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        hoverlabel={"bgcolor": T["surface"], "bordercolor": T["grid"], "font": {"color": T["ink"], "family": FONT}},
        legend={"orientation": "h", "x": 0, "y": 1.1, "xanchor": "left", "font": {"color": T["ink"]}},
        margin={"t": 36, "b": 8, "l": 8, "r": 8},
        height=340,
    )
    fig.update_xaxes(showgrid=False, linecolor=T["grid"], ticks="", hoverformat="%-d %b %Y", automargin=True)
    # Y axis on the trailing side keeps a clean leading edge (HIG › Charts › Best practices)
    fig.update_yaxes(gridcolor=T["grid"], zeroline=False, side="right", automargin=True,
                     tickformat=".0%" if percent else None)
    return fig


def base_layout(fig: go.Figure, height: int = 340) -> go.Figure:
    """Shared look for charts that are not Portfolio-vs-index lines."""
    fig.update_layout(
        font={"family": FONT, "size": 13, "color": T["secondary"]},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel={"bgcolor": T["surface"], "bordercolor": T["grid"], "font": {"color": T["ink"], "family": FONT}},
        legend={"orientation": "h", "x": 0, "y": 1.1, "xanchor": "left", "font": {"color": T["ink"]}},
        margin={"t": 36, "b": 8, "l": 8, "r": 8},
        height=height,
    )
    fig.update_xaxes(showgrid=False, linecolor=T["grid"], ticks="", automargin=True, zeroline=False)
    fig.update_yaxes(gridcolor=T["grid"], zeroline=False, side="right", automargin=True)
    return fig


def to_percent_weights(w: np.ndarray) -> list[int]:
    """Round fractions to whole percentages that still add up to exactly 100 (largest remainder)."""
    raw = np.asarray(w, dtype=float) * 100
    whole = np.floor(raw).astype(int)
    for i in np.argsort(-(raw - whole))[: 100 - whole.sum()]:
        whole[i] += 1
    return whole.tolist()


def apply_weights(tickers: list[str], percents: list[int]) -> None:
    """Copy suggested weights into the sidebar sliders, so every tab updates."""
    for t, w in zip(tickers, percents):
        st.session_state[f"weight_{t}"] = int(w)


@st.cache_data(show_spinner="Optimising…")
def optimise(asset_returns: pd.DataFrame, risk_free_rate: float, periods: float) -> dict:
    """Run the optimiser once per (assets, period, risk-free rate); slider moves reuse the result."""
    mu, cov = optimization.estimate_inputs(asset_returns, periods)
    return {
        "mu": mu,
        "cov": cov,
        "min": optimization.min_variance_weights(cov),
        "max": optimization.max_sharpe_weights(mu, cov, risk_free_rate),
        "frontier": optimization.efficient_frontier(mu, cov),
        "cloud": optimization.random_portfolios(mu, cov, n_portfolios=3000, risk_free_rate=risk_free_rate),
    }


# --------------------------------------------------------------------------
# Header and context bar — what you are looking at (market, period, benchmark, currency)
# Layout: the sidebar builds the portfolio; the context bar chooses the view.
# --------------------------------------------------------------------------
st.markdown('<p class="app-name">Portfolio Risk Dashboard</p>', unsafe_allow_html=True)

with st.container(key="context_bar"):
    col_market, col_period, col_bench, col_currency = st.columns([1.35, 1.7, 1.05, 0.9], vertical_alignment="top")

    with col_market:
        st.markdown('<p class="bar-label">Market</p>', unsafe_allow_html=True)
        market_key = st.segmented_control(
            "Market", list(settings.markets), format_func=lambda k: settings.markets[k].name,
            default=list(settings.markets)[0], required=True, key="market", label_visibility="collapsed",
            width="stretch",
        )
    MARKET = settings.markets[market_key]

    with col_currency:
        st.markdown('<p class="bar-label">Currency</p>', unsafe_allow_html=True)
        in_base = False
        if MARKET.currency != settings.base_currency:
            st.session_state.setdefault(f"in_base_{market_key}", False)
            in_base = st.toggle(
                f"Show in {CURRENCY_NAMES.get(settings.base_currency, settings.base_currency)}",
                key=f"in_base_{market_key}",
                help=f"Converts prices with the daily {settings.base_currency}/{MARKET.currency} rate, "
                     "so returns and risk are those of an investor who holds euros.",
            )
        else:
            st.markdown(
                f'<p class="bar-value">{CURRENCY_NAMES.get(MARKET.currency, MARKET.currency).capitalize()}</p>',
                unsafe_allow_html=True,
            )
    CURRENCY = settings.base_currency if in_base else MARKET.currency
    CURRENCY_SIGN = CURRENCY_SIGNS.get(CURRENCY, CURRENCY + " ")

    all_prices = market_prices(raw_prices, MARKET, in_base)
    first_day = all_prices.index.min().date()
    last_day = all_prices.index.max().date()

    with col_bench:
        st.markdown('<p class="bar-label">Compare with</p>', unsafe_allow_html=True)
        if len(MARKET.benchmarks) > 1:
            st.session_state.setdefault(f"bench_{market_key}", MARKET.benchmarks[0])
            BENCH = st.selectbox(
                "Benchmark", MARKET.benchmarks, format_func=name, key=f"bench_{market_key}",
                label_visibility="collapsed",
            )
        else:
            BENCH = MARKET.benchmarks[0]
            st.markdown(f'<p class="bar-value">{name(BENCH)}</p>', unsafe_allow_html=True)

    with col_period:
        st.markdown('<p class="bar-label">Period</p>', unsafe_allow_html=True)
        choice = st.segmented_control(
            "Period", [*PERIODS, "Custom"], default="Max", required=True, key="period",
            label_visibility="collapsed", width="stretch",
        ) or "Max"
        if choice == "Custom":
            chosen = st.date_input(
                "Dates", value=(first_day, last_day), min_value=first_day, max_value=last_day,
                format="DD/MM/YYYY", label_visibility="collapsed",
            )
            if not isinstance(chosen, tuple) or len(chosen) != 2:
                st.info("Pick an end date to finish the range.")
                st.stop()
            start, end = chosen
        elif PERIODS[choice]:
            end = last_day
            start = max(first_day, (pd.Timestamp(last_day) - pd.DateOffset(years=PERIODS[choice])).date())
        else:
            start, end = first_day, last_day


# --------------------------------------------------------------------------
# Sidebar — build the portfolio
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("Portfolio")
    st.session_state.setdefault(f"assets_{market_key}", MARKET.tickers)
    n_chosen = len(st.session_state[f"assets_{market_key}"])
    # Progressive disclosure: the full list of chips only when people want to change it
    with st.expander(f"Assets · {n_chosen} of {len(MARKET.tickers)}"):
        selected = st.multiselect(
            "Assets", MARKET.tickers, format_func=name, key=f"assets_{market_key}", label_visibility="collapsed"
        )
    if not selected:
        st.warning("Choose at least one asset to build the portfolio.")
        st.stop()

    for t, w in zip(selected, equal_weights(len(selected))):
        st.session_state.setdefault(f"weight_{t}", w)

    st.markdown("**Weights**")
    raw_weights = {
        t: st.slider(name(t), 0, 100, step=1, format="%d%%", key=f"weight_{t}") for t in selected
    }
    total = sum(raw_weights.values())
    if total == 0:
        st.error("Set at least one weight above 0%.")
        st.stop()
    weights = {t: w / total for t, w in raw_weights.items()}

    note = f"Total {total}%"
    if total != 100:
        note += " · rescaled to 100% in the calculations"
    st.caption(note)
    st.button("Equal weights", on_click=reset_weights, args=(selected,))

    with st.expander("Assumptions"):
        st.session_state.setdefault(f"rf_{CURRENCY}", round(settings.risk_free_rate_for(CURRENCY) * 100, 2))
        risk_free = (
            st.number_input(
                f"Risk-free rate ({CURRENCY}, % a year)", step=0.25, format="%.2f", key=f"rf_{CURRENCY}"
            )
            / 100
        )
        source = RISK_FREE_SOURCES.get(CURRENCY)
        st.caption(
            (f"Default: {source}. " if source else "")
            + "Used in the Sharpe ratio. Weights are rebalanced every day."
        )

    fx_note = f" · converted from {MARKET.currency} at the daily rate" if in_base else ""
    st.caption(f"Prices up to {fmt_date(last_day)} · Yahoo Finance{fx_note}")


# --------------------------------------------------------------------------
# Calculations (all from src/portfolio/metrics.py)
# --------------------------------------------------------------------------
prices = all_prices.loc[pd.Timestamp(start) : pd.Timestamp(end), selected + [BENCH]]
if len(prices) < MIN_DAYS:
    st.warning(f"This period has {len(prices)} trading days. Choose one with at least {MIN_DAYS}.")
    st.stop()

PERIODS_PER_YEAR = metrics.periods_per_year(prices.index)  # observations per year in this data
returns = metrics.simple_returns(prices)
port_value = metrics.portfolio_value(prices[selected], weights)
port_returns = metrics.simple_returns(port_value)
bench_returns = returns[BENCH]
bench_value = metrics.rebase(prices[BENCH])

summary = metrics.summary_table(
    pd.concat([port_value, prices[[BENCH] + selected]], axis=1), risk_free, PERIODS_PER_YEAR
)
summary.index = [name(i) if i != "Portfolio" else i for i in summary.index]
p, b = summary.loc["Portfolio"], summary.loc[name(BENCH)]

port_dd = metrics.drawdown_series(port_value)
bench_dd = metrics.drawdown_series(prices[BENCH])
port_vol = metrics.rolling_volatility(port_returns, ROLLING_WINDOW, PERIODS_PER_YEAR).dropna()
bench_vol = metrics.rolling_volatility(bench_returns, ROLLING_WINDOW, PERIODS_PER_YEAR).dropna()


# --------------------------------------------------------------------------
# Main page
# --------------------------------------------------------------------------
diff = p["Annual return"] - b["Annual return"]
st.markdown(
    f'<p class="verdict">Since {fmt_date(start)}, this portfolio returned '
    f'<strong>{p["Annual return"]:.1%} a year</strong> in {CURRENCY_NAMES.get(CURRENCY, CURRENCY)}, '
    f'{abs(diff) * 100:.1f} percentage points '
    f'{"more" if diff >= 0 else "less"} than the {name(BENCH)}, with '
    f'<strong>{p["Annual volatility"]:.1%} volatility</strong> against {b["Annual volatility"]:.1%} '
    f"for the index.</p>",
    unsafe_allow_html=True,
)

# Scorecard: one quiet row, no boxes — the sentence above is the headline
c1, c2, c3, c4 = st.columns(4)
c1.metric("Annual return", f"{p['Annual return']:.1%}", pp(diff))
c2.metric(
    "Annual volatility",
    f"{p['Annual volatility']:.1%}",
    pp(p["Annual volatility"] - b["Annual volatility"]),
    delta_color="inverse",  # lower volatility is better
)
c3.metric(
    "Sharpe ratio",
    f"{p['Sharpe ratio']:.2f}",
    f"{p['Sharpe ratio'] - b['Sharpe ratio']:+.2f} vs {name(BENCH)}",
    help="Return above the risk-free rate for each unit of volatility. Higher is better.",
)
c4.metric(
    "Max drawdown",
    pct(p["Max drawdown"]),
    pp(p["Max drawdown"] - b["Max drawdown"]),
    help="Worst fall from a previous peak.",
)
st.caption(
    f"{len(selected)} assets · {len(prices):,} trading days to {fmt_date(end)} · "
    "Educational project, not investment advice"
)

tab_overview, tab_risk, tab_corr, tab_opt = st.tabs(["Overview", "Risk", "Correlation", "Optimisation"])

with tab_overview:
    chart_header(
        f"Growth of {CURRENCY_SIGN}100",
        f"{CURRENCY_SIGN}100 invested on {fmt_date(start)} was worth {CURRENCY_SIGN}{port_value.iloc[-1]:,.0f} "
        f"on {fmt_date(end)}, against {CURRENCY_SIGN}{bench_value.iloc[-1]:,.0f} in the {name(BENCH)}.",
    )
    st.plotly_chart(
        line_chart({"Portfolio": port_value, name(BENCH): bench_value}, end_labels=CURRENCY_SIGN + "{:,.0f}"),
        theme=None, config=CHART_CONFIG,
    )

    st.subheader("By asset")
    st.dataframe(
        summary.rename_axis("").reset_index().style.format(TABLE_FORMAT), hide_index=True,
        column_config={"": st.column_config.TextColumn(width="medium")},
    )
    st.caption("Annualised over the selected period. Max drawdown is the worst fall from a previous peak.")

with tab_risk:
    c1, c2, c3 = st.columns(3)
    c1.metric(
        f"Beta vs {name(BENCH)}",
        f"{metrics.beta(port_returns, bench_returns):.2f}",
        help="How much the portfolio moves when the index moves 1%. Above 1 means it amplifies the index.",
    )
    c2.metric("Worst drawdown", pct(port_dd.min()), f"on {fmt_date(port_dd.idxmin())}",
              delta_color="off", delta_arrow="off")
    c3.metric(f"Highest {ROLLING_WINDOW}-day volatility", pct(port_vol.max(), 0),
              f"on {fmt_date(port_vol.idxmax())}", delta_color="off", delta_arrow="off")

    chart_header(
        "Drawdown",
        f"Distance from the previous peak. The portfolio's deepest fall was {pct(port_dd.min())} on "
        f"{fmt_date(port_dd.idxmin())}; the {name(BENCH)}'s was {pct(bench_dd.min())} on {fmt_date(bench_dd.idxmin())}.",
    )
    st.plotly_chart(
        line_chart({"Portfolio": port_dd, name(BENCH): bench_dd}, percent=True, area=True),
        theme=None, config=CHART_CONFIG,
    )

    chart_header(
        f"Volatility over the last {ROLLING_WINDOW} trading days",
        f"Annualised. The portfolio peaked at {port_vol.max():.0%} on {fmt_date(port_vol.idxmax())} "
        f"and is at {port_vol.iloc[-1]:.0%} now.",
    )
    st.plotly_chart(line_chart({"Portfolio": port_vol, name(BENCH): bench_vol}, percent=True), theme=None, config=CHART_CONFIG)

    # ---- Value at Risk -----------------------------------------------------
    st.subheader("Value at risk")
    level_label = st.segmented_control(
        "Confidence level", ["95%", "99%"], default="95%", required=True, key="var_level"
    )
    level = 0.99 if level_label == "99%" else 0.95
    tail = round((1 - level) * 100)
    var_hist = risk.historical_var(port_returns, level)
    cvar_hist = risk.historical_cvar(port_returns, level)
    var_norm = risk.parametric_var(port_returns, level)

    c1, c2, c3 = st.columns(3)
    c1.metric("Daily VaR (historical)", pct(var_hist),
              help=f"On {level:.0%} of days, the daily loss was smaller than this.")
    c2.metric("Daily CVaR (historical)", pct(cvar_hist),
              help=f"Average loss on the worst {tail}% of days.")
    c3.metric("Daily VaR (normal model)", pct(var_norm),
              help="What a normal distribution with the same mean and volatility would predict.")

    if var_norm < var_hist:
        model_note = (f"A normal distribution would put the threshold at {pct(var_norm)}, "
                      "so it underestimates how bad the worst days really are (fat tails).")
    else:
        model_note = (f"A normal distribution would put the threshold at {pct(var_norm)}, "
                      "slightly more cautious than history at this level.")
    chart_header(
        "Daily returns",
        f"On {level:.0%} of days the portfolio lost less than {pct(var_hist)}. On the worst {tail}% of days "
        f"it lost {pct(cvar_hist)} on average. {model_note}",
    )
    lo, hi = port_returns.quantile(0.001), port_returns.quantile(0.999)
    fig = go.Figure(
        go.Histogram(
            x=port_returns,
            xbins={"size": (hi - lo) / 100},
            marker={"color": T["portfolio"], "line": {"color": T["surface"], "width": 1}},
            hovertemplate="%{x}<br>%{y} days<extra></extra>",
            name="Daily returns",
        )
    )
    hist_left = var_hist > var_norm  # the larger loss sits further left; its label goes on the left
    fig.add_vline(x=-var_hist, line={"color": T["ink"], "width": 2},
                  annotation_text=f"Historical {pct(-var_hist)}",
                  annotation_position="top left" if hist_left else "top right",
                  annotation_font_color=T["ink"])
    fig.add_vline(x=-var_norm, line={"color": T["ink"], "width": 2, "dash": "dash"},
                  annotation_text=f"Normal {pct(-var_norm)}",
                  annotation_position="top right" if hist_left else "top left",
                  annotation_font_color=T["ink"])
    base_layout(fig)
    fig.update_layout(showlegend=False, bargap=0)
    fig.update_xaxes(range=[lo, hi], tickformat=".0%")
    fig.update_yaxes(title_text="Days")
    st.plotly_chart(fig, theme=None, config=CHART_CONFIG)
    st.caption("The axis leaves out the 0.1% most extreme days on each side so the shape stays readable.")

with tab_corr:
    corr = metrics.correlation_matrix(returns)
    corr.index = corr.columns = [name(c) for c in corr.columns]

    # Show each pair once: keep the lower triangle, hide the diagonal of 1.00s.
    lower = corr.where(pd.DataFrame(
        [[i > j for j in range(len(corr))] for i in range(len(corr))], index=corr.index, columns=corr.columns
    ))
    pairs = lower.drop(index=name(BENCH), columns=name(BENCH), errors="ignore").stack()

    if len(pairs):
        lo, hi = pairs.idxmin(), pairs.idxmax()
        summary_text = (
            f"Lowest pair: {lo[0]} and {lo[1]} ({pairs.min():.2f}). "
            f"Highest pair: {hi[0]} and {hi[1]} ({pairs.max():.2f}). "
            "Lower values mean the assets diversify each other more."
        )
    else:
        summary_text = "Add a second asset to compare correlations."
    chart_header("Correlation of daily returns", summary_text)

    fig = px.imshow(
        lower.iloc[1:, :-1],
        text_auto=".2f",
        zmin=-1,
        zmax=1,
        color_continuous_scale=[[0.0, T["negative"]], [0.5, T["neutral"]], [1.0, T["portfolio"]]],
        aspect="auto",
        labels={"x": "", "y": "", "color": "Correlation"},
    )
    fig.update_traces(hovertemplate="%{y} and %{x}: %{z:.2f}<extra></extra>")
    fig.update_layout(
        font={"family": FONT, "size": 13, "color": T["secondary"]},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"t": 16, "b": 8, "l": 8, "r": 8},
        height=440,
        coloraxis_colorbar={"thickness": 12, "tickvals": [-1, 0, 1], "ticktext": ["−1 opposite", "0 unrelated", "1 together"]},
    )
    fig.update_xaxes(showgrid=False, side="bottom", automargin=True)
    fig.update_yaxes(showgrid=False, automargin=True)
    st.plotly_chart(fig, theme=None, config=CHART_CONFIG)

with tab_opt:
    if len(selected) < 2:
        st.info("Choose at least two assets in the sidebar to compare different weightings.")
        st.stop()

    opt = optimise(returns[selected], risk_free, PERIODS_PER_YEAR)
    mu, cov = opt["mu"], opt["cov"]
    labels = [name(t) for t in selected]
    current = np.array([weights[t] for t in selected])
    mixes = {"Your portfolio": current, "Lowest volatility": opt["min"], "Highest Sharpe": opt["max"]}
    perf = {k: optimization.portfolio_performance(w, mu, cov) for k, w in mixes.items()}
    sharpe = {k: (r - risk_free) / v for k, (r, v) in perf.items()}
    (r_you, v_you), (r_min, v_min), (r_max, v_max) = perf.values()

    chart_header(
        "Risk and expected return",
        f"Over this period, the highest-Sharpe mix earned {pct(r_max)} a year for {pct(v_max)} volatility, "
        f"against {pct(r_you)} for {pct(v_you)} in your portfolio. "
        f"The lowest-volatility mix brings risk down to {pct(v_min)}.",
    )

    mu_idx, cov_idx = optimization.estimate_inputs(returns[[BENCH]], PERIODS_PER_YEAR)
    cloud, frontier = opt["cloud"], opt["frontier"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=cloud["volatility"], y=cloud["return"], mode="markers", name="Random mixes",
        marker={"color": T["cloud"], "size": 4, "opacity": 0.45}, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=frontier["volatility"], y=frontier["return"], mode="lines", name="Efficient frontier",
        line={"color": T["ink"], "width": 2}, hovertemplate="Volatility %{x:.1%}<br>Return %{y:.1%}<extra>Frontier</extra>",
    ))
    label_assets = len(labels) <= 6  # more names than that collide; hover still shows each one
    fig.add_trace(go.Scatter(
        x=np.sqrt(np.diag(cov)), y=mu, mode="markers+text" if label_assets else "markers",
        name="Single assets", text=labels,
        textposition="top center", textfont={"color": T["secondary"]},
        marker={"color": "rgba(0,0,0,0)", "size": 9, "line": {"color": T["secondary"], "width": 2}},
        hovertemplate="%{text}<br>Volatility %{x:.1%}<br>Return %{y:.1%}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[np.sqrt(cov_idx[0, 0])], y=[mu_idx[0]], mode="markers+text", name=name(BENCH), text=[name(BENCH)],
        textposition="bottom center", textfont={"color": T["ink"]},
        marker={"color": T["index"], "size": 13, "symbol": "diamond", "line": {"color": T["surface"], "width": 2}},
        hovertemplate=name(BENCH) + "<br>Volatility %{x:.1%}<br>Return %{y:.1%}<extra></extra>",
    ))
    highlights = [
        ("Lowest volatility", "square", T["ink"], (-50, 0)),
        ("Highest Sharpe", "star", T["ink"], (-50, -30)),
        ("Your portfolio", "circle", T["portfolio"], (-60, -50)),
    ]
    # If the sliders already hold a suggested mix, label that point once
    same_as = [k for k in ("Lowest volatility", "Highest Sharpe") if np.allclose(current, mixes[k], atol=0.01)]
    for label, symbol, color, (ax, ay) in highlights:
        r, v = perf[label]
        text = label
        if label in same_as:
            text = None
        elif label == "Your portfolio" and same_as:
            text = {"Highest Sharpe": "Your portfolio (highest-Sharpe mix)",
                    "Lowest volatility": "Your portfolio (lowest-volatility mix)"}[same_as[0]]
        fig.add_trace(go.Scatter(
            x=[v], y=[r], mode="markers", name=label,
            marker={"color": color, "size": 15 if symbol == "circle" else 14, "symbol": symbol,
                    "line": {"color": T["surface"], "width": 2}},
            hovertemplate=label + "<br>Volatility %{x:.1%}<br>Return %{y:.1%}<extra></extra>",
        ))
        # Label in the empty area to the upper left of the frontier, with a thin leader line
        if text:
            fig.add_annotation(x=v, y=r, text=text, ax=ax, ay=ay, showarrow=True, arrowhead=0, arrowwidth=1,
                               arrowcolor=T["secondary"], font={"color": T["ink"]}, bgcolor=T["surface"],
                               borderpad=2, standoff=8)
    all_vols = np.concatenate([np.sqrt(np.diag(cov)), [np.sqrt(cov_idx[0, 0])], cloud["volatility"]])
    base_layout(fig, height=480)
    # Volatility starts at 0: an honest baseline, and room on the left for the labels
    fig.update_xaxes(title_text="Volatility (a year)", tickformat=".0%", range=[0, all_vols.max() * 1.05])
    fig.update_yaxes(title_text="Expected return (a year)", tickformat=".0%")
    st.plotly_chart(fig, theme=None, config=CHART_CONFIG)
    st.caption(
        "Expected return is the average daily return × days per year, so it is a little higher than the compound "
        "annual return on the Overview. Every grey dot is a random long-only mix of the selected assets."
        + ("" if label_assets else " Point at a circle to see which asset it is.")
    )

    st.subheader("Suggested weights")
    weights_table = pd.DataFrame({k: to_percent_weights(w) for k, w in mixes.items()}, index=labels)
    st.dataframe(
        weights_table.rename_axis("").reset_index().style.format("{:d}%", subset=list(mixes)), hide_index=True,
        column_config={"": st.column_config.TextColumn(width="medium")},
    )

    stats = pd.DataFrame(
        {k: {"Expected return": r, "Volatility": v, "Sharpe ratio": sharpe[k]} for k, (r, v) in perf.items()}
    )
    st.dataframe(
        stats.rename_axis("").reset_index().style
        .format("{:.1%}", subset=pd.IndexSlice[[0, 1], list(mixes)])
        .format("{:.2f}", subset=pd.IndexSlice[[2], list(mixes)]),
        hide_index=True,
        column_config={"": st.column_config.TextColumn(width="medium")},
    )

    b1, b2 = st.columns(2)
    b1.button("Use lowest-volatility weights", on_click=apply_weights,
              args=(selected, to_percent_weights(opt["min"])), width="stretch")
    b2.button("Use highest-Sharpe weights", on_click=apply_weights,
              args=(selected, to_percent_weights(opt["max"])), width="stretch")
    st.caption("Copies the weights to the sliders, so every tab updates. Equal weights in the sidebar takes you back.")

    # ---- Out-of-sample check -----------------------------------------------
    cutoff = prices.index[-1] - pd.DateOffset(years=1)
    train = returns.loc[:cutoff, selected]
    if len(train) < 2 * PERIODS_PER_YEAR:
        st.info("Choose a period of at least 3 years to test whether the suggested weights would have worked.")
    else:
        mu_t, cov_t = optimization.estimate_inputs(train, PERIODS_PER_YEAR)
        w_fit = optimization.max_sharpe_weights(mu_t, cov_t, risk_free)
        test = prices.loc[cutoff:]
        result = {
            "Highest Sharpe, fitted before": metrics.portfolio_value(test[selected], dict(zip(selected, w_fit))),
            "Your portfolio": metrics.portfolio_value(test[selected], weights),
            name(BENCH): metrics.rebase(test[BENCH]),
        }
        growth = {k: v.iloc[-1] / 100 - 1 for k, v in result.items()}
        g_fit, g_you, g_idx = growth.values()
        chart_header(
            "Would it have worked?",
            f"The highest-Sharpe weights were fitted with data up to {fmt_date(test.index[0])} and then held "
            f"for the next 12 months. They returned {pct(g_fit)}, against {pct(g_you)} for your portfolio "
            f"and {pct(g_idx)} for the {name(BENCH)}. Weights that were best in the past are not a forecast.",
        )
        c1, c2, c3 = st.columns(3)
        for col, (label, g) in zip((c1, c2, c3), growth.items()):
            col.metric(label, pct(g))
        fitted = ", ".join(f"{lab} {w}%" for lab, w in zip(labels, to_percent_weights(w_fit)) if w > 0)
        st.caption(f"Fitted weights: {fitted}. Last 12 months of the selected period.")
