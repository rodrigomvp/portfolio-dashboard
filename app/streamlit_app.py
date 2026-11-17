"""Portfolio Risk Dashboard — Streamlit app.

Run with:  streamlit run app/streamlit_app.py

Rule: this file only handles inputs, layout and charts. Every number shown
here comes from a tested function in src/portfolio/.

Design: the screen answers one question — is this portfolio worth the risk
it takes compared with the PSI index? The answer is written as a plain
sentence at the top of the Overview; everything else supports it.
Theme colours live in .streamlit/config.toml; chart colours are below.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from portfolio import metrics
from portfolio.config import load_settings
from portfolio.db import get_connection, load_close_prices

st.set_page_config(page_title="Portfolio Risk Dashboard", page_icon="📈", layout="wide")

settings = load_settings()
BENCH = settings.benchmark
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
    },
}
MODE = "dark" if st.context.theme.type == "dark" else "light"
T = TOKENS[MODE]
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
      [data-testid="stMainBlockContainer"] {{ padding-top: 2.5rem; }}
      [data-testid="stMarkdownContainer"] p.verdict {{ font-size: 1.5rem; line-height: 1.4; font-weight: 400; color: {T["ink"]};
                  max-width: 44rem; margin: 0.25rem 0 1.5rem 0; }}
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
@st.cache_data(ttl=60 * 60)
def get_prices(symbols: tuple[str, ...]) -> pd.DataFrame:
    """Load closing prices once per hour (cached across reruns)."""
    conn = get_connection(settings.database_path)
    try:
        prices = load_close_prices(conn, list(symbols))
    finally:
        conn.close()
    # Phase 1 decision: keep only dates where every series has a price.
    return prices.dropna()


all_prices = get_prices(tuple(settings.all_symbols))
if all_prices.empty:
    st.error("There is no price data yet. Run `python scripts/update_data.py` and reload this page.")
    st.stop()

first_day = all_prices.index.min().date()
last_day = all_prices.index.max().date()


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


def line_chart(series: dict[str, pd.Series], percent: bool = False) -> go.Figure:
    """Portfolio vs index. Colour AND line style tell them apart (index is dashed)."""
    styles = {
        "Portfolio": {"color": T["portfolio"], "width": 2.5},
        name(BENCH): {"color": T["index"], "width": 2, "dash": "dash"},
    }
    value_format = "%{y:.1%}" if percent else "%{y:.1f}"
    fig = go.Figure()
    for label, s in series.items():
        fig.add_trace(
            go.Scatter(x=s.index, y=s.values, name=label, mode="lines",
                       line=styles[label], hovertemplate=value_format)
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


# --------------------------------------------------------------------------
# Sidebar — inputs
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("Portfolio")
    selected = st.multiselect("Assets", settings.tickers, default=settings.tickers, format_func=name)
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

    st.header("Period")
    custom = st.session_state.get("custom_dates", False)
    choice = st.segmented_control(
        "Period", list(PERIODS), default="Max", required=True, key="period", label_visibility="collapsed",
        width="stretch", disabled=custom,
    ) or "Max"
    st.toggle("Custom dates", key="custom_dates")
    if custom:
        chosen = st.date_input(
            "Dates", value=(first_day, last_day), min_value=first_day, max_value=last_day, format="DD/MM/YYYY"
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

    with st.expander("Assumptions"):
        risk_free = (
            st.number_input(
                "Risk-free rate (% a year)", value=settings.risk_free_rate * 100, step=0.25, format="%.2f"
            )
            / 100
        )
        st.caption("Used in the Sharpe ratio. Weights are rebalanced every day.")

    st.caption(f"Prices up to {fmt_date(last_day)} · Yahoo Finance")


# --------------------------------------------------------------------------
# Calculations (all from src/portfolio/metrics.py)
# --------------------------------------------------------------------------
prices = all_prices.loc[pd.Timestamp(start) : pd.Timestamp(end), selected + [BENCH]]
if len(prices) < MIN_DAYS:
    st.warning(f"This period has {len(prices)} trading days. Choose one with at least {MIN_DAYS}.")
    st.stop()

returns = metrics.simple_returns(prices)
port_value = metrics.portfolio_value(prices[selected], weights)
port_returns = metrics.simple_returns(port_value)
bench_returns = returns[BENCH]
bench_value = metrics.rebase(prices[BENCH])

summary = metrics.summary_table(pd.concat([port_value, prices[[BENCH] + selected]], axis=1), risk_free)
summary.index = [name(i) if i != "Portfolio" else i for i in summary.index]
p, b = summary.loc["Portfolio"], summary.loc[name(BENCH)]

port_dd = metrics.drawdown_series(port_value)
bench_dd = metrics.drawdown_series(prices[BENCH])
port_vol = metrics.rolling_volatility(port_returns, ROLLING_WINDOW).dropna()
bench_vol = metrics.rolling_volatility(bench_returns, ROLLING_WINDOW).dropna()


# --------------------------------------------------------------------------
# Main page
# --------------------------------------------------------------------------
st.title("Portfolio Risk Dashboard")
st.caption(
    f"{len(selected)} assets against the {name(BENCH)} index · {fmt_date(start)} to {fmt_date(end)} · "
    f"{len(prices):,} trading days · Educational project, not investment advice"
)

tab_overview, tab_risk, tab_corr = st.tabs(["Overview", "Risk", "Correlation"])

with tab_overview:
    diff = p["Annual return"] - b["Annual return"]
    st.markdown(
        f'<p class="verdict">Since {fmt_date(start)}, this portfolio returned '
        f'<strong>{p["Annual return"]:.1%} a year</strong>, {abs(diff) * 100:.1f} percentage points '
        f'{"more" if diff >= 0 else "less"} than the {name(BENCH)}, with '
        f'<strong>{p["Annual volatility"]:.1%} volatility</strong> against {b["Annual volatility"]:.1%} '
        f"for the index.</p>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Annual return", f"{p['Annual return']:.1%}", pp(diff), border=True)
    c2.metric(
        "Annual volatility",
        f"{p['Annual volatility']:.1%}",
        pp(p["Annual volatility"] - b["Annual volatility"]),
        delta_color="inverse",  # lower volatility is better
        border=True,
    )
    c3.metric(
        "Sharpe ratio",
        f"{p['Sharpe ratio']:.2f}",
        f"{p['Sharpe ratio'] - b['Sharpe ratio']:+.2f} vs {name(BENCH)}",
        border=True,
        help="Return above the risk-free rate for each unit of volatility. Higher is better.",
    )
    c4.metric(
        "Max drawdown",
        pct(p["Max drawdown"]),
        pp(p["Max drawdown"] - b["Max drawdown"]),
        border=True,
        help="Worst fall from a previous peak.",
    )

    chart_header(
        "Growth of €100",
        f"€100 invested on {fmt_date(start)} was worth €{port_value.iloc[-1]:,.0f} on {fmt_date(end)}, "
        f"against €{bench_value.iloc[-1]:,.0f} in the {name(BENCH)}.",
    )
    st.plotly_chart(line_chart({"Portfolio": port_value, name(BENCH): bench_value}), theme=None)

    st.subheader("By asset")
    st.dataframe(summary.style.format(TABLE_FORMAT))
    st.caption("Annualised over the selected period. Max drawdown is the worst fall from a previous peak.")

with tab_risk:
    c1, c2, c3 = st.columns(3)
    c1.metric(
        f"Beta vs {name(BENCH)}",
        f"{metrics.beta(port_returns, bench_returns):.2f}",
        border=True,
        height="stretch",
        help="How much the portfolio moves when the index moves 1%. Above 1 means it amplifies the index.",
    )
    c2.metric("Worst drawdown", pct(port_dd.min()), f"on {fmt_date(port_dd.idxmin())}",
              delta_color="off", delta_arrow="off", border=True, height="stretch")
    c3.metric(f"Highest {ROLLING_WINDOW}-day volatility", pct(port_vol.max(), 0),
              f"on {fmt_date(port_vol.idxmax())}", delta_color="off", delta_arrow="off", border=True,
              height="stretch")

    chart_header(
        "Drawdown",
        f"Distance from the previous peak. The portfolio's deepest fall was {pct(port_dd.min())} on "
        f"{fmt_date(port_dd.idxmin())}; the {name(BENCH)}'s was {pct(bench_dd.min())} on {fmt_date(bench_dd.idxmin())}.",
    )
    st.plotly_chart(line_chart({"Portfolio": port_dd, name(BENCH): bench_dd}, percent=True), theme=None)

    chart_header(
        f"Volatility over the last {ROLLING_WINDOW} trading days",
        f"Annualised. The portfolio peaked at {port_vol.max():.0%} on {fmt_date(port_vol.idxmax())} "
        f"and is at {port_vol.iloc[-1]:.0%} now.",
    )
    st.plotly_chart(line_chart({"Portfolio": port_vol, name(BENCH): bench_vol}, percent=True), theme=None)

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
    st.plotly_chart(fig, theme=None)
