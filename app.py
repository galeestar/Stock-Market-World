import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Market Pulse Terminal",
    page_icon="📈",
    layout="wide",
)

# Custom CSS for clean dark-glass metric cards
st.markdown(
    """
    <style>
    .stock-card {
        background-color: #1e2130;
        padding: 16px;
        border-radius: 12px;
        border: 1px solid #2e344e;
        text-align: center;
    }
    .badge-up { color: #00e676; font-weight: bold; }
    .badge-down { color: #ff5252; font-weight: bold; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header Banner
st.title("📈 Market Pulse: Real-World Stock Tracker")
st.caption("Automated daily market progression powered by GitHub Actions & Streamlit")

CSV_FILE = "market_history.csv"

# Map tickers to clean display names and logo domains
TICKER_META = {
    "^GSPC": {"name": "S&P 500", "logo": "https://clearbit.com"},
    "^DJI": {"name": "Dow Jones", "logo": "https://clearbit.com"},
    "^IXIC": {"name": "NASDAQ", "logo": "https://clearbit.com"},
    "AAPL": {"name": "Apple Inc.", "logo": "https://clearbit.com"},
    "MSFT": {"name": "Microsoft", "logo": "https://clearbit.com"},
}

# Sidebar Controls & Live Lookup
st.sidebar.header("🎛️ Dashboard Controls")
custom_ticker = st.sidebar.text_input("Search Any Live Ticker (e.g. NVDA, TSLA, BTC-USD):").upper().strip()

if not os.path.exists(CSV_FILE):
    st.warning("No logged data found yet. Run your GitHub Action workflow first to generate market_history.csv.")
    st.stop()

df = pd.read_csv(CSV_FILE)
df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])

available_tickers = df["ticker"].unique().tolist()
selected_tickers = st.sidebar.multiselect(
    "Tracked Watchlist", available_tickers, default=available_tickers
)

chart_mode = st.sidebar.radio(
    "Chart View",
    ["Normalized Growth (%)", "Raw Price History"],
)

# 1. Visual Watchlist Cards with Logos
st.subheader("Watchlist Snapshot")
if selected_tickers:
    cols = st.columns(len(selected_tickers))
    for idx, symbol in enumerate(selected_tickers):
        t_df = df[df["ticker"] == symbol].sort_values("timestamp_utc")
        if not t_df.empty:
            latest = t_df.iloc[-1]
            meta = TICKER_META.get(
                symbol,
                {"name": symbol, "logo": "https://flaticon.com"},
            )
            pct = latest["change_pct"]
            badge_class = "badge-up" if pct >= 0 else "badge-down"
            arrow = "▲" if pct >= 0 else "▼"

            with cols[idx]:
                st.markdown(
                    f"""
                    <div class="stock-card">
                        <img src="{meta['logo']}" width="42" style="border-radius:8px; margin-bottom:8px;"
                             onerror="this.src='https://flaticon.com'">
                        <h4 style="margin:0;">{meta['name']}</h4>
                        <p style="color:#9aa0b4; font-size:12px; margin:2px 0 8px 0;">{symbol}</p>
                        <h3 style="margin:0;">{latest['price']:,.2f}</h3>
                        <p class="{badge_class}" style="margin-top:6px;">{arrow} {pct:+.2f}%</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

st.divider()

# 2. Interactive Plotly Progression Chart
filtered_df = df[df["ticker"].isin(selected_tickers)].copy()

if not filtered_df.empty:
    st.subheader(f"📊 {chart_mode}")
    if chart_mode == "Normalized Growth (%)":
        # Normalize each ticker to 0% at its earliest logged timestamp
        filtered_df["value"] = filtered_df.groupby("ticker")["price"].transform(
            lambda x: ((x / x.iloc[0]) - 1) * 100
        )
        y_label = "Cumulative Growth (%)"
    else:
        filtered_df["value"] = filtered_df["price"]
        y_label = "Price"

    fig = px.line(
        filtered_df,
        x="timestamp_utc",
        y="value",
        color="ticker",
        markers=True,
        labels={"timestamp_utc": "Date (UTC)", "value": y_label, "ticker": "Ticker"},
        template="plotly_dark",
    )
    fig.update_layout(hovermode="x unified", height=420)
    st.plotly_chart(fig, use_container_width=True)

# 3. Live On-Demand Candlestick Lookup
if custom_ticker:
    st.divider()
    st.subheader(f"🕯️ Live 3-Month Candlestick View: {custom_ticker}")
    live_hist = yf.Ticker(custom_ticker).history(period="3mo")
    if not live_hist.empty:
        candle = go.Figure(
            data=[
                go.Candlestick(
                    x=live_hist.index,
                    open=live_hist["Open"],
                    high=live_hist["High"],
                    low=live_hist["Low"],
                    close=live_hist["Close"],
                )
            ]
        )
        candle.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=400)
        st.plotly_chart(candle, use_container_width=True)
    else:
        st.error(f"Could not find market data for '{custom_ticker}'.")

# 4. Expandable Data Table
with st.expander("📄 View Full Logged History"):
    st.dataframe(filtered_df.sort_values("timestamp_utc", ascending=False), use_container_width=True)
