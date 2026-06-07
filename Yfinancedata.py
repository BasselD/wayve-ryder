"""
APEX Data Module
Pulls and caches market data using yfinance.
Run this file to download data for all tracked tickers.
"""

import yfinance as yf
import pandas as pd
import os

# ── CONFIG ──────────────────────────────────────────────────────────────────
TICKERS = ["SPY", "NVDA", "GOOGL", "TSLA", "AAPL", "AMD",
           "MSFT", "AMZN", "META", "SMCI", "PLTR",
           "CRM", "NFLX"]
START_DATE = "2020-01-01"
END_DATE   = "2026-06-06"
DATA_DIR   = "./data"
# ────────────────────────────────────────────────────────────────────────────

def download_daily(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Download daily OHLCV data for a single ticker."""
    df = yf.download(
        ticker,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        progress=False
    )
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df.index.name = "Date"
    return df


def download_intraday(ticker: str, interval: str = "1h") -> pd.DataFrame:
    """
    Download intraday data.
    Good for lower-timeframe entry timing after daily setup confirmation.
    """
    df = yf.download(
        ticker,
        period="730d",
        interval=interval,
        auto_adjust=True,
        progress=False
    )
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df


def save_data(df: pd.DataFrame, ticker: str, timeframe: str = "daily"):
    """Save dataframe to CSV in ./data folder."""
    os.makedirs(DATA_DIR, exist_ok=True)
    path = f"{DATA_DIR}/{ticker}_{timeframe}.csv"
    df.to_csv(path)
    print(f"✅ Saved {ticker} ({timeframe}): {len(df)} rows → {path}")


def load_data(ticker: str, timeframe: str = "daily") -> pd.DataFrame:
    """Load previously saved CSV data."""
    path = f"{DATA_DIR}/{ticker}_{timeframe}.csv"
    df = pd.read_csv(path, index_col="Date", parse_dates=True)
    return df


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add indicators used in EW + Fib + S/R analysis.
    """
    df = df.copy()

    df["SMA_50"] = df["Close"].rolling(50).mean()
    df["SMA_200"] = df["Close"].rolling(200).mean()

    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["ATR_14"] = true_range.rolling(14).mean()

    df["Volume_MA_20"] = df["Volume"].rolling(20).mean()
    df["Volume_Above_Avg"] = df["Volume"] > df["Volume_MA_20"]

    return df


def get_fib_levels(swing_low: float, swing_high: float) -> dict:
    """
    Calculate Fibonacci retracement and extension levels.
    """
    diff = swing_high - swing_low

    retracements = {
        "23.6%":  swing_high - diff * 0.236,
        "38.2%":  swing_high - diff * 0.382,
        "50.0%":  swing_high - diff * 0.500,
        "61.8%":  swing_high - diff * 0.618,
        "78.6%":  swing_high - diff * 0.786,
        "100.0%": swing_low,
    }

    extensions = {
        "100.0%": swing_high + diff * 1.000,
        "127.2%": swing_high + diff * 1.272,
        "161.8%": swing_high + diff * 1.618,
        "200.0%": swing_high + diff * 2.000,
        "261.8%": swing_high + diff * 2.618,
    }

    return {
        "swing_low": swing_low,
        "swing_high": swing_high,
        "retracement": retracements,
        "extension": extensions
    }


def validate_wave_rules(
    w1_start: float,
    w1_end: float,
    w2_end: float,
    w3_end: float,
    w4_end: float
) -> dict:
    """
    Validate the three core Elliott Wave rules for a bullish impulse.
    """
    w1_length = abs(w1_end - w1_start)
    w3_length = abs(w3_end - w2_end)

    rule1 = w2_end > w1_start
    rule2 = w3_length > w1_length
    rule3 = w4_end > w1_end

    return {
        "rule1_pass": rule1,
        "rule1_detail": f"Wave 2 end ({w2_end:.2f}) {'>' if rule1 else '<='} Wave 1 start ({w1_start:.2f})",
        "rule2_pass": rule2,
        "rule2_detail": f"Wave 3 length ({w3_length:.2f}) {'>' if rule2 else '<='} Wave 1 length ({w1_length:.2f})",
        "rule3_pass": rule3,
        "rule3_detail": f"Wave 4 end ({w4_end:.2f}) {'>' if rule3 else '<='} Wave 1 end ({w1_end:.2f})",
        "all_rules_pass": rule1 and rule2 and rule3,
        "grade": "VALID — proceed to Fib + S/R check" if (rule1 and rule2 and rule3) else "INVALID — count must be abandoned"
    }


if __name__ == "__main__":
    print("=" * 50)
    print("APEX Data Download")
    print("=" * 50)

    for ticker in TICKERS:
        print(f"\nDownloading {ticker}...")
        try:
            df = download_daily(ticker, START_DATE, END_DATE)
            df = add_indicators(df)
            save_data(df, ticker, "daily")
        except Exception as e:
            print(f"❌ Daily error: {e}")

        try:
            df_1h = download_intraday(ticker, interval="1h")
            save_data(df_1h, ticker, "1h")
        except Exception as e:
            print(f"❌ 1H error: {e}")

    print("\n" + "=" * 50)
    print("Done. Data saved to ./data/")
    print("=" * 50)

    print("\n── Fib Level Demo ──")
    fib = get_fib_levels(520, 600)
    print(f"Wave 2 entry zone (61.8% retrace): ${fib['retracement']['61.8%']:.2f}")
    print(f"Wave 2 entry zone (50.0% retrace): ${fib['retracement']['50.0%']:.2f}")
    print(f"Wave 3 target (161.8% extend): ${fib['extension']['161.8%']:.2f}")

    print("\n── Wave Rule Validator Demo ──")
    result = validate_wave_rules(
        w1_start=500,
        w1_end=560,
        w2_end=530,
        w3_end=650,
        w4_end=590
    )
    for k, v in result.items():
        print(f"{k}: {v}")