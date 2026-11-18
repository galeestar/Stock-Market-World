import os
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf

# Indices & stocks to track (^GSPC = S&P 500, ^DJI = Dow Jones, ^IXIC = Nasdaq)
TICKERS = ["^GSPC", "^DJI", "^IXIC", "AAPL", "MSFT"]
CSV_FILE = "market_history.csv"

def fetch_market_data():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    records = []

    for symbol in TICKERS:
        ticker = yf.Ticker(symbol)
        # Fetch the most recent 2 days to calculate daily change
        hist = ticker.history(period="2d")
        
        if not hist.empty:
            latest_close = round(float(hist["Close"].iloc[-1]), 2)
            prev_close = round(float(hist["Close"].iloc[0]), 2) if len(hist) > 1 else latest_close
            pct_change = round(((latest_close - prev_close) / prev_close) * 100, 2) if prev_close else 0.0

            records.append({
                "timestamp_utc": timestamp,
                "ticker": symbol,
                "price": latest_close,
                "change_pct": pct_change
            })

    return pd.DataFrame(records)

def save_to_csv(df):
    if df.empty:
        print("No data retrieved.")
        return

    file_exists = os.path.isfile(CSV_FILE)
    df.to_csv(CSV_FILE, mode="a", header=not file_exists, index=False)
    print(f"Logged {len(df)} records to {CSV_FILE}")

if __name__ == "__main__":
    market_df = fetch_market_data()
    save_to_csv(market_df)

import matplotlib.pyplot as plt

def save_chart_image():
    if not os.path.exists(CSV_FILE):
        return
    df = pd.read_csv(CSV_FILE)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(10, 4.5))

    for symbol, group in df.groupby("ticker"):
        group = group.sort_values("timestamp_utc")
        norm = ((group["price"] / group["price"].iloc[0]) - 1) * 100
        ax.plot(group["timestamp_utc"], norm, marker="o", label=symbol)

    ax.set_title("Stock Market Progression (% Change)", fontsize=13, fontweight="bold")
    ax.set_ylabel("Growth (%)")
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.legend()
    plt.xticks(rotation=25)
    plt.tight_layout()
    plt.savefig("market_chart.png", dpi=150)
    plt.close()
