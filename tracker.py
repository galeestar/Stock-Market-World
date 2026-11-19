import os
from datetime import datetime, timezone
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

TICKERS = ["^GSPC", "^DJI", "^IXIC", "AAPL", "MSFT"]
CSV_FILE = "market_history.csv"
CHART_FILE = "market_chart.png"


def fetch_market_data():
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    records = []

    for symbol in TICKERS:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="2d")

        if not hist.empty:
            latest_close = round(float(hist["Close"].tail(1).item()), 2)
            prev_close = (
                round(float(hist["Close"].head(1).item()), 2)
                if len(hist) > 1
                else latest_close
            )
            pct_change = (
                round(((latest_close - prev_close) / prev_close) * 100, 2)
                if prev_close
                else 0.0
            )

            records.append(
                {
                    "timestamp_utc": timestamp,
                    "ticker": symbol,
                    "price": latest_close,
                    "change_pct": pct_change,
                }
            )

    return pd.DataFrame(records)


def save_to_csv(df):
    if df.empty:
        print("No data retrieved.")
        return

    file_exists = os.path.isfile(CSV_FILE)
    df.to_csv(CSV_FILE, mode="a", header=not file_exists, index=False)
    print(f"Logged {len(df)} records to {CSV_FILE}")


def save_chart_image():
    if not os.path.exists(CSV_FILE):
        return

    df = pd.read_csv(CSV_FILE)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"])

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(10, 4.5))

    for symbol, group in df.groupby("ticker"):
        group = group.sort_values("timestamp_utc")
        first_price = float(group["price"].head(1).item())
        norm = ((group["price"] / first_price) - 1) * 100
        ax.plot(group["timestamp_utc"], norm, marker="o", markersize=6, label=symbol)

    ax.set_title("Stock Market Progression (% Change)", fontsize=13, fontweight="bold")
    ax.set_ylabel("Growth (%)")
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.legend()
    plt.xticks(rotation=25)
    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=150)
    plt.close()
    print(f"Saved chart image to {CHART_FILE}")


if __name__ == "__main__":
    market_df = fetch_market_data()
    save_to_csv(market_df)
    save_chart_image()
