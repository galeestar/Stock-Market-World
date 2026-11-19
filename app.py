import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Atlas Market Terminal",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CUSTOM TERMINAL STYLING ---
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    div[data-testid="stMetric"] {
        background-color: #151A24;
        border: 1px solid #263042;
        padding: 14px 18px;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- CACHED DATA ENGINES ---
@st.cache_data(ttl=300)
def get_live_history(symbol: str, period: str = "6mo"):
    try:
        return yf.Ticker(symbol).history(period=period)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_multi_close(symbols: tuple, period: str = "1y"):
    try:
        raw = yf.download(list(symbols), period=period, progress=False)
        if raw.empty:
            return pd.DataFrame()
        if "Close" in raw:
            close_df = raw["Close"]
            if isinstance(close_df, pd.Series):
                return close_df.to_frame(name=symbols[0])
            return close_df.dropna(how="all")
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_ticker_news(symbol: str):
    try:
        news = yf.Ticker(symbol).news
        return news[:6] if news else []
    except Exception:
        return []


@st.cache_data(ttl=3600)
def get_usd_ngn_rate():
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
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


# --- SIDEBAR: GLOBAL TELEMETRY & NAVIGATION ---
with st.sidebar:
    st.title("🌐 Atlas Terminal")
    st.caption("Real-Time Global & Local Market Intelligence")

    fx_rate = get_usd_ngn_rate()
    st.metric("USD / NGN Reference Rate", f"₦{fx_rate:,.2f}")

    st.divider()
    st.subheader("⚡ Quick Watchlist Pulse")
    pulse_tickers = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "Bitcoin": "BTC-USD",
        "Gold": "GC=F",
    }
    for label, sym in pulse_tickers.items():
        p_hist = get_live_history(sym, "5d")
        if len(p_hist) >= 2:
            curr = float(p_hist["Close"].tail(1).item())
            prev = float(p_hist["Close"].tail(2).head(1).item())
            chg = ((curr - prev) / prev) * 100 if prev else 0.0
            st.metric(label, f"{curr:,.2f}", f"{chg:+.2f}%")

    st.divider()
    if st.button("🔄 Refresh Live Market Feed", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- MAIN HEADER ---
st.title("🌐 Atlas Global Market Terminal")
st.caption(
    "Live multi-asset analytics, technical charting, portfolio battleground & wealth simulator"
)

tab_pro, tab_battle, tab_sim, tab_github = st.tabs(
    [
        "📊 Pro Charting & News",
        "⚔️ Asset Battleground",
        "💰 Wealth & DCA Simulator",
        "🤖 GitHub Auto-Tracker",
    ]
)

# ==============================================================================
# TAB 1: PRO TECHNICAL CHARTING & NEWS
# ==============================================================================
with tab_pro:
    presets = {
        "NVIDIA (NVDA)": "NVDA",
        "Apple (AAPL)": "AAPL",
        "Microsoft (MSFT)": "MSFT",
        "S&P 500 Index (^GSPC)": "^GSPC",
        "NASDAQ Composite (^IXIC)": "^IXIC",
        "Bitcoin (BTC-USD)": "BTC-USD",
        "Gold Futures (GC=F)": "GC=F",
        "Crude Oil (CL=F)": "CL=F",
        "Custom Ticker...": "",
    }

    c1, c2, c3 = st.columns(3)
    with c1:
        choice = st.selectbox("Select Market Asset", list(presets.keys()), index=0)
    with c2:
        default_val = presets[choice] if presets[choice] else "TSLA"
        symbol = st.text_input("Ticker Symbol", value=default_val).upper().strip()
    with c3:
        period = st.selectbox("Chart Timeframe", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2)

    ind1, ind2, ind3 = st.columns(3)
    with ind1:
        show_sma20 = st.checkbox("20-Day Moving Average", value=True)
    with ind2:
        show_sma50 = st.checkbox("50-Day Moving Average", value=True)
    with ind3:
        show_rsi = st.checkbox("Show RSI Momentum Panel", value=True)

    if symbol:
        hist = get_live_history(symbol, period)
        if not hist.empty and len(hist) >= 2:
            latest_c = float(hist["Close"].tail(1).item())
            prev_c = float(hist["Close"].tail(2).head(1).item())
            day_chg = ((latest_c - prev_c) / prev_c) * 100
            period_high = float(hist["High"].max())
            period_low = float(hist["Low"].min())
            latest_vol = int(hist["Volume"].tail(1).item())

            k1, k2, k3, k4 = st.columns(4)
            k1.metric(f"{symbol} Price", f"${latest_c:,.2f}", f"{day_chg:+.2f}%")
            k2.metric(f"{period.upper()} High", f"${period_high:,.2f}")
            k3.metric(f"{period.upper()} Low", f"${period_low:,.2f}")
            k4.metric("Latest Volume", f"{latest_vol:,}")

            rows = 2 if show_rsi else 1
            row_heights = [0.72, 0.28] if show_rsi else [1.0]
            fig = make_subplots(
                rows=rows,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.04,
                row_heights=row_heights,
            )

            fig.add_trace(
                go.Candlestick(
                    x=hist.index,
                    open=hist["Open"],
                    high=hist["High"],
                    low=hist["Low"],
                    close=hist["Close"],
                    name="OHLC",
                ),
                row=1,
                col=1,
            )

            if show_sma20:
                fig.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=hist["Close"].rolling(20).mean(),
                        line=dict(color="#00E676", width=1.6),
                        name="20-Day SMA",
                    ),
                    row=1,
                    col=1,
                )

            if show_sma50:
                fig.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=hist["Close"].rolling(50).mean(),
                        line=dict(color="#38BDF8", width=1.6),
                        name="50-Day SMA",
                    ),
                    row=1,
                    col=1,
                )

            if show_rsi:
                rsi_series = compute_rsi(hist["Close"])
                fig.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=rsi_series,
                        line=dict(color="#C084FC", width=1.6),
                        name="RSI (14)",
                    ),
                    row=2,
                    col=1,
                )
                fig.add_hline(y=70, line_dash="dash", line_color="#EF4444", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="#10B981", row=2, col=1)
                fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)

            fig.update_layout(
                template="plotly_dark",
                xaxis_rangeslider_visible=False,
                height=540 if show_rsi else 440,
                hovermode="x unified",
                margin=dict(l=10, r=10, t=20, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Live Headlines
            st.subheader(f"📰 Live Intelligence Feed: {symbol}")
            articles = get_ticker_news(symbol)
            if articles:
                for art in articles:
                    content = art.get("content", art)
                    title = content.get("title", "Market Headline")
                    canonical = content.get("canonicalUrl") or {}
                    url = canonical.get("url") or content.get("link", "#")
                    provider = (content.get("provider") or {}).get("displayName", "Market News")
                    st.markdown(f"**[{title}]({url})** — *{provider}*")
            else:
                st.caption("No recent headlines found for this symbol.")
        else:
            st.error("Unable to fetch data for that ticker. Check the symbol and try again.")

# ==============================================================================
# TAB 2: MULTI-ASSET BATTLEGROUND (HEAD-TO-HEAD COMPARISON)
# ==============================================================================
with tab_battle:
    st.subheader("⚔️ Head-to-Head Asset Performance")
    st.caption("Compare percentage progression across stocks, indices, crypto, and commodities from a 0% baseline.")

    b1, b2 = st.columns([3, 1])
    with b1:
        compare_input = st.text_input(
            "Enter Tickers Separated by Commas",
            value="^GSPC, NVDA, AAPL, BTC-USD, GC=F",
        )
    with b2:
        battle_period = st.selectbox("Comparison Window", ["1mo", "3mo", "6mo", "1y", "3y", "5y"], index=3)

    ticker_list = tuple(t.strip().upper() for t in compare_input.split(",") if t.strip())
    if ticker_list:
        close_df = get_multi_close(ticker_list, battle_period)
        if not close_df.empty:
            norm_df = pd.DataFrame(index=close_df.index)
            for col in close_df.columns:
                valid_col = close_df[col].dropna()
