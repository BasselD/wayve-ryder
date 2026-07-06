"""
APEX Live Signal Scanner
Runs all three strategies against current data and surfaces actionable setups.
Designed to be run on demand: python3 Scanner_Live.py

Outputs:
  - Console trade cards (ranked by confidence)
  - ./signals/signals_YYYY-MM-DD.csv
"""

import pandas as pd
import numpy as np
import yfinance as yf
import os
import warnings
from datetime import datetime, timedelta

from events import (load_earnings_calendar, days_to_next_earnings,
                    calendar_is_stale, EARNINGS_VETO_DAYS)
warnings.filterwarnings("ignore")

# ── CONFIG ───────────────────────────────────────────────────────────────────
TICKERS = [
    # Core — high-conviction momentum tech
    "NVDA", "TSLA", "AAPL", "AMD",  "MSFT", "AMZN", "GOOGL", "META",
    "CRM",  "MU",   "DKNG", "AVGO",
    "COIN", "MRVL", "PANW", "ORCL", "ABNB",
    # Expansion batch 1
    "CRWD", "APP",  "ANET", "FTNT",
    "SNOW", "HOOD", "DASH", "XYZ",
    # Expansion batch 2 — quality momentum additions
    "DDOG", "ZS",   "ADBE", "CELH", "LRCX",
]

DATA_DIR       = "./data"
SIGNALS_DIR    = "./signals"
LOOKBACK_DAYS  = 10     # how many days back to look for completed signals
PENDING_W2_BARS = 30   # how many bars back a W2 can be and still be considered active
START_DATE     = "2020-01-01"

# W3 Scalper params (must match Backtest_W3_Scalper.py)
W3_SWING_LB    = 7
W3_MIN_W1      = 0.04
W3_FIB_MIN     = 0.382
W3_FIB_MAX     = 0.700
W3_BUF         = 0.001
W3_TARGET      = 1.618
W3_STOP_PCT    = None   # stop = W2 low (dynamic)
W3_MIN_RR      = 1.0
W3_RSI_W2      = 65
W3_RSI_BRK     = 50
W3_VOL_RATIO   = 1.0
W3_VOL_LB      = 20
W3_MAX_W2_BARS = 60
W3_MAX_W3_BARS = 30

# Daily v11 params (must match Backtest_Daily.py)
D_MIN_W1       = 0.07
D_FIB_MIN      = 0.50
D_FIB_MAX      = 0.786
D_RSI_W2       = 55
D_RSI_BRK      = 50
D_VOL_RATIO    = 1.3
D_TARGET       = 1.618
D_SWING_LB     = 10
D_MIN_RR       = 1.5

# Regime
REGIME_TICKER  = "QQQ"
REGIME_MA      = 50
# ─────────────────────────────────────────────────────────────────────────────


def refresh_data(ticker):
    """Download latest daily data and save."""
    df = yf.download(ticker, start=START_DATE,
                     end=(datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d"),
                     interval="1d", auto_adjust=True, progress=False)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df.index.name = "Date"
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(f"{DATA_DIR}/{ticker}_daily.csv")
    return df


def load_data(ticker):
    path = f"{DATA_DIR}/{ticker}_daily.csv"
    return pd.read_csv(path, index_col="Date", parse_dates=True)


def add_indicators(df):
    df = df.copy()
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df["RSI"]   = 100 - 100 / (1 + rs)
    df["MA50"]  = df["Close"].rolling(50).mean()
    df["Vol20"] = df["Volume"].rolling(W3_VOL_LB).mean()
    return df


def find_swing_highs(df, lookback):
    highs = []
    for i in range(lookback, len(df) - lookback):
        if df["High"].iloc[i] == df["High"].iloc[i-lookback:i+lookback+1].max():
            highs.append(i)
    return highs


def find_swing_lows(df, lookback):
    lows = []
    for i in range(lookback, len(df) - lookback):
        if df["Low"].iloc[i] == df["Low"].iloc[i-lookback:i+lookback+1].min():
            lows.append(i)
    return lows


# ── W3 SCANNER ───────────────────────────────────────────────────────────────

def scan_w3_live(df, ticker, regime, cutoff_date):
    """Find W3 setups where the breakout bar is within LOOKBACK_DAYS of today."""
    signals = []
    swing_highs = find_swing_highs(df, W3_SWING_LB)
    swing_lows  = find_swing_lows(df, W3_SWING_LB)
    used_w1 = set()

    for low_idx in swing_lows:
        phase1_limit = min(low_idx + W3_MAX_W2_BARS, len(df))
        phase2_limit = min(low_idx + W3_MAX_W2_BARS + W3_MAX_W3_BARS, len(df))

        candidates = [h for h in swing_highs if low_idx < h <= low_idx + 80]
        if not candidates:
            continue
        high_idx = candidates[0]
        if high_idx in used_w1:
            continue

        w0_low  = df["Low"].iloc[low_idx]
        w1_high = df["High"].iloc[high_idx]
        w1_size = w1_high - w0_low
        if w1_size / w0_low < W3_MIN_W1:
            continue

        fib_382 = w1_high - W3_FIB_MIN * w1_size
        fib_786 = w1_high - W3_FIB_MAX * w1_size

        w2_price, w2_idx = float("inf"), None
        for j in range(high_idx + 1, phase1_limit):
            if df["Low"].iloc[j] < w0_low:
                break
            retrace = (w1_high - df["Low"].iloc[j]) / w1_size
            if W3_FIB_MIN <= retrace <= W3_FIB_MAX:
                if df["Low"].iloc[j] < w2_price:
                    w2_price, w2_idx = df["Low"].iloc[j], j

        if w2_idx is None:
            continue

        rsi_at_w2 = df["RSI"].iloc[w2_idx]
        if pd.isna(rsi_at_w2) or rsi_at_w2 >= W3_RSI_W2:
            continue

        for k in range(w2_idx + 1, phase2_limit):
            if df["Low"].iloc[k] < w0_low:
                break
            if df["Close"].iloc[k] <= w1_high * (1 + W3_BUF):
                continue

            # Only care about recent breakouts
            entry_date = df.index[k]
            if entry_date < cutoff_date:
                continue

            # Regime
            if entry_date in regime.index and not bool(regime.loc[entry_date]):
                break

            # RSI at breakout
            rsi_k = df["RSI"].iloc[k]
            if pd.isna(rsi_k) or rsi_k < W3_RSI_BRK or rsi_k <= rsi_at_w2:
                break

            # Volume
            vol20 = df["Vol20"].iloc[k]
            if not pd.isna(vol20) and vol20 > 0:
                if df["Volume"].iloc[k] < W3_VOL_RATIO * vol20:
                    break

            entry_price  = df["Close"].iloc[k]
            stop_price   = w2_price
            target_price = w2_price + W3_TARGET * w1_size
            risk         = entry_price - stop_price
            reward       = target_price - entry_price
            if risk <= 0:
                break
            rr = reward / risk
            if rr < W3_MIN_RR:
                break

            used_w1.add(high_idx)
            risk_pct   = risk / entry_price * 100
            reward_pct = reward / entry_price * 100

            signals.append({
                "strategy":     "W3_SCALPER",
                "ticker":       ticker,
                "signal_date":  entry_date.strftime("%Y-%m-%d"),
                "entry":        round(entry_price, 2),
                "stop":         round(stop_price, 2),
                "target":       round(target_price, 2),
                "risk_pct":     round(risk_pct, 2),
                "reward_pct":   round(reward_pct, 2),
                "rr":           round(rr, 2),
                "rsi_at_w2":    round(rsi_at_w2, 1),
                "rsi_at_entry": round(rsi_k, 1),
                "w1_pct":       round(w1_size / w0_low * 100, 1),
                "w2_retrace":   round((w1_high - w2_price) / w1_size * 100, 1),
            })
            break

    return signals


# ── DAILY v11 SCANNER ────────────────────────────────────────────────────────

def scan_daily_live(df, ticker, regime, cutoff_date):
    """Find Daily v11 long setups where confirmation is within LOOKBACK_DAYS."""
    signals = []
    swing_highs = find_swing_highs(df, D_SWING_LB)
    swing_lows  = find_swing_lows(df, D_SWING_LB)
    used_w1 = set()

    for low_idx in swing_lows:
        candidates = [h for h in swing_highs if low_idx < h <= low_idx + 100]
        if not candidates:
            continue
        high_idx = candidates[0]
        if high_idx in used_w1:
            continue

        w0_low  = df["Low"].iloc[low_idx]
        w1_high = df["High"].iloc[high_idx]
        w1_size = w1_high - w0_low
        if w1_size / w0_low < D_MIN_W1:
            continue

        w2_price, w2_idx = float("inf"), None
        search_end = min(high_idx + 90, len(df))
        for j in range(high_idx + 1, search_end):
            if df["Low"].iloc[j] < w0_low:
                break
            retrace = (w1_high - df["Low"].iloc[j]) / w1_size
            if D_FIB_MIN <= retrace <= D_FIB_MAX:
                if df["Low"].iloc[j] < w2_price:
                    w2_price, w2_idx = df["Low"].iloc[j], j

        if w2_idx is None:
            continue

        rsi_w2 = df["RSI"].iloc[w2_idx]
        if pd.isna(rsi_w2) or rsi_w2 >= D_RSI_W2:
            continue

        confirm_end = min(w2_idx + 60, len(df))
        for k in range(w2_idx + 1, confirm_end):
            if df["Low"].iloc[k] < w0_low:
                break
            if df["Close"].iloc[k] <= w1_high:
                continue

            entry_date = df.index[k]
            if entry_date < cutoff_date:
                continue

            if entry_date in regime.index and not bool(regime.loc[entry_date]):
                break

            rsi_k = df["RSI"].iloc[k]
            if pd.isna(rsi_k) or rsi_k < D_RSI_BRK:
                break

            vol20 = df["Vol20"].iloc[k]
            if not pd.isna(vol20) and vol20 > 0:
                if df["Volume"].iloc[k] < D_VOL_RATIO * vol20:
                    break

            entry_price  = df["Close"].iloc[k]
            stop_price   = w2_price
            target_price = w2_price + D_TARGET * w1_size
            risk         = entry_price - stop_price
            reward       = target_price - entry_price
            if risk <= 0:
                break
            rr = reward / risk
            if rr < D_MIN_RR:
                break

            used_w1.add(high_idx)
            signals.append({
                "strategy":     "DAILY_V11",
                "ticker":       ticker,
                "signal_date":  entry_date.strftime("%Y-%m-%d"),
                "entry":        round(entry_price, 2),
                "stop":         round(stop_price, 2),
                "target":       round(target_price, 2),
                "risk_pct":     round(risk / entry_price * 100, 2),
                "reward_pct":   round(reward / entry_price * 100, 2),
                "rr":           round(rr, 2),
                "rsi_at_w2":    round(rsi_w2, 1),
                "rsi_at_entry": round(rsi_k, 1),
                "w1_pct":       round(w1_size / w0_low * 100, 1),
                "w2_retrace":   round((w1_high - w2_price) / w1_size * 100, 1),
            })
            break

    return signals


# ── PENDING W3 SCANNER ───────────────────────────────────────────────────────

def scan_pending_w3(df, ticker, regime):
    """Find W3 setups where W2 is complete but breakout hasn't fired yet.
    Price must be within 6% below the W1 high trigger — coiling for Monday.
    """
    pending      = []
    swing_highs  = find_swing_highs(df, W3_SWING_LB)
    swing_lows   = find_swing_lows(df, W3_SWING_LB)
    used_w1      = set()
    current_bar  = len(df) - 1
    current_price = df["Close"].iloc[-1]

    for low_idx in swing_lows:
        candidates = [h for h in swing_highs if low_idx < h <= low_idx + 80]
        if not candidates:
            continue
        high_idx = candidates[0]
        if high_idx in used_w1:
            continue

        w0_low  = df["Low"].iloc[low_idx]
        w1_high = df["High"].iloc[high_idx]
        w1_size = w1_high - w0_low
        if w1_size / w0_low < W3_MIN_W1:
            continue

        w2_price, w2_idx = float("inf"), None
        phase1_limit = min(high_idx + W3_MAX_W2_BARS, len(df))
        for j in range(high_idx + 1, phase1_limit):
            if df["Low"].iloc[j] < w0_low:
                break
            retrace = (w1_high - df["Low"].iloc[j]) / w1_size
            if W3_FIB_MIN <= retrace <= W3_FIB_MAX:
                if df["Low"].iloc[j] < w2_price:
                    w2_price, w2_idx = df["Low"].iloc[j], j

        if w2_idx is None:
            continue

        # W2 must be recent enough to still be active
        if current_bar - w2_idx > PENDING_W2_BARS:
            continue

        rsi_at_w2 = df["RSI"].iloc[w2_idx]
        if pd.isna(rsi_at_w2) or rsi_at_w2 >= W3_RSI_W2:
            continue

        # Confirm W3 has NOT fired yet and structure is intact
        trigger = w1_high * (1 + W3_BUF)
        already_triggered = False
        for k in range(w2_idx + 1, current_bar + 1):
            if df["Close"].iloc[k] > trigger:
                already_triggered = True
                break
            if df["Low"].iloc[k] < w0_low:
                already_triggered = True  # W2 structure broken
                break
        if already_triggered:
            continue

        # Must be within 6% of trigger — close enough to watch for Monday
        proximity_pct = (trigger - current_price) / current_price * 100
        if proximity_pct > 6.0 or proximity_pct < -0.5:
            continue

        # Regime check
        last_date = df.index[-1]
        if last_date in regime.index and not bool(regime.loc[last_date]):
            continue

        stop_price   = w2_price * 0.998
        target_price = w2_price + W3_TARGET * w1_size
        risk         = trigger - stop_price
        reward       = target_price - trigger
        if risk <= 0:
            continue
        rr_val = reward / risk
        if rr_val < W3_MIN_RR:
            continue

        used_w1.add(high_idx)
        pending.append({
            "strategy":      "W3_PENDING",
            "ticker":        ticker,
            "signal_date":   df.index[w2_idx].strftime("%Y-%m-%d"),
            "current_price": round(current_price, 2),
            "trigger":       round(trigger, 2),
            "proximity_pct": round(proximity_pct, 1),
            "entry":         round(trigger, 2),
            "stop":          round(stop_price, 2),
            "target":        round(target_price, 2),
            "risk_pct":      round(risk / trigger * 100, 2),
            "reward_pct":    round(reward / trigger * 100, 2),
            "rr":            round(reward / risk, 2),
            "rsi_at_w2":     round(rsi_at_w2, 1),
            "rsi_at_entry":  0.0,
            "w1_pct":        round(w1_size / w0_low * 100, 1),
            "w2_retrace":    round((w1_high - w2_price) / w1_size * 100, 1),
        })

    return pending


# ── TRADE CARD PRINTER ───────────────────────────────────────────────────────

def print_trade_card(s, rank):
    is_pending = s["strategy"] == "W3_PENDING"
    strategy_label = {
        "W3_SCALPER": "⚡ W3 Scalper",
        "DAILY_V11":  "📊 Daily v11",
        "W3_PENDING": "👀 W3 Watch",
    }.get(s["strategy"], s["strategy"])

    rr_label = "🟢" if s["rr"] >= 2.0 else "🔶" if s["rr"] >= 1.5 else "🔴"

    print(f"\n  ┌─ #{rank} {strategy_label} — {s['ticker']} ─────────────────────────────")
    if is_pending:
        print(f"  │  ⚠️  PENDING — breakout not yet confirmed")
        print(f"  │  W2 date     : {s['signal_date']}  (structure active)")
        print(f"  │  Now trading : ${s['current_price']:.2f}  →  trigger at ${s['trigger']:.2f}  ({s['proximity_pct']:.1f}% away)")
        print(f"  │  ACTION      : Watch for close above ${s['trigger']:.2f} Monday")
    else:
        print(f"  │  Signal date : {s['signal_date']}")
        print(f"  │  Entry       : ${s['entry']:.2f}  (buy at market open next session)")
    print(f"  │  Stop        : ${s['stop']:.2f}  ({s['risk_pct']:.1f}% risk from entry)")
    print(f"  │  Target T1   : ${s['target']:.2f}  ({s['reward_pct']:.1f}% reward)")
    print(f"  │  R:R         : {rr_label} {s['rr']:.2f}:1")
    print(f"  │  W1 size     : {s['w1_pct']:.1f}%  |  W2 retrace: {s['w2_retrace']:.1f}%")
    print(f"  │  RSI @ W2    : {s['rsi_at_w2']}")
    d_earn = s.get("days_to_earnings")
    if d_earn is None or (isinstance(d_earn, float) and pd.isna(d_earn)):
        print(f"  │  Earnings    : ⚠️  UNKNOWN — calendar stale, run `python events.py` before trading")
    elif s.get("earnings_veto"):
        print(f"  │  Earnings    : 🚫 in {int(d_earn)}d — VETOED (no entry ≤{EARNINGS_VETO_DAYS}d before earnings)")
    elif d_earn <= EARNINGS_VETO_DAYS:
        print(f"  │  Earnings    : ⚠️  in {int(d_earn)}d — inside veto window but W3 is exempt (gaps power breakouts)")
    else:
        print(f"  │  Earnings    : {int(d_earn)}d away — clear")
    print(f"  │  Position    : 10% of portfolio  |  Max loss: {s['risk_pct']*0.10:.2f}% of portfolio")
    print(f"  └────────────────────────────────────────────────────────────")


# ── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    today       = datetime.today()
    cutoff      = pd.Timestamp(today - timedelta(days=LOOKBACK_DAYS))
    today_str   = today.strftime("%Y-%m-%d")

    print(f"\n{'='*62}")
    print(f"  APEX LIVE SCANNER  |  {today_str}  |  lookback: {LOOKBACK_DAYS} days")
    print(f"{'='*62}")

    # Refresh all data
    print("\n📡 Refreshing market data...")
    for ticker in TICKERS + [REGIME_TICKER]:
        try:
            refresh_data(ticker)
            print(f"  ✅ {ticker}")
        except Exception as e:
            print(f"  ❌ {ticker}: {e}")

    # Earnings calendar — warn loudly if stale for any scanned ticker
    earnings_cal = load_earnings_calendar()
    stale = [t for t in TICKERS if calendar_is_stale(earnings_cal, t, today)]
    if stale:
        print(f"\n⚠️  Earnings calendar STALE for {len(stale)} tickers ({', '.join(stale[:8])}"
              f"{'…' if len(stale) > 8 else ''}) — run `python events.py` to refresh before trading.")

    # Load regime
    qqq = load_data(REGIME_TICKER)
    qqq["ma"] = qqq["Close"].rolling(REGIME_MA).mean()
    regime     = qqq["Close"] > qqq["ma"]
    regime_on  = bool(regime.iloc[-1])
    print(f"\n📈 QQQ MA{REGIME_MA} regime: {'🟢 BULLISH' if regime_on else '🔴 BEARISH'}")
    print(f"   QQQ close: ${qqq['Close'].iloc[-1]:.2f}  |  MA50: ${qqq['ma'].iloc[-1]:.2f}")

    all_signals = []

    print(f"\n🔍 Scanning {len(TICKERS)} tickers for setups in last {LOOKBACK_DAYS} days...\n")

    for ticker in TICKERS:
        try:
            df = load_data(ticker)
            df = add_indicators(df)
            regime_aligned = regime.reindex(df.index, method="ffill").fillna(False)

            w3_sigs      = scan_w3_live(df, ticker, regime_aligned, cutoff)
            d_sigs       = scan_daily_live(df, ticker, regime_aligned, cutoff)
            pending_sigs = scan_pending_w3(df, ticker, regime_aligned)

            for s in w3_sigs + d_sigs + pending_sigs:
                # Earnings awareness: attach days-to-earnings; veto Daily entries
                # inside the pre-earnings window (W3 is exempt — data-driven).
                d_earn = days_to_next_earnings(ticker, today, earnings_cal)
                s["days_to_earnings"] = d_earn
                s["earnings_veto"]    = (s["strategy"] == "DAILY_V11"
                                         and d_earn is not None
                                         and d_earn <= EARNINGS_VETO_DAYS)
                all_signals.append(s)
                veto_tag = "  🚫 EARNINGS VETO" if s["earnings_veto"] else ""
                if s["strategy"] == "W3_PENDING":
                    print(f"  👀 {s['strategy']:12s} {ticker:6s} — W2 date {s['signal_date']}  {s['proximity_pct']:.1f}% from trigger  R:R {s['rr']:.1f}{veto_tag}")
                else:
                    print(f"  🎯 {s['strategy']:12s} {ticker:6s} — signal {s['signal_date']}  R:R {s['rr']:.1f}  entry ${s['entry']}{veto_tag}")

        except Exception as e:
            print(f"  ❌ {ticker}: {e}")

    print(f"\n{'='*62}")

    if not all_signals:
        print("\n  No fresh signals in the last 10 days and no pending setups within 6% of trigger.")
        print("  Regime is active — setups will form. Check again tomorrow.")
    else:
        df_sig = pd.DataFrame(all_signals)

        confirmed = df_sig[df_sig["strategy"] != "W3_PENDING"].sort_values(
            ["rr", "signal_date"], ascending=[False, False])
        watchlist = df_sig[df_sig["strategy"] == "W3_PENDING"].sort_values(
            "proximity_pct", ascending=True)

        if not confirmed.empty:
            print(f"\n  ── CONFIRMED SIGNALS ({len(confirmed)}) — entry at open Monday ──\n")
            for rank, (_, row) in enumerate(confirmed.iterrows(), 1):
                print_trade_card(row, rank)
        else:
            print("\n  No confirmed signals in the last 10 days.")

        if not watchlist.empty:
            print(f"\n  ── MONDAY WATCHLIST ({len(watchlist)}) — pending breakout ──\n")
            for rank, (_, row) in enumerate(watchlist.iterrows(), 1):
                print_trade_card(row, rank)

        # Save all to signals dir
        os.makedirs(SIGNALS_DIR, exist_ok=True)
        out_path = f"{SIGNALS_DIR}/signals_{today_str}.csv"
        df_sig.to_csv(out_path, index=False)
        print(f"\n  💾 Saved to {out_path}")

    print(f"\n{'='*62}\n")
