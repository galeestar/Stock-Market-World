import os
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# ==============================================================================
# PAGE CONFIG & INSTITUTIONAL TERMINAL STYLING
# ==============================================================================
st.set_page_config(
    page_title="Atlas Sovereign Terminal",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #131822, #19202e);
        border: 1px solid #283347;
        padding: 14px 18px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }
    .status-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background-color: #162436;
        border: 1px solid #2b4466;
        color: #38bdf8;
        margin-right: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# CACHED DATA & QUANTITATIVE ENGINES (ZERO BRACKET INDEXING)
# ==============================================================================
@st.cache_data(ttl=300)
def get_live_history(symbol: str, period: str = "6mo") -> pd.DataFrame:
    try:
        return yf.Ticker(symbol).history(period=period)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_multi_close(symbols: tuple, period: str = "1y") -> pd.DataFrame:
    try:
        raw = yf.download(list(symbols), period=period, progress=False)
        if raw.empty:
            return pd.DataFrame()
        if "Close" in raw:
            close_df = raw["Close"]
            if isinstance(close_df, pd.Series):
                return close_df.to_frame(name=symbols)
            return close_df.dropna(how="all")
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_ticker_news(symbol: str) -> list:
    try:
        news = yf.Ticker(symbol).news
        return news[:6] if news else []
    except Exception:
        return []


@st.cache_data(ttl=1800)
def get_usd_ngn_rate() -> float:
    try:
        fx = yf.Ticker("NGN=X").history(period="5d")
        if not fx.empty:
            return float(fx["Close"].tail(1).item())
    except Exception:
        pass
    return 1550.0


def compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(series: pd.Series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


# ==============================================================================
# SIDEBAR: SOVEREIGN MACRO TELEMETRY & LIVE FX CONVERTER
# ==============================================================================
with st.sidebar:
    st.title("🏛️ Atlas Sovereign")
    st.caption("Global & Nigerian Market Intelligence")

    fx_rate = get_usd_ngn_rate()
    st.metric("USD / NGN Live Reference", f"₦{fx_rate:,.2f}")

    with st.expander("💱 Instant USD ↔ NGN Converter", expanded=False):
        conv_dir = st.radio("Direction", ["USD ($) → NGN (₦)", "NGN (₦) → USD ($)"], horizontal=True)
        conv_amt = st.number_input("Amount", min_value=1.0, value=100.0, step=10.0)
        if conv_dir == "USD ($) → NGN (₦)":
            st.success(f"**₦{conv_amt * fx_rate:,.2f}**")
        else:
            st.success(f"**${conv_amt / fx_rate:,.2f}**")

    st.divider()
    st.subheader("📡 Global Macro Tape")
    macro_assets = {
        "S&P 500": "^GSPC",
        "NASDAQ 100": "^IXIC",
        "Bitcoin": "BTC-USD",
        "Gold": "GC=F",
        "Brent Crude": "BZ=F",
    }
    for label, sym in macro_assets.items():
        m_hist = get_live_history(sym, "5d")
        if len(m_hist) >= 2:
            curr = float(m_hist["Close"].tail(1).item())
            prev = float(m_hist["Close"].tail(2).head(1).item())
            chg = ((curr - prev) / prev) * 100 if prev else 0.0
            st.metric(label, f"{curr:,.2f}", f"{chg:+.2f}%")

    st.divider()
    if st.button("🔄 Sync Live Market Feeds", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ==============================================================================
# TOP COMMAND HEADER & SESSION CLOCK
# ==============================================================================
now_utc = datetime.now(timezone.utc)
utc_hour = now_utc.hour
us_open = (now_utc.weekday() < 5) and (14 <= utc_hour < 21)
ngx_open = (now_utc.weekday() < 5) and (9 <= utc_hour < 14)

st.title("🏛️ Atlas Sovereign Market Terminal")
st.markdown(
    f"""
    <span class="status-pill">🕒 UTC: {now_utc.strftime('%H:%M')}</span>
    <span class="status-pill">🇺🇸 US Markets: {'🟢 OPEN' if us_open else '🔴 CLOSED'}</span>
    <span class="status-pill">🇳🇬 NGX Session: {'🟢 OPEN' if ngx_open else '🔴 CLOSED'}</span>
    """,
    unsafe_allow_html=True,
)
st.write("")

# ==============================================================================
# 5-TAB INSTITUTIONAL WORKSPACE
# ==============================================================================
tab_chart, tab_quant, tab_battle, tab_wealth, tab_github = st.tabs(
    [
        "📊 Quant Charting & Intel",
        "🧠 Portfolio & Risk Lab",
        "⚔️ Multi-Asset Battleground",
        "💰 Dual-Currency Wealth Engine",
        "🤖 GitHub Auto-Tracker",
    ]
)

# ------------------------------------------------------------------------------
# TAB 1: QUANTITATIVE TECHNICAL CHARTING & LIVE INTELLIGENCE
# ------------------------------------------------------------------------------
with tab_chart:
    presets = {
        "NVIDIA (NVDA)": "NVDA",
        "Apple (AAPL)": "AAPL",
        "Microsoft (MSFT)": "MSFT",
        "S&P 500 Index (^GSPC)": "^GSPC",
        "NASDAQ Composite (^IXIC)": "^IXIC",
        "Bitcoin (BTC-USD)": "BTC-USD",
        "Ethereum (ETH-USD)": "ETH-USD",
        "Gold Futures (GC=F)": "GC=F",
        "Brent Crude Oil (BZ=F)": "BZ=F",
        "Custom Ticker...": "",
    }

    c1, c2, c3 = st.columns(3)
    with c1:
        choice = st.selectbox("Asset Preset", list(presets.keys()), index=0)
    with c2:
        default_sym = presets[choice] if presets[choice] else "TSLA"
        symbol = st.text_input("Ticker Symbol", value=default_sym).upper().strip()
    with c3:
        period = st.selectbox("Lookback Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3)

    ind1, ind2, ind3, ind4 = st.columns(4)
    with ind1:
        show_sma = st.checkbox("20 & 50 SMAs", value=True)
    with ind2:
        show_bb = st.checkbox("Bollinger Bands (20, 2)", value=True)
    with ind3:
        show_rsi = st.checkbox("RSI (14) Momentum", value=True)
    with ind4:
        show_macd = st.checkbox("MACD Oscillator", value=False)

    if symbol:
        hist = get_live_history(symbol, period)
        if not hist.empty and len(hist) >= 2:
            latest_c = float(hist["Close"].tail(1).item())
            prev_c = float(hist["Close"].tail(2).head(1).item())
            first_c = float(hist["Close"].head(1).item())
            day_chg = ((latest_c - prev_c) / prev_c) * 100
            period_chg = ((latest_c - first_c) / first_c) * 100
            period_high = float(hist["High"].max())
            period_low = float(hist["Low"].min())

            k1, k2, k3, k4 = st.columns(4)
            k1.metric(f"{symbol} Last Price", f"${latest_c:,.2f}", f"{day_chg:+.2f}% (1D)")
            k2.metric(f"{period.upper()} Return", f"{period_chg:+.2f}%", f"From ${first_c:,.2f}")
            k3.metric(f"{period.upper()} Range High", f"${period_high:,.2f}")
            k4.metric(f"{period.upper()} Range Low", f"${period_low:,.2f}")

            # Dynamic Subplot Builder
            panel_count = 1 + int(show_rsi) + int(show_macd)
            if panel_count == 1:
                heights = [1.0]
            elif panel_count == 2:
                heights = [0.72, 0.28]
            else:
                heights = [0.56, 0.22, 0.22]

            fig = make_subplots(
                rows=panel_count,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.04,
                row_heights=heights,
            )

            fig.add_trace(
                go.Candlestick(
                    x=hist.index,
                    open=hist["Open"],
                    high=hist["High"],
                    low=hist["Low"],
                    close=hist["Close"],
                    name="Price",
                ),
                row=1,
                col=1,
            )

            sma20 = hist["Close"].rolling(20).mean()
            std20 = hist["Close"].rolling(20).std()

            if show_sma:
                fig.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=sma20,
                        line=dict(color="#00E676", width=1.5),
                        name="SMA 20",
                    ),
                    row=1,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=hist["Close"].rolling(50).mean(),
