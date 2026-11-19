import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Market Pulse Pro", page_icon="📈", layout="wide")


@st.cache_data(ttl=300)
def get_live_history(symbol: str, period: str = "6mo"):
    try:
        return yf.Ticker(symbol).history(period=period)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_ticker_news(symbol: str):
    try:
        news = yf.Ticker(symbol).news
        return news[:5] if news else []
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


st.title("📈 Market Pulse Pro")
st.caption("Automated global market progression, live technical charts & investment simulator")

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

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            selected = st.multiselect("Compare Tracked Assets", tickers, default=tickers)
        with col_f2:
            mode = st.selectbox("Display Metric", ["Normalized Growth (%)", "Raw Price"])

        filtered = df[df["ticker"].isin(selected)].sort_values("timestamp_utc").copy()
        if not filtered.empty:
            # Top KPI Metric Row
            kpi_cols = st.columns(len(selected))
            for idx, sym in enumerate(selected):
                sym_df = filtered[filtered["ticker"] == sym]
                if not sym_df.empty:
                    latest_price = float(sym_df["price"].tail(1).item())
                    latest_chg = float(sym_df["change_pct"].tail(1).item())
                    kpi_cols[idx].metric(
                        label=sym,
                        value=f"{latest_price:,.2f}",
                        delta=f"{latest_chg:+.2f}%",
                    )

            if mode == "Normalized Growth (%)":
                filtered["plot_val"] = filtered.groupby("ticker")["price"].transform(
                    lambda s: ((s / float(s.head(1).item())) - 1) * 100
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
                labels={"timestamp_utc": "Date (UTC)", "plot_val": y_title},
            )
            fig.update_layout(hovermode="x unified", height=430)
            st.plotly_chart(fig, use_container_width=True)

            st.download_button(
                label="⬇️ Download Market History (CSV)",
                data=filtered.to_csv(index=False).encode("utf-8"),
                file_name="market_history_export.csv",
                mime="text/csv",
            )
        else:
            st.warning("Select at least one asset above to display the chart.")
    else:
        st.info("Run your GitHub Action workflow once to generate market_history.csv.")

# --- TAB 2: LIVE DEEP-DIVE & NEWS ---
with tab_explorer:
    presets = {
        "Custom Symbol": "",
        "S&P 500 (^GSPC)": "^GSPC",
        "NASDAQ (^IXIC)": "^IXIC",
        "NVIDIA (NVDA)": "NVDA",
        "Apple (AAPL)": "AAPL",
        "Bitcoin (BTC-USD)": "BTC-USD",
        "Gold (GC=F)": "GC=F",
    }

    c1, c2, c3 = st.columns(3)
    with c1:
        preset_choice = st.selectbox("Quick Preset", list(presets.keys()), index=3)
    with c2:
        default_sym = presets[preset_choice] if presets[preset_choice] else "TSLA"
        symbol = st.text_input("Or Enter Any Ticker", value=default_sym).upper().strip()
    with c3:
        period = st.selectbox("Timeframe", ["1mo", "3mo", "6mo", "1y", "5y"], index=2)

    show_sma = st.checkbox("Overlay 20-Day Moving Average", value=True)

    if symbol:
        hist = get_live_history(symbol, period)
        if not hist.empty:
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
            if show_sma:
                hist["SMA_20"] = hist["Close"].rolling(20).mean()
                fig_candle.add_trace(
                    go.Scatter(
                        x=hist.index,
                        y=hist["SMA_20"],
                        line=dict(color="#00E676", width=1.5),
                        name="20-Day SMA",
                    )
                )
            fig_candle.update_layout(
                template="plotly_dark", xaxis_rangeslider_visible=False, height=430
            )
            st.plotly_chart(fig_candle, use_container_width=True)

            st.subheader(f"📰 Latest Headlines for {symbol}")
            news_items = get_ticker_news(symbol)
            if news_items:
                for article in news_items:
                    content = article.get("content", article)
                    title = content.get("title", "Market Update")
                    canonical = content.get("canonicalUrl") or {}
                    link = canonical.get("url") or content.get("link", "#")
                    st.markdown(f"- [{title}]({link})")
            else:
                st.caption("No recent headlines available for this ticker.")
        else:
            st.error("Ticker not found. Try a valid symbol like AAPL, MSFT, or BTC-USD.")

# --- TAB 3: "WHAT-IF" INVESTMENT SIMULATOR ---
with tab_simulator:
    st.subheader("Calculate Historical Return")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        sim_ticker = st.text_input("Asset Ticker", value="^GSPC").upper().strip()
    with s2:
        currency = st.selectbox("Currency", ["USD ($)", "NGN (₦)"])
    with s3:
        default_amt = 1000.0 if currency == "USD ($)" else 1000000.0
        invest_amount = st.number_input(
            "Initial Investment", min_value=10.0, value=default_amt, step=100.0
        )
    with s4:
        sim_period = st.selectbox("Holding Period", ["6mo", "1y", "2y", "5y"], index=1)

    sim_hist = get_live_history(sim_ticker, sim_period)
    if not sim_hist.empty:
        start_price = float(sim_hist["Close"].head(1).item())
        end_price = float(sim_hist["Close"].tail(1).item())
        final_value = invest_amount * (end_price / start_price)
        profit = final_value - invest_amount
        roi = (profit / invest_amount) * 100
        sym_prefix = "$" if currency == "USD ($)" else "₦"

        m1, m2, m3 = st.columns(3)
        m1.metric("Final Value", f"{sym_prefix}{final_value:,.2f}")
        m2.metric("Total Profit / Loss", f"{sym_prefix}{profit:+,.2f}", delta=f"{roi:+.2f}%")
        m3.metric("Asset Price Change", f"${start_price:,.2f} → ${end_price:,.2f}")

        if currency == "NGN (₦)":
            fx_rate = get_usd_ngn_rate()
            st.caption(f"Reference FX rate: ~₦{fx_rate:,.2f} / $1 (simulation tracks underlying asset return)")

        sim_hist["Portfolio Value"] = invest_amount * (sim_hist["Close"] / start_price)
        fig_sim = px.area(
            sim_hist,
            y="Portfolio Value",
            template="plotly_dark",
            title=f"Growth of {sym_prefix}{invest_amount:,.0f} in {sim_ticker} ({sim_period})",
        )
        st.plotly_chart(fig_sim, use_container_width=True)
    else:
        st.error("Unable to load historical data for that ticker.")

st.divider()
st.caption("⚠️ For informational and educational purposes only. Not financial advice.")
