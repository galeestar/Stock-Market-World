import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Market Pulse Pro", page_icon="📈", layout="wide")

# Cache live Yahoo Finance calls for 5 minutes so public traffic stays fast
@st.cache_data(ttl=300)
def get_live_history(symbol: str, period: str = "6mo"):
    return yf.Ticker(symbol).history(period=period)

@st.cache_data(ttl=600)
def get_ticker_news(symbol: str):
    return yf.Ticker(symbol).news[:5]

st.title("📈 Market Pulse Pro")
st.caption("Real-world market progression, interactive simulator & live market intelligence")

# Top Navigation Tabs
tab_overview, tab_explorer, tab_simulator = st.tabs(
    ["📊 Market Progression", "🔍 Live Ticker & News", "💰 Investment Simulator"]
)

CSV_FILE = "market_history.csv"

# --- TAB 1: AUTOMATED MARKET PROGRESSION ---
with tab_overview:
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])
        tickers = df["ticker"].unique().tolist()

        col_f1, col_f2 = st.columns([3, 1])
        with col_f1:
            selected = st.multiselect("Compare Assets", tickers, default=tickers)
        with col_f2:
            mode = st.selectbox("Metric", ["Normalized Growth (%)", "Raw Price"])

        filtered = df[df["ticker"].isin(selected)].copy()
        if not filtered.empty:
            if mode == "Normalized Growth (%)":
              filtered["plot_val"] = filtered.groupby("ticker")["price"].transform(
                  lambda x: ((x / x.iloc[0]) - 1) * 100
              )

                y_title = "Return (%)"
            else:
                filtered["plot_val"] = filtered["price"]
                y_title = "Price"

            fig = px.line(
                filtered,
                x="timestamp_utc",
                y="plot_val",
                color="ticker",
                markers=True,
                template="plotly_dark",
                labels={"timestamp_utc": "Date", "plot_val": y_title},
            )
            fig.update_layout(hovermode="x unified", height=430)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Run your GitHub Action workflow to populate historical tracking data.")

# --- TAB 2: LIVE DEEP-DIVE & NEWS ---
with tab_explorer:
    c1, c2 = st.columns([2, 1])
    with c1:
        symbol = st.text_input("Enter Ticker Symbol", value="NVDA").upper().strip()
    with c2:
        period = st.selectbox("Timeframe", ["1mo", "3mo", "6mo", "1y", "5y"], index=2)

    if symbol:
        hist = get_live_history(symbol, period)
        if not hist.empty:
            hist["SMA_20"] = hist["Close"].rolling(20).mean()
            fig_candle = go.Figure()
            fig_candle.add_trace(
                go.Candlestick(
                    x=hist.index,
                    open=hist["Open"],
                    high=hist["High"],
                    low=hist["Low"],
                    close=hist["Close"],
                    name="Price",
                )
            )
            fig_candle.add_trace(
                go.Scatter(
                    x=hist.index,
                    y=hist["SMA_20"],
                    line=dict(color="#00E676", width=1.5),
                    name="20-Day SMA",
                )
            )
            fig_candle.update_layout(
                template="plotly_dark", xaxis_rangeslider_visible=False, height=420
            )
            st.plotly_chart(fig_candle, use_container_width=True)

            st.subheader(f"📰 Latest Headlines for {symbol}")
            for article in get_ticker_news(symbol):
                content = article.get("content", article)
                title = content.get("title", "Market Update")
                link = content.get("canonicalUrl", {}).get("url") or content.get("link", "#")
                st.markdown(f"- [{title}]({link})")
        else:
            st.error("Ticker not found. Try a valid symbol like AAPL, MSFT, or BTC-USD.")

# --- TAB 3: "WHAT-IF" INVESTMENT SIMULATOR ---
with tab_simulator:
    st.subheader("Calculate Historical Return")
    s1, s2, s3 = st.columns(3)
    with s1:
        sim_ticker = st.text_input("Asset Ticker", value="^GSPC").upper().strip()
    with s2:
        invest_amount = st.number_input("Initial Investment ($)", min_value=10.0, value=1000.0, step=100.0)
    with s3:
        sim_period = st.selectbox("Holding Period", ["6mo", "1y", "2y", "5y"], index=1)

    sim_hist = get_live_history(sim_ticker, sim_period)
    if not sim_hist.empty:
        start_price = float(sim_hist["Close"].iloc)
        end_price = float(sim_hist["Close"].iloc[-1])
        final_value = invest_amount * (end_price / start_price)
        profit = final_value - invest_amount
        roi = (profit / invest_amount) * 100

        m1, m2, m3 = st.columns(3)
        m1.metric("Final Value", f"${final_value:,.2f}")
        m2.metric("Total Profit / Loss", f"${profit:+,.2f}", delta=f"{roi:+.2f}%")
        m3.metric("Start → Current Price", f"${start_price:,.2f} → ${end_price:,.2f}")

        sim_hist["Portfolio Value ($)"] = invest_amount * (sim_hist["Close"] / start_price)
        fig_sim = px.area(
            sim_hist,
            y="Portfolio Value ($)",
            template="plotly_dark",
            title=f"Growth of ${invest_amount:,.0f} in {sim_ticker} ({sim_period})",
        )
        st.plotly_chart(fig_sim, use_container_width=True)
