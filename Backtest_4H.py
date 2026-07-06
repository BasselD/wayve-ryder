"""
APEX Backtest Engine — 4H Timeframe
Runs the same Elliott Wave + Fib strategy on 4-hour bars resampled from 1H data.
Targets weekly options (7-21 DTE). Hold window ~17 trading days.
Daily system (Backtest.py) is untouched — this runs in parallel.
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings("ignore")

# ── CONFIG ────────────────────────────────────────────────────────────────────
TICKERS          = ["NVDA", "GOOGL", "TSLA", "AAPL", "AMD",
                    "MSFT", "AMZN", "META", "SMCI", "PLTR",
                    "CRM", "NFLX"]
REGIME_TICKER    = "QQQ"
DATA_DIR         = "./data"
RESULTS_DIR      = "./results/4h"
SWING_LOOKBACK   = 10      # 10 × 4H = 40 hrs ≈ 5 trading days — same ratio as daily
MIN_WAVE1_PCT    = 0.07    # 7% — consistent with daily; filters single-session noise spikes
FIB_ENTRY_MIN    = 0.50
FIB_ENTRY_MAX    = 0.786
FIB_TARGET_1     = 1.0
FIB_TARGET_2     = 1.618
HOLD_BARS_MAX    = 80      # 80 × 4H ≈ 40 trading days — reduces timeouts on slower wave completions
TRANSACTION_COST = 0.0005
MIN_RR           = 1.5     # same as daily — 4H R:R is tighter, don't over-restrict
VOL_LOOKBACK     = 8
RSI_PERIOD       = 14
RSI_MAX_AT_TOUCH = 55
TREND_MA         = 50
REGIME_MA        = 200
MA_SLOPE_BARS    = 8
# ─────────────────────────────────────────────────────────────────────────────


def load_and_resample(ticker):
    """Load 1H CSV and resample to 4H bars."""
    path = f"{DATA_DIR}/{ticker}_1h.csv"
    df = pd.read_csv(path)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [str(c).split(",")[0].strip("('\" )") for c in df.columns]

    date_col = None
    for c in df.columns:
        if "date" in c.lower() or "time" in c.lower() or "datetime" in c.lower():
            date_col = c
            break

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], utc=True)
        df[date_col] = df[date_col].dt.tz_localize(None)
        df = df.set_index(date_col)

    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if cl == "open":    col_map[c] = "Open"
        elif cl == "high":  col_map[c] = "High"
        elif cl == "low":   col_map[c] = "Low"
        elif cl == "close": col_map[c] = "Close"
        elif cl == "volume":col_map[c] = "Volume"
    df = df.rename(columns=col_map)

    required = ["Open", "High", "Low", "Close"]
    for c in required:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=required)

    # Resample to 4H
    df_4h = df.resample("4h").agg({
        "Open":   "first",
        "High":   "max",
        "Low":    "min",
        "Close":  "last",
        "Volume": "sum",
    }).dropna(subset=["Open", "High", "Low", "Close"])

    # Drop incomplete bars at market open/close edges
    df_4h = df_4h[df_4h["Volume"] > 0]
    return df_4h


def calc_rsi(close_series, period=14):
    delta    = close_series.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def find_swings(df, lookback):
    highs, lows = [], []
    for i in range(lookback, len(df) - lookback):
        if df["High"].iloc[i] == df["High"].iloc[i-lookback:i+lookback].max():
            highs.append(i)
        if df["Low"].iloc[i] == df["Low"].iloc[i-lookback:i+lookback].min():
            lows.append(i)
    return highs, lows


def scan_setups(df, ticker, regime):
    df = df.copy()
    df["RSI"]  = calc_rsi(df["Close"], RSI_PERIOD)
    df["MA50"] = df["Close"].rolling(TREND_MA).mean()

    swing_highs, swing_lows = find_swings(df, SWING_LOOKBACK)
    setups = []

    skipped_w1_size = skipped_rule1 = skipped_confirm = 0
    skipped_trend   = skipped_volume = skipped_rsi = 0
    skipped_regime  = skipped_rr = 0

    for low_idx in swing_lows:
        next_highs = [h for h in swing_highs if h > low_idx and h < low_idx + 80]
        if not next_highs:
            continue

        high_idx = next_highs[0]
        w1_start = df["Low"].iloc[low_idx]
        w1_end   = df["High"].iloc[high_idx]
        w1_len   = w1_end - w1_start
        w1_pct   = w1_len / w1_start

        if w1_pct < MIN_WAVE1_PCT:
            skipped_w1_size += 1
            continue

        fib_touched   = False
        fib_touch_bar = None
        fib_touch_low = w1_end

        for j in range(high_idx + 1, min(high_idx + 60, len(df))):
            cur_low     = df["Low"].iloc[j]
            retracement = (w1_end - cur_low) / w1_len if w1_len > 0 else 0

            if cur_low <= w1_start:
                skipped_confirm += 1 if fib_touched else 0
                if not fib_touched:
                    skipped_rule1 += 1
                break

            if FIB_ENTRY_MIN <= retracement <= FIB_ENTRY_MAX:
                if cur_low < fib_touch_low:
                    fib_touch_low = cur_low
                    fib_touch_bar = j
                fib_touched = True

            if not (fib_touched and fib_touch_bar is not None and j > fib_touch_bar):
                continue

            if df["Close"].iloc[j] <= df["High"].iloc[fib_touch_bar]:
                continue

            # Trend: price must be above 50 MA. No slope check — 4H MA slope is too noisy.
            ma50_at_entry = df["MA50"].iloc[j]
            if not pd.isna(ma50_at_entry) and df["Close"].iloc[j] < ma50_at_entry:
                skipped_trend += 1
                continue

            rsi_at_touch = df["RSI"].iloc[fib_touch_bar]
            if pd.isna(rsi_at_touch) or rsi_at_touch >= RSI_MAX_AT_TOUCH:
                skipped_rsi += 1
                break

            rsi_at_confirm = df["RSI"].iloc[j]
            if pd.isna(rsi_at_confirm) or rsi_at_confirm <= rsi_at_touch:
                skipped_rsi += 1
                continue

            # Volume filter removed on 4H — resampled intraday volume is unreliable.
            # Morning 4H bars carry ~2x the volume of afternoon bars by default,
            # creating systematic bias in W1 vs W2 volume comparisons.

            entry_date = df.index[j]
            if entry_date in regime.index and not regime.loc[entry_date]:
                skipped_regime += 1
                continue

            entry    = df["Close"].iloc[j]
            stop     = w1_start * 0.999
            target_1 = fib_touch_low + (w1_len * FIB_TARGET_1)
            target_2 = fib_touch_low + (w1_len * FIB_TARGET_2)
            risk     = entry - stop
            reward   = target_2 - entry
            rr       = reward / risk if risk > 0 else 0

            if rr < MIN_RR:
                skipped_rr += 1
                break

            setups.append({
                "direction":       "LONG",
                "ticker":          ticker,
                "w1_start_date":   df.index[low_idx],
                "w1_end_date":     df.index[high_idx],
                "w2_date":         df.index[fib_touch_bar],
                "confirm_date":    df.index[j],
                "w1_start_price":  round(w1_start, 2),
                "w1_end_price":    round(w1_end, 2),
                "w2_low":          round(fib_touch_low, 2),
                "entry_price":     round(entry, 2),
                "stop_price":      round(stop, 2),
                "target_1_price":  round(target_1, 2),
                "target_2_price":  round(target_2, 2),
                "w1_pct_move":     round(w1_pct * 100, 2),
                "retracement_pct": round((w1_end - fib_touch_low) / w1_len * 100, 2),
                "rsi_at_touch":    round(rsi_at_touch, 1),
                "rsi_at_confirm":  round(rsi_at_confirm, 1),
                "rr_ratio":        round(rr, 2),
                "entry_bar":       j,
            })
            break

    print(f"  [4H LONG {ticker}] Filtered — W1 small: {skipped_w1_size} | Rule1: {skipped_rule1} | "
          f"Trend: {skipped_trend} | No confirm: {skipped_confirm} | "
          f"Vol: {skipped_volume} | RSI: {skipped_rsi} | Regime: {skipped_regime} | R/R: {skipped_rr}")
    print(f"  [4H LONG {ticker}] ✅ Qualifying setups: {len(setups)}")
    return setups


def simulate_trades(df, setups):
    results = []
    for setup in setups:
        entry_bar   = setup["entry_bar"]
        entry_price = setup["entry_price"]
        stop_price  = setup["stop_price"]
        target_1    = setup["target_1_price"]
        target_2    = setup["target_2_price"]

        outcome     = "TIMEOUT"
        exit_price  = df["Close"].iloc[min(entry_bar + HOLD_BARS_MAX, len(df) - 1)]
        exit_date   = df.index[min(entry_bar + HOLD_BARS_MAX, len(df) - 1)]
        hold_bars   = HOLD_BARS_MAX
        t1_hit      = False
        active_stop = stop_price

        for k in range(entry_bar + 1, min(entry_bar + HOLD_BARS_MAX, len(df))):
            high_k = df["High"].iloc[k]
            low_k  = df["Low"].iloc[k]

            if not t1_hit and high_k >= target_1:
                t1_hit      = True
                active_stop = entry_price * 1.001

            if high_k >= target_2:
                outcome    = "WIN"
                exit_price = target_2
                exit_date  = df.index[k]
                hold_bars  = k - entry_bar
                break

            if low_k <= active_stop:
                outcome    = "PARTIAL_WIN" if t1_hit else "LOSS"
                exit_price = active_stop
                exit_date  = df.index[k]
                hold_bars  = k - entry_bar
                break

        if outcome == "WIN":
            r1 = (target_1 - entry_price) / entry_price
            r2 = (target_2 - entry_price) / entry_price
            net_return = (0.5 * r1 + 0.5 * r2) - 2 * TRANSACTION_COST
        elif outcome == "PARTIAL_WIN":
            r1 = (target_1 - entry_price) / entry_price
            net_return = (0.5 * r1) - 2 * TRANSACTION_COST
        else:
            net_return = (exit_price - entry_price) / entry_price - 2 * TRANSACTION_COST

        results.append({**setup, "outcome": outcome, "t1_hit": t1_hit,
                        "exit_price": round(exit_price, 2), "exit_date": exit_date,
                        "hold_bars": hold_bars, "net_return": round(net_return * 100, 2)})
    return results


def calc_metrics(trades):
    if len(trades) == 0:
        return None
    positive = trades[trades["outcome"].isin(["WIN", "PARTIAL_WIN"])]
    losses   = trades[trades["outcome"] == "LOSS"]
    timeouts = trades[trades["outcome"] == "TIMEOUT"]

    win_rate   = len(positive) / len(trades) * 100
    avg_win    = positive["net_return"].mean() if len(positive) > 0 else 0
    avg_loss   = losses["net_return"].mean()   if len(losses) > 0 else 0
    expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)

    gross_wins   = positive["net_return"].sum() if len(positive) > 0 else 0
    gross_losses = abs(losses["net_return"].sum()) if len(losses) > 0 else 0.0001
    pf = gross_wins / gross_losses

    cum    = (1 + trades["net_return"] / 100).cumprod()
    max_dd = ((cum - cum.cummax()) / cum.cummax()).min() * 100

    return {"total": len(trades), "wins": len(positive), "losses": len(losses),
            "timeouts": len(timeouts), "win_rate": round(win_rate, 1),
            "avg_win": round(avg_win, 2), "avg_loss": round(avg_loss, 2),
            "expectancy": round(expectancy, 2), "profit_factor": round(pf, 2),
            "max_drawdown": round(max_dd, 2), "total_return": round(trades["net_return"].sum(), 2)}


if __name__ == "__main__":
    os.makedirs(RESULTS_DIR, exist_ok=True)
    all_trades = []

    print("\n🔍 APEX Backtest Engine — 4H Timeframe")
    print(f"   Swing lookback: {SWING_LOOKBACK} bars | Min W1: {MIN_WAVE1_PCT*100}% | "
          f"Fib: {FIB_ENTRY_MIN*100}%–{FIB_ENTRY_MAX*100}% | "
          f"Hold: {HOLD_BARS_MAX} bars (~{round(HOLD_BARS_MAX*4/6.5)} trading days) | "
          f"T1: {FIB_TARGET_1*100}% | T2: {FIB_TARGET_2*100}% | "
          f"RSI<{RSI_MAX_AT_TOUCH} | Min R/R: {MIN_RR}\n")

    # Load SPY regime
    try:
        spy_4h = load_and_resample(REGIME_TICKER)
        spy_4h["MA200"]    = spy_4h["Close"].rolling(REGIME_MA).mean()
        spy_regime_full    = spy_4h["Close"] > spy_4h["MA200"]
        spy_loaded         = True
    except Exception as e:
        print(f"⚠️  SPY regime load failed: {e} — regime filter disabled")
        spy_regime_full = None
        spy_loaded      = False

    for ticker in TICKERS:
        try:
            df = load_and_resample(ticker)
            print(f"\n📂 {ticker}: {len(df)} 4H bars | "
                  f"${df['Close'].min():.2f} – ${df['Close'].max():.2f}")

            regime = (spy_regime_full.reindex(df.index, method="ffill").fillna(False)
                      if spy_loaded else pd.Series(True, index=df.index))

            setups = scan_setups(df, ticker, regime)
            trades = simulate_trades(df, setups)

            if trades:
                tdf = pd.DataFrame(trades)
                tdf.to_csv(f"{RESULTS_DIR}/{ticker}_4h.csv", index=False)
                all_trades.extend(trades)
                m     = calc_metrics(tdf)
                grade = "🟢" if m["expectancy"] > 0 else "🔴"
                print(f"  {grade} 4H {ticker} | WR: {m['win_rate']}% | "
                      f"E: {m['expectancy']}%/trade | PF: {m['profit_factor']} | "
                      f"MaxDD: {m['max_drawdown']}% | W:{m['wins']} L:{m['losses']} T:{m['timeouts']}")
            else:
                print(f"  ⚠️  No qualifying 4H setups")

        except FileNotFoundError:
            print(f"  ❌ {ticker}: 1H data not found — run Yfinancedata.py first")
        except Exception as e:
            print(f"  ❌ {ticker} ERROR: {e}")

    if all_trades:
        all_df = pd.DataFrame(all_trades)
        all_df.to_csv(f"{RESULTS_DIR}/ALL_4h_backtest.csv", index=False)
        m = calc_metrics(all_df)
        print(f"\n{'='*60}")
        print(f"⚡ 4H COMBINED — {m['total']} trades | WR: {m['win_rate']}% | "
              f"E: {m['expectancy']}% | PF: {m['profit_factor']} | MaxDD: {m['max_drawdown']}%")
        print(f"   Breakdown — W:{m['wins']} L:{m['losses']} T:{m['timeouts']}")
        print(f"{'='*60}\n")
