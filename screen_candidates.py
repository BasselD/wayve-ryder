"""
APEX Ticker Screener — find clean-EW candidates to grow the MTF universe.

Downloads daily + 1H data for candidate tickers into ./data/ (same format as
Yfinancedata.py), then runs the EXISTING MTF engine on each WITHOUT touching the
production TICKERS list. Ranks candidates by 4H entries, win rate, and expectancy.

This is a research tool — it does not modify Backtest_MTF.py or production config.
Run:  python screen_candidates.py
"""

import os
import warnings
warnings.filterwarnings("ignore")
import pandas as pd
import yfinance as yf

import Backtest_MTF as bt

# ── Candidate pool (3 approved groups) ────────────────────────────────────────
CANDIDATES = {
    "AI/Semis":     ["AVGO", "MU", "MRVL", "ARM", "COIN"],
    "Megacaps":     ["UBER", "NOW", "PANW", "ORCL"],
    "Momentum":     ["SHOP", "ABNB", "DKNG", "RBLX"],
}
START_DATE = "2020-01-01"
END_DATE   = "2026-06-06"
DATA_DIR   = "./data"


def download_one(ticker):
    """Download daily + 1H for a candidate if not already cached."""
    daily_path = f"{DATA_DIR}/{ticker}_daily.csv"
    h1_path    = f"{DATA_DIR}/{ticker}_1h.csv"

    if not os.path.exists(daily_path):
        d = yf.download(ticker, start=START_DATE, end=END_DATE,
                        interval="1d", auto_adjust=True, progress=False)
        d.columns = [c[0] if isinstance(c, tuple) else c for c in d.columns]
        d.index.name = "Date"
        d.to_csv(daily_path)
    if not os.path.exists(h1_path):
        h = yf.download(ticker, period="730d", interval="1h",
                        auto_adjust=True, progress=False)
        h.columns = [c[0] if isinstance(c, tuple) else c for c in h.columns]
        h.to_csv(h1_path)


def screen(ticker, regime_series):
    """Run the production MTF engine on one ticker. Returns a metrics row or None."""
    df_daily = bt.load_daily(ticker)
    df_4h    = bt.load_4h(ticker)
    df_4h["RSI"]  = bt.calc_rsi(df_4h["Close"])
    df_4h["MA50"] = df_4h["Close"].rolling(bt.FH_TREND_MA).mean()

    regime = regime_series.reindex(df_daily.index, method="ffill").fillna(False) \
        if regime_series is not None else pd.Series(True, index=df_daily.index)

    zones = bt.scan_daily_zones(df_daily, ticker, regime)
    setups = []
    for z in zones:
        e = bt.find_4h_entry(z, df_4h)
        if e:
            setups.append({**z, **e})

    if not setups:
        return {"ticker": ticker, "zones": len(zones), "entries": 0,
                "trades": 0, "win_rate": None, "expectancy": None,
                "profit_factor": None, "max_dd": None, "total_return": 0.0}

    trades = bt.simulate_mtf_trades(df_4h, setups)
    tdf    = pd.DataFrame(trades)
    m      = bt.calc_metrics(tdf)
    return {"ticker": ticker, "zones": len(zones), "entries": len(setups),
            "trades": m["total"], "win_rate": m["win_rate"],
            "expectancy": m["expectancy"], "profit_factor": m["profit_factor"],
            "max_dd": m["max_drawdown"], "total_return": m["total_return"]}


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)

    print("📥 Downloading candidate data (cached if present)...")
    for group, tickers in CANDIDATES.items():
        for t in tickers:
            try:
                download_one(t)
                print(f"   ✅ {t}")
            except Exception as e:
                print(f"   ❌ {t}: {e}")

    # SPY regime
    try:
        spy = bt.load_daily(bt.REGIME_TICKER)
        spy["MA200"] = spy["Close"].rolling(bt.D_REGIME_MA).mean()
        regime_series = spy["Close"] > spy["MA200"]
    except Exception:
        regime_series = None

    print("\n🔬 Screening candidates through the MTF engine...\n")
    rows = []
    for group, tickers in CANDIDATES.items():
        for t in tickers:
            try:
                r = screen(t, regime_series)
                r["group"] = group
                rows.append(r)
                wr = f"{r['win_rate']}%" if r['win_rate'] is not None else "—"
                e  = f"{r['expectancy']}%" if r['expectancy'] is not None else "—"
                print(f"  {t:5s} [{group:9s}] | zones {r['zones']:2d} | entries {r['entries']:2d} | "
                      f"trades {r['trades']:2d} | WR {wr:>6s} | E {e:>7s} | net {r['total_return']:6.1f}%")
            except Exception as ex:
                print(f"  {t:5s} ERROR: {ex}")

    res = pd.DataFrame(rows)
    res.to_csv(f"{bt.RESULTS_DIR}/candidate_screen.csv", index=False)

    # Rank: positive expectancy + meaningful sample (>=3 trades)
    print(f"\n{'='*70}")
    print("🏆 RANKED — candidates with ≥3 trades and positive expectancy:")
    qualified = res[(res["trades"] >= 3) & (res["expectancy"].fillna(-99) > 0)] \
        .sort_values("expectancy", ascending=False)
    if len(qualified):
        for _, r in qualified.iterrows():
            print(f"   ✅ {r['ticker']:5s} | {r['trades']:2.0f} trades | WR {r['win_rate']}% | "
                  f"E {r['expectancy']}% | PF {r['profit_factor']} | DD {r['max_dd']}%")
    else:
        print("   (none cleared the bar — small sample is expected on 2.9yr of data)")
    print(f"{'='*70}")
    print(f"Full results: {bt.RESULTS_DIR}/candidate_screen.csv")
