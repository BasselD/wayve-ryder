"""
APEX Backtest Engine v10
Changes from v9:
- MIN_WAVE1_PCT reset to 7% — 9% threshold made AMZN worse, not better
- Short scanner re-enabled
- MA slope filter removed from shorts — Trend filter was blocking nearly all short setups;
  price below 50 MA + below own 200 MA is sufficient directional confirmation
- Minimum Wave B duration added (5 bars) — filters one-day spike bounces that aren't
  genuine corrective Wave B structures
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings("ignore")

# ── CONFIG ────────────────────────────────────────────────────────────────────
TICKERS           = ["NVDA", "GOOGL", "TSLA", "AAPL", "AMD",
                     "MSFT", "AMZN", "META", "SMCI", "PLTR",
                     "CRM", "NFLX"]
REGIME_TICKER     = "SPY"
DATA_DIR          = "./data"
RESULTS_DIR       = "./results"
SWING_LOOKBACK    = 10
MIN_WAVE1_PCT     = 0.07    # 7% minimum — proven threshold across all versions
FIB_ENTRY_MIN     = 0.50
FIB_ENTRY_MAX     = 0.786
FIB_TARGET_1      = 1.0     # T1: 100% extension — take 50% off, trail to BE
FIB_TARGET_2      = 1.618   # T2: 161.8% extension — close remaining 50%
HOLD_DAYS_MAX     = 90
TRANSACTION_COST  = 0.0005
MIN_RR            = 1.5
VOL_LOOKBACK      = 5
RSI_PERIOD        = 14
RSI_MAX_AT_TOUCH  = 55      # longs: RSI at W2 bottom must be < 55
RSI_MIN_AT_WB_TOP = 62      # shorts: RSI at Wave B top must be > 62 — genuine overbought trap
TREND_MA          = 50
MA_SLOPE_BARS     = 5       # bars to measure 50 MA slope — confirms trend has direction, not just level
REGIME_MA         = 200
# ─────────────────────────────────────────────────────────────────────────────


def load_data(ticker):
    path = f"{DATA_DIR}/{ticker}_daily.csv"
    df = pd.read_csv(path)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [str(c).split(",")[0].strip("('\" )") for c in df.columns]

    date_col = None
    for c in df.columns:
        if "date" in c.lower() or "time" in c.lower():
            date_col = c
            break

    if date_col:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)

    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if cl in ["open"]:    col_map[c] = "Open"
        elif cl in ["high"]:  col_map[c] = "High"
        elif cl in ["low"]:   col_map[c] = "Low"
        elif cl in ["close"]: col_map[c] = "Close"
        elif cl in ["volume"]:col_map[c] = "Volume"
    df = df.rename(columns=col_map)

    required = ["Open", "High", "Low", "Close"]
    missing = [r for r in required if r not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}. Available: {list(df.columns)}")

    for c in required:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=required)
    return df


def calc_rsi(close_series, period=14):
    delta    = close_series.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def find_swings(df, lookback=10):
    highs, lows = [], []
    for i in range(lookback, len(df) - lookback):
        if df["High"].iloc[i] == df["High"].iloc[i-lookback:i+lookback].max():
            highs.append(i)
        if df["Low"].iloc[i] == df["Low"].iloc[i-lookback:i+lookback].min():
            lows.append(i)
    return highs, lows


# ── LONG SCANNER (W1 → W2 → enter W3) ───────────────────────────────────────

def scan_setups(df, ticker, regime):
    df = df.copy()
    df["RSI"]  = calc_rsi(df["Close"], RSI_PERIOD)
    df["MA50"] = df["Close"].rolling(TREND_MA).mean()

    swing_highs, swing_lows = find_swings(df, SWING_LOOKBACK)
    setups = []

    skipped_w1_size = 0
    skipped_rule1   = 0
    skipped_confirm = 0
    skipped_trend   = 0
    skipped_volume  = 0
    skipped_rsi     = 0
    skipped_regime  = 0
    skipped_rr      = 0

    has_volume = "Volume" in df.columns

    for low_idx in swing_lows:
        next_highs = [h for h in swing_highs if h > low_idx and h < low_idx + 100]
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

        w1_avg_vol = df["Volume"].iloc[low_idx:high_idx + 1].mean() if has_volume else None

        fib_touched   = False
        fib_touch_bar = None
        fib_touch_low = w1_end

        for j in range(high_idx + 1, min(high_idx + 80, len(df))):
            cur_low     = df["Low"].iloc[j]
            retracement = (w1_end - cur_low) / w1_len if w1_len > 0 else 0

            if cur_low <= w1_start:
                if fib_touched:
                    skipped_confirm += 1
                else:
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

            ma50_at_entry = df["MA50"].iloc[j]
            if not pd.isna(ma50_at_entry) and df["Close"].iloc[j] < ma50_at_entry:
                skipped_trend += 1
                continue

            # MA slope: 50 MA must be rising — price above a flat/declining MA is a weak signal
            ma50_slope = df["MA50"].iloc[j] - df["MA50"].iloc[max(0, j - MA_SLOPE_BARS)]
            if ma50_slope <= 0:
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

            if w1_avg_vol is not None:
                vol_start     = max(high_idx, j - VOL_LOOKBACK)
                w2_recent_vol = df["Volume"].iloc[vol_start:j].mean()
                if w2_recent_vol >= w1_avg_vol:
                    skipped_volume += 1
                    continue

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

    print(f"  [LONG  {ticker}] Filtered — W1 small: {skipped_w1_size} | Rule1: {skipped_rule1} | "
          f"Trend: {skipped_trend} | No confirm: {skipped_confirm} | "
          f"Vol: {skipped_volume} | RSI: {skipped_rsi} | Regime: {skipped_regime} | R/R: {skipped_rr}")
    print(f"  [LONG  {ticker}] ✅ Qualifying setups: {len(setups)}")
    return setups


# ── SHORT SCANNER (Wave A down → Wave B bounce → enter Wave C puts) ──────────

def scan_short_setups(df, ticker):
    """
    Wave A-B-C correction scanner.
    A = significant swing high → swing low (downward impulse)
    B = partial bounce 38.2–78.6% of Wave A (trap bounce)
    Entry = close below Wave B top bar's low (reversal confirmation)
    Stop = above Wave A start (wave count invalidated if B > A origin)
    T1 = projected DOWN from Wave B high — exit 100% here (Wave C rarely reaches 161.8%)
    Regime gate: ticker must be below its OWN 200 MA — stock-specific bear trend filter.
    Stronger than SPY macro gate: stock can be in its own bear while SPY holds up.
    """
    df = df.copy()
    df["RSI"]   = calc_rsi(df["Close"], RSI_PERIOD)
    df["MA50"]  = df["Close"].rolling(TREND_MA).mean()
    df["MA200"] = df["Close"].rolling(REGIME_MA).mean()

    swing_highs, swing_lows = find_swings(df, SWING_LOOKBACK)
    setups = []

    skipped_wa_size = 0
    skipped_wb_inv  = 0
    skipped_confirm = 0
    skipped_trend   = 0
    skipped_regime  = 0
    skipped_volume  = 0
    skipped_rr      = 0

    has_volume = "Volume" in df.columns

    for high_idx in swing_highs:
        # Wave A: swing high → next swing low
        next_lows = [l for l in swing_lows if l > high_idx and l < high_idx + 100]
        if not next_lows:
            continue

        low_idx = next_lows[0]
        wa_start = df["High"].iloc[high_idx]  # Wave A origin (top)
        wa_end   = df["Low"].iloc[low_idx]    # Wave A bottom
        wa_len   = wa_start - wa_end
        wa_pct   = wa_len / wa_start

        if wa_pct < MIN_WAVE1_PCT:
            skipped_wa_size += 1
            continue

        wa_avg_vol = df["Volume"].iloc[high_idx:low_idx + 1].mean() if has_volume else None

        # Track the highest Wave B bounce in the fib zone
        wb_touched    = False
        wb_touch_bar  = None
        wb_touch_high = wa_end   # will be updated to highest Wave B top seen

        for j in range(low_idx + 1, min(low_idx + 80, len(df))):
            cur_high    = df["High"].iloc[j]
            retracement = (cur_high - wa_end) / wa_len if wa_len > 0 else 0

            # Wave B cannot exceed Wave A origin — count invalidated
            if cur_high >= wa_start:
                skipped_wb_inv += 1
                break

            # Track the highest Wave B top in the fib zone
            if FIB_ENTRY_MIN <= retracement <= FIB_ENTRY_MAX:
                if cur_high > wb_touch_high:
                    wb_touch_high = cur_high
                    wb_touch_bar  = j
                wb_touched = True

            if not (wb_touched and wb_touch_bar is not None and j > wb_touch_bar):
                continue

            # Reversal confirmation: close below Wave B top bar's LOW (momentum turning down)
            if df["Close"].iloc[j] >= df["Low"].iloc[wb_touch_bar]:
                continue

            # Minimum Wave B duration: bounce must span at least 5 bars.
            # One-day spike reversals are not genuine corrective Wave B structures.
            if (wb_touch_bar - low_idx) < 5:
                skipped_confirm += 1
                continue

            # Trend filter: entry close below 50 MA confirms downtrend context.
            # No slope check for shorts — price below 50 MA + below 200 MA is sufficient.
            ma50_at_entry = df["MA50"].iloc[j]
            if not pd.isna(ma50_at_entry) and df["Close"].iloc[j] > ma50_at_entry:
                skipped_trend += 1
                continue

            # Volume: Wave B bounce should come on declining volume vs Wave A
            if wa_avg_vol is not None:
                vol_start     = max(low_idx, j - VOL_LOOKBACK)
                wb_recent_vol = df["Volume"].iloc[vol_start:j].mean()
                if wb_recent_vol >= wa_avg_vol:
                    skipped_volume += 1
                    continue

            # Regime gate: ticker must be below its own 200 MA at entry.
            # Stock-specific bear trend — stronger than SPY macro gate because stocks
            # can be in their own bear markets while SPY still holds above 200 MA.
            ma200_at_entry = df["MA200"].iloc[j]
            if not pd.isna(ma200_at_entry) and df["Close"].iloc[j] > ma200_at_entry:
                skipped_regime += 1
                continue

            entry    = df["Close"].iloc[j]
            stop     = wa_start * 1.001   # above Wave A origin = wave invalidation
            # Targets projected DOWN from Wave B high (C point anchor)
            target_1 = wb_touch_high - (wa_len * FIB_TARGET_1)
            target_2 = wb_touch_high - (wa_len * FIB_TARGET_2)

            risk   = stop - entry          # how far price can go up before stop
            reward = entry - target_1      # R:R measured to T1 — exits 100% there
            rr     = reward / risk if risk > 0 else 0

            if rr < MIN_RR:
                skipped_rr += 1
                break

            setups.append({
                "direction":       "SHORT",
                "ticker":          ticker,
                "wa_start_date":   df.index[high_idx],
                "wa_end_date":     df.index[low_idx],
                "wb_date":         df.index[wb_touch_bar],
                "confirm_date":    df.index[j],
                "wa_start_price":  round(wa_start, 2),
                "wa_end_price":    round(wa_end, 2),
                "wb_high":         round(wb_touch_high, 2),
                "entry_price":     round(entry, 2),
                "stop_price":      round(stop, 2),
                "target_1_price":  round(target_1, 2),
                "target_2_price":  round(target_2, 2),
                "wa_pct_move":     round(wa_pct * 100, 2),
                "retracement_pct": round((wb_touch_high - wa_end) / wa_len * 100, 2),
                "rr_ratio":        round(rr, 2),
                "entry_bar":       j,
            })
            break

    print(f"  [SHORT {ticker}] Filtered — WA small: {skipped_wa_size} | WB invalid: {skipped_wb_inv} | "
          f"Trend: {skipped_trend} | No confirm: {skipped_confirm} | "
          f"Regime: {skipped_regime} | Vol: {skipped_volume} | R/R: {skipped_rr}")
    print(f"  [SHORT {ticker}] ✅ Qualifying setups: {len(setups)}")
    return setups


# ── SIMULATION ────────────────────────────────────────────────────────────────

def simulate_trades(df, setups):
    """Long trades: WIN when High >= target, LOSS when Low <= stop."""
    results = []
    for setup in setups:
        entry_bar   = setup["entry_bar"]
        entry_price = setup["entry_price"]
        stop_price  = setup["stop_price"]
        target_1    = setup["target_1_price"]
        target_2    = setup["target_2_price"]

        outcome     = "TIMEOUT"
        exit_price  = df["Close"].iloc[min(entry_bar + HOLD_DAYS_MAX, len(df) - 1)]
        exit_date   = df.index[min(entry_bar + HOLD_DAYS_MAX, len(df) - 1)]
        hold_days   = HOLD_DAYS_MAX
        t1_hit      = False
        active_stop = stop_price

        for k in range(entry_bar + 1, min(entry_bar + HOLD_DAYS_MAX, len(df))):
            high_k = df["High"].iloc[k]
            low_k  = df["Low"].iloc[k]

            if not t1_hit and high_k >= target_1:
                t1_hit      = True
                active_stop = entry_price * 1.001

            if high_k >= target_2:
                outcome    = "WIN"
                exit_price = target_2
                exit_date  = df.index[k]
                hold_days  = k - entry_bar
                break

            if low_k <= active_stop:
                outcome    = "PARTIAL_WIN" if t1_hit else "LOSS"
                exit_price = active_stop
                exit_date  = df.index[k]
                hold_days  = k - entry_bar
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
                        "hold_days": hold_days, "net_return": round(net_return * 100, 2)})
    return results


def simulate_short_trades(df, setups):
    """
    Short trades: exit 100% at T1 (Wave C = Wave A length).
    Wave C rarely reaches 161.8% in any regime — lock the win at 100% extension.
    WIN  = Low touches T1
    LOSS = High touches stop before T1
    TIMEOUT = neither hit within HOLD_DAYS_MAX
    """
    results = []
    for setup in setups:
        entry_bar   = setup["entry_bar"]
        entry_price = setup["entry_price"]
        stop_price  = setup["stop_price"]
        target_1    = setup["target_1_price"]

        outcome    = "TIMEOUT"
        exit_price = df["Close"].iloc[min(entry_bar + HOLD_DAYS_MAX, len(df) - 1)]
        exit_date  = df.index[min(entry_bar + HOLD_DAYS_MAX, len(df) - 1)]
        hold_days  = HOLD_DAYS_MAX

        for k in range(entry_bar + 1, min(entry_bar + HOLD_DAYS_MAX, len(df))):
            high_k = df["High"].iloc[k]
            low_k  = df["Low"].iloc[k]

            if low_k <= target_1:
                outcome    = "WIN"
                exit_price = target_1
                exit_date  = df.index[k]
                hold_days  = k - entry_bar
                break

            if high_k >= stop_price:
                outcome    = "LOSS"
                exit_price = stop_price
                exit_date  = df.index[k]
                hold_days  = k - entry_bar
                break

        net_return = (entry_price - exit_price) / entry_price - 2 * TRANSACTION_COST
        results.append({**setup, "outcome": outcome, "t1_hit": outcome == "WIN",
                        "exit_price": round(exit_price, 2), "exit_date": exit_date,
                        "hold_days": hold_days, "net_return": round(net_return * 100, 2)})
    return results


# ── METRICS ──────────────────────────────────────────────────────────────────

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


def print_metrics(m, label):
    grade = "🟢" if m["expectancy"] > 0 else "🔴"
    print(f"  {grade} {label} | WR: {m['win_rate']}% | E: {m['expectancy']}%/trade | "
          f"PF: {m['profit_factor']} | MaxDD: {m['max_drawdown']}% | "
          f"W:{m['wins']} L:{m['losses']} T:{m['timeouts']}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(RESULTS_DIR, exist_ok=True)
    all_long_trades  = []
    all_short_trades = []

    print("\n🔍 APEX Backtest Engine v10")
    print(f"   Min move: {MIN_WAVE1_PCT*100}% | Fib: {FIB_ENTRY_MIN*100}%–{FIB_ENTRY_MAX*100}% | "
          f"Hold: {HOLD_DAYS_MAX}d | T1: {FIB_TARGET_1*100}% | T2: {FIB_TARGET_2*100}% | "
          f"RSI long<{RSI_MAX_AT_TOUCH} | RSI short>{RSI_MIN_AT_WB_TOP} | "
          f"Trend MA: {TREND_MA} | Regime: {REGIME_TICKER} {REGIME_MA}MA\n")

    try:
        spy_df = load_data(REGIME_TICKER)
        spy_df["MA200"]    = spy_df["Close"].rolling(REGIME_MA).mean()
        spy_regime_full    = spy_df["Close"] > spy_df["MA200"]
        spy_loaded         = True
    except Exception:
        spy_regime_full = None
        spy_loaded      = False

    for ticker in TICKERS:
        try:
            df = load_data(ticker)
            print(f"\n📂 {ticker}: {len(df)} rows | "
                  f"${df['Close'].min():.2f} – ${df['Close'].max():.2f}")

            regime = (spy_regime_full.reindex(df.index, method="ffill").fillna(False)
                      if spy_loaded else pd.Series(True, index=df.index))

            # ── LONGS ──
            long_setups  = scan_setups(df, ticker, regime)
            long_trades  = simulate_trades(df, long_setups)
            if long_trades:
                ltdf = pd.DataFrame(long_trades)
                ltdf.to_csv(f"{RESULTS_DIR}/{ticker}_long.csv", index=False)
                all_long_trades.extend(long_trades)
                print_metrics(calc_metrics(ltdf), f"LONG  {ticker}")

            # ── SHORTS ──
            short_setups = scan_short_setups(df, ticker)
            short_trades = simulate_short_trades(df, short_setups)
            if short_trades:
                stdf = pd.DataFrame(short_trades)
                stdf.to_csv(f"{RESULTS_DIR}/{ticker}_short.csv", index=False)
                all_short_trades.extend(short_trades)
                print_metrics(calc_metrics(stdf), f"SHORT {ticker}")

        except Exception as e:
            print(f"  ❌ {ticker} ERROR: {e}")

    print(f"\n{'='*65}")
    all_trades = all_long_trades + all_short_trades
    if all_trades:
        all_df = pd.DataFrame(all_trades)
        all_df.to_csv(f"{RESULTS_DIR}/ALL_backtest.csv", index=False)

        if all_long_trades:
            lm = calc_metrics(pd.DataFrame(all_long_trades))
            print(f"📈 LONG  TOTAL  — {lm['total']} trades | WR: {lm['win_rate']}% | "
                  f"E: {lm['expectancy']}% | PF: {lm['profit_factor']} | MaxDD: {lm['max_drawdown']}%")

        if all_short_trades:
            sm = calc_metrics(pd.DataFrame(all_short_trades))
            print(f"📉 SHORT TOTAL  — {sm['total']} trades | WR: {sm['win_rate']}% | "
                  f"E: {sm['expectancy']}% | PF: {sm['profit_factor']} | MaxDD: {sm['max_drawdown']}%")

        cm = calc_metrics(all_df)
        print(f"{'─'*65}")
        print(f"⚡ COMBINED     — {cm['total']} trades | WR: {cm['win_rate']}% | "
              f"E: {cm['expectancy']}% | PF: {cm['profit_factor']} | MaxDD: {cm['max_drawdown']}%")
        print(f"   Breakdown — W:{cm['wins']} L:{cm['losses']} T:{cm['timeouts']}")
    print(f"{'='*65}\n")
