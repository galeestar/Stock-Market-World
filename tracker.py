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
