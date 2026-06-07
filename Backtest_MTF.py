"""
APEX Backtest Engine — Multi-TimeFrame (MTF) Cascade v1

Architecture:
  Daily chart  → validates Wave 1-2 structure (WHERE and WHAT)
  4H chart     → times the entry within the daily Wave 2 zone (WHEN)

Why this outperforms standalone 4H:
  - Daily filters out noisy intraday "waves" (NVDA/TSLA 5% spikes)
  - 4H entry puts you closer to the actual W2 bottom → better R:R
  - Result: daily-quality signals with 4H-precision timing

Flow per ticker:
  1. Daily scanner finds qualifying W2 zones (W1 size, RSI, volume, trend, regime)
  2. For each zone, 4H sub-scanner finds the reversal confirmation
     within the daily W2 price and time bounds
  3. Targets anchored to the 4H W2 low (more precise than daily close)
  4. Simulation on 4H bars, hold up to FH_HOLD_BARS
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings("ignore")

# ── DAILY CONFIG (structure identification) ───────────────────────────────────
TICKERS              = ["NVDA", "GOOGL", "TSLA", "AAPL", "AMD",
                        "MSFT", "AMZN", "META", "SMCI", "PLTR",
                        "CRM", "NFLX",
                        "SHOP", "MU", "DKNG"] 
REGIME_TICKER        = "SPY"
DATA_DIR             = "./data"
RESULTS_DIR          = "./results/mtf"

D_SWING_LOOKBACK     = 10
D_MIN_WAVE1_PCT      = 0.07
D_FIB_ENTRY_MIN      = 0.50
D_FIB_ENTRY_MAX      = 0.786
D_FIB_TARGET_1       = 1.0
D_FIB_TARGET_2       = 1.618
D_RSI_MAX_AT_TOUCH   = 55
D_TREND_MA           = 50
D_REGIME_MA          = 200
D_MA_SLOPE_BARS      = 5
D_VOL_LOOKBACK       = 5

# ── 4H CONFIG (entry timing) ──────────────────────────────────────────────────
FH_HOLD_BARS         = 160     # 160 × 4H bars ≈ 80 trading days (~4 months, matches v7 90-day hold)
FH_RSI_MAX           = 60      # 4H RSI at fib touch — loosened from 55; daily already validated RSI<55
FH_TREND_MA          = 50      # 50 4H bars ≈ 6.5 weeks

# ── SHARED ────────────────────────────────────────────────────────────────────
MIN_RR               = 1.0     # Lowered 1.5→1.0 (v1.2): tested data showed WR 45%→46%,
                               # E +0.02%→+0.30%, drawdown UNCHANGED at -61%. Safe gain.
MAX_RR               = 2.5     # NEW: upper R:R cap. Counterintuitive but data-proven —
                               # absurdly high R:R = stop is structurally too far (loose setup).
                               # Capping R:R lifted WR 37%→50%, PF 1.17→1.46 on the v1 run.
QUALITY_W1_PCT       = 0.25    # NEW: bonus quality flag — W1≥25% impulses had E +3.06%/trade
                               # vs +0.44% baseline. Flagged in output, not hard-filtered, so we
                               # keep all 12 tickers per the universe decision.
TRANSACTION_COST     = 0.0005
# ─────────────────────────────────────────────────────────────────────────────


def load_daily(ticker):
    path = f"{DATA_DIR}/{ticker}_daily.csv"
    df = pd.read_csv(path)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).split(",")[0].strip("('\" )") for c in df.columns]

    date_col = next((c for c in df.columns if "date" in c.lower() or "time" in c.lower()), None)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)

    col_map = {c: {"open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"}
               .get(c.lower().strip(), c) for c in df.columns}
    df = df.rename(columns=col_map)

    for c in ["Open","High","Low","Close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["Open","High","Low","Close"])


def load_4h(ticker):
    """Load 1H data and resample to 4H bars."""
    path = f"{DATA_DIR}/{ticker}_1h.csv"
    df = pd.read_csv(path)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).split(",")[0].strip("('\" )") for c in df.columns]

    date_col = next((c for c in df.columns
                     if "date" in c.lower() or "time" in c.lower() or "datetime" in c.lower()), None)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], utc=True).dt.tz_localize(None)
        df = df.set_index(date_col)

    col_map = {c: {"open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"}
               .get(c.lower().strip(), c) for c in df.columns}
    df = df.rename(columns=col_map)

    for c in ["Open","High","Low","Close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Open","High","Low","Close"])

    df_4h = df.resample("4h").agg(
        {"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}
    ).dropna(subset=["Open","High","Low","Close"])
    return df_4h[df_4h["Volume"] > 0]


def calc_rsi(close_series, period=14):
    delta    = close_series.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
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


# ── STEP 1: Daily zone scanner ────────────────────────────────────────────────

def scan_daily_zones(df_daily, ticker, regime):
    """
    Scan daily chart for qualifying Wave 2 zones.
    Returns zones WITHOUT entry prices — entry timing is delegated to 4H.
    All structural filters (W1 size, RSI, volume, trend, regime) are applied here.
    """
    df = df_daily.copy()
    df["RSI"]  = calc_rsi(df["Close"])
    df["MA50"] = df["Close"].rolling(D_TREND_MA).mean()

    swing_highs, swing_lows = find_swings(df, D_SWING_LOOKBACK)
    zones = []

    skipped_w1   = skipped_rule1 = skipped_trend = 0
    skipped_vol  = skipped_rsi   = skipped_regime = 0

    has_vol = "Volume" in df.columns

    for low_idx in swing_lows:
        next_highs = [h for h in swing_highs if h > low_idx and h < low_idx + 100]
        if not next_highs:
            continue

        high_idx = next_highs[0]
        w1_start = df["Low"].iloc[low_idx]
        w1_end   = df["High"].iloc[high_idx]
        w1_len   = w1_end - w1_start
        w1_pct   = w1_len / w1_start

        if w1_pct < D_MIN_WAVE1_PCT:
            skipped_w1 += 1
            continue

        w1_avg_vol = df["Volume"].iloc[low_idx:high_idx+1].mean() if has_vol else None

        # Daily trend + regime checks at W1 peak
        ma50_at_w1_end = df["MA50"].iloc[high_idx]
        if not pd.isna(ma50_at_w1_end) and w1_end < ma50_at_w1_end:
            skipped_trend += 1
            continue

        # Scan for W2 zone: find the lowest fib touch in the daily retracement
        fib_touched   = False
        fib_touch_bar = None
        fib_touch_low = w1_end

        found_zone = False
        for j in range(high_idx + 1, min(high_idx + 80, len(df))):
            cur_low     = df["Low"].iloc[j]
            retracement = (w1_end - cur_low) / w1_len if w1_len > 0 else 0

            if cur_low <= w1_start:
                skipped_rule1 += 1
                break

            if D_FIB_ENTRY_MIN <= retracement <= D_FIB_ENTRY_MAX:
                if cur_low < fib_touch_low:
                    fib_touch_low = cur_low
                    fib_touch_bar = j
                fib_touched = True

            # Once fib zone has been touched, validate the zone
            if fib_touched and fib_touch_bar is not None:
                # Only validate once per zone (at the fib touch point)
                rsi_at_touch = df["RSI"].iloc[fib_touch_bar]
                if pd.isna(rsi_at_touch) or rsi_at_touch >= D_RSI_MAX_AT_TOUCH:
                    skipped_rsi += 1
                    break

                # Volume: W2 on daily should come on declining volume vs W1
                if w1_avg_vol is not None:
                    vol_start     = max(high_idx, fib_touch_bar - D_VOL_LOOKBACK)
                    w2_recent_vol = df["Volume"].iloc[vol_start:fib_touch_bar+1].mean()
                    if w2_recent_vol >= w1_avg_vol:
                        skipped_vol += 1
                        break

                # Daily MA slope: 50 MA must be rising at W2 touch
                ma50_slope = df["MA50"].iloc[fib_touch_bar] - df["MA50"].iloc[max(0, fib_touch_bar - D_MA_SLOPE_BARS)]
                if ma50_slope <= 0:
                    skipped_trend += 1
                    break

                # Regime: SPY above 200 MA
                entry_date = df.index[fib_touch_bar]
                if entry_date in regime.index and not regime.loc[entry_date]:
                    skipped_regime += 1
                    break

                # Zone validated — pass to 4H for precise entry timing
                w2_window_start = df.index[high_idx]
                w2_window_end   = df.index[min(high_idx + 60, len(df) - 1)]

                zones.append({
                    "ticker":            ticker,
                    "w1_start_date":     df.index[low_idx],
                    "w1_end_date":       df.index[high_idx],
                    "w2_daily_date":     df.index[fib_touch_bar],
                    "w1_start_price":    round(w1_start, 2),
                    "w1_end_price":      round(w1_end, 2),
                    "w1_len":            round(w1_len, 4),
                    "w1_pct_move":       round(w1_pct * 100, 2),
                    "w2_daily_low":      round(fib_touch_low, 2),
                    "daily_retracement": round((w1_end - fib_touch_low) / w1_len * 100, 2),
                    "rsi_at_daily_w2":   round(rsi_at_touch, 1),
                    "stop_price":        round(w1_start * 0.999, 2),
                    "w2_window_start":   w2_window_start,
                    "w2_window_end":     w2_window_end,
                    "fib_zone_low":      round(w1_end - w1_len * D_FIB_ENTRY_MAX, 2),  # 78.6% level
                    "fib_zone_high":     round(w1_end - w1_len * D_FIB_ENTRY_MIN, 2),  # 50% level
                })
                found_zone = True
                break

    print(f"  [MTF-D {ticker}] Filtered — W1 small: {skipped_w1} | Rule1: {skipped_rule1} | "
          f"Trend: {skipped_trend} | Vol: {skipped_vol} | RSI: {skipped_rsi} | Regime: {skipped_regime}")
    print(f"  [MTF-D {ticker}] ✅ Daily zones: {len(zones)}")
    return zones


# ── STEP 2: 4H entry finder ───────────────────────────────────────────────────

def find_4h_entry(zone, df_4h):
    """
    Within the daily W2 time/price window, find a 4H reversal confirmation.

    Fix log (v2):
    - Fib touch now triggers when bar Low PENETRATES the zone from above (Low <= fib_zone_high),
      not just when Low sits inside it — catches bars that wick through the zone floor.
    - Touch tracking resets on each new lower low so confirmation always references the
      deepest touch seen so far, preventing stale-high confirmation off a shallower bar.
    - R:R failure changed from break → continue so deeper confirmation bars in the same
      zone window are still evaluated.
    - 4H MA50 filter removed: at W2 bottom price is structurally below the MA; the daily
      MA50 filter already validates trend health. Re-added after confirmation only if close
      is more than 2% below MA50 (hard structural break, not normal W2 drawdown).
    """
    fib_zone_low  = zone["fib_zone_low"]   # 78.6% level (lower fib bound)
    fib_zone_high = zone["fib_zone_high"]  # 50% level  (upper fib bound)
    w1_start      = zone["w1_start_price"]
    w1_len        = zone["w1_len"]
    stop          = zone["stop_price"]

    start_ts = pd.Timestamp(zone["w2_window_start"]).normalize()
    end_ts   = pd.Timestamp(zone["w2_window_end"]).normalize() + pd.Timedelta(days=1)

    mask       = (df_4h.index >= start_ts) & (df_4h.index < end_ts)
    window_idx = df_4h.index[mask]

    if len(window_idx) < 3:
        return None

    fib_touched   = False
    fib_touch_ts  = None
    fib_touch_low = fib_zone_high  # tracks deepest touch seen

    for ts in window_idx:
        bar     = df_4h.loc[ts]
        cur_low = bar["Low"]

        # EW Rule 1: abort if 4H bar breaks below W1 origin
        if cur_low <= w1_start * 0.999:
            break

        # Fib touch: bar low penetrates INTO or THROUGH the fib zone from above.
        # Condition: low <= fib_zone_high (bar reached the zone) AND
        #            low >= fib_zone_low  (didn't fully blow through it — Rule 1 handles the extreme case)
        if cur_low <= fib_zone_high and cur_low >= fib_zone_low:
            if not fib_touched or cur_low < fib_touch_low:
                # New or deeper touch — reset the confirmation anchor
                fib_touch_low = cur_low
                fib_touch_ts  = ts
            fib_touched = True

        # Confirmation bar: must come AFTER the touch bar
        if not fib_touched or fib_touch_ts is None or ts <= fib_touch_ts:
            continue

        touch_bar_high = df_4h.loc[fib_touch_ts, "High"]
        cur_close      = bar["Close"]

        # Reversal confirmation: close above the touch bar's high
        if cur_close <= touch_bar_high:
            continue

        # 4H RSI: touch bar < FH_RSI_MAX, confirmation bar rising
        rsi_touch   = df_4h.loc[fib_touch_ts, "RSI"]
        rsi_confirm = df_4h.loc[ts, "RSI"]

        if not pd.isna(rsi_touch) and not pd.isna(rsi_confirm):
            if rsi_touch >= FH_RSI_MAX:
                # 4H momentum was not corrective at touch — zone invalid
                break
            if rsi_confirm <= rsi_touch:
                # Momentum not yet turning — keep scanning this window
                continue

        # 4H MA50: allow entry if close is within 3% below MA (normal W2 recovery path).
        # Hard reject only when price is more than 3% below MA (structural bear territory).
        ma50_4h = df_4h.loc[ts, "MA50"]
        if not pd.isna(ma50_4h) and cur_close < ma50_4h * 0.97:
            continue

        # Targets anchored to 4H fib touch low
        target_1 = fib_touch_low + w1_len * D_FIB_TARGET_1
        target_2 = fib_touch_low + w1_len * D_FIB_TARGET_2

        risk   = cur_close - stop
        reward = target_2 - cur_close
        rr     = reward / risk if risk > 0 else 0

        # R:R floor → continue scanning (a later confirmation bar may have better entry)
        if rr < MIN_RR:
            continue

        # R:R ceiling → reject. A very high R:R here means the stop (W1 origin) sits far
        # below entry — a structurally loose setup that produced near-total losses in v1.
        if rr > MAX_RR:
            continue

        try:
            global_pos = df_4h.index.get_loc(ts)
            if isinstance(global_pos, slice):
                global_pos = global_pos.start
        except KeyError:
            continue

        return {
            "entry_price":       round(cur_close, 2),
            "stop_price":        round(stop, 2),
            "target_1_price":    round(target_1, 2),
            "target_2_price":    round(target_2, 2),
            "fib_touch_low_4h":  round(fib_touch_low, 2),
            "rr_ratio":          round(rr, 2),
            "quality_w1":        w1_len / w1_start >= QUALITY_W1_PCT,  # high-conviction impulse flag
            "entry_bar_4h":      global_pos,
            "confirm_ts_4h":     ts,
            "rsi_touch_4h":      round(rsi_touch, 1) if not pd.isna(rsi_touch) else None,
            "rsi_confirm_4h":    round(rsi_confirm, 1) if not pd.isna(rsi_confirm) else None,
        }

    return None


# ── STEP 3: Simulation on 4H data ─────────────────────────────────────────────

def simulate_mtf_trades(df_4h, setups):
    """Simulate trades on 4H bars using daily-based targets."""
    results = []
    for setup in setups:
        entry_bar   = setup["entry_bar_4h"]
        entry_price = setup["entry_price"]
        stop_price  = setup["stop_price"]
        target_1    = setup["target_1_price"]
        target_2    = setup["target_2_price"]

        outcome     = "TIMEOUT"
        exit_price  = df_4h["Close"].iloc[min(entry_bar + FH_HOLD_BARS, len(df_4h)-1)]
        exit_ts     = df_4h.index[min(entry_bar + FH_HOLD_BARS, len(df_4h)-1)]
        hold_bars   = FH_HOLD_BARS
        t1_hit      = False
        active_stop = stop_price

        for k in range(entry_bar + 1, min(entry_bar + FH_HOLD_BARS, len(df_4h))):
            high_k = df_4h["High"].iloc[k]
            low_k  = df_4h["Low"].iloc[k]

            if not t1_hit and high_k >= target_1:
                t1_hit      = True
                active_stop = entry_price * 1.001

            if high_k >= target_2:
                outcome    = "WIN"
                exit_price = target_2
                exit_ts    = df_4h.index[k]
                hold_bars  = k - entry_bar
                break

            if low_k <= active_stop:
                outcome    = "PARTIAL_WIN" if t1_hit else "LOSS"
                exit_price = active_stop
                exit_ts    = df_4h.index[k]
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

        results.append({
            **setup,
            "outcome":    outcome,
            "t1_hit":     t1_hit,
            "exit_price": round(exit_price, 2),
            "exit_ts":    exit_ts,
            "hold_bars":  hold_bars,
            "net_return": round(net_return * 100, 2),
        })
    return results


# ── METRICS ──────────────────────────────────────────────────────────────────

def calc_metrics(trades, annual_4h_bars=1560):
    """
    Full performance suite — mandatory metrics per APEX standards.
    annual_4h_bars: trading hours per year / 4 = ~252 days × 6.5h / 4 ≈ 409.5, but
    we use 1560 for 252 × 6.5h raw to then divide by 4 = 409.5; default 1560 for raw
    4H bar count (adjusted below). Pass actual bars_per_year if period differs.
    """
    if len(trades) == 0:
        return None

    positive = trades[trades["outcome"].isin(["WIN", "PARTIAL_WIN"])]
    losses   = trades[trades["outcome"] == "LOSS"]
    timeouts = trades[trades["outcome"] == "TIMEOUT"]

    # ── Core rates ────────────────────────────────────────────────────────────
    win_rate   = len(positive) / len(trades) * 100
    avg_win    = positive["net_return"].mean() if len(positive) > 0 else 0.0
    avg_loss   = losses["net_return"].mean()   if len(losses)   > 0 else 0.0
    expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)

    gross_wins   = positive["net_return"].sum() if len(positive) > 0 else 0.0
    if len(losses) > 0 and abs(losses["net_return"].sum()) > 0:
        profit_factor = gross_wins / abs(losses["net_return"].sum())
    else:
        # No losses → PF is undefined/infinite. Report a capped sentinel instead of
        # a meaningless 30-million-style number from dividing by ~zero.
        profit_factor = 99.99 if gross_wins > 0 else 0.0

    # ── Equity curve ─────────────────────────────────────────────────────────
    returns_frac = trades["net_return"] / 100          # fractional per-trade returns
    cum          = (1 + returns_frac).cumprod()
    running_max  = cum.cummax()
    drawdown_ser = (cum - running_max) / running_max * 100
    max_dd       = drawdown_ser.min()                  # negative number

    # ── CAGR ─────────────────────────────────────────────────────────────────
    # Estimate elapsed 4H bars: use avg hold_bars if available, else FH_HOLD_BARS
    bars_per_year = annual_4h_bars / 4                 # ~409.5 4H bars/year
    if "hold_bars" in trades.columns:
        total_bars = trades["hold_bars"].sum()
    else:
        total_bars = len(trades) * FH_HOLD_BARS

    years  = max(total_bars / bars_per_year, 1 / 12)  # floor at 1 month
    final  = float(cum.iloc[-1])
    cagr   = (final ** (1 / years) - 1) * 100

    # ── Sharpe & Sortino (per-trade, annualised) ──────────────────────────────
    avg_return   = returns_frac.mean()
    std_return   = returns_frac.std()
    trades_year  = bars_per_year / trades["hold_bars"].mean() if "hold_bars" in trades.columns else 12

    sharpe = (avg_return / std_return * np.sqrt(trades_year)) if std_return > 0 else 0.0

    downside_ret = returns_frac[returns_frac < 0]
    downside_std = downside_ret.std() if len(downside_ret) > 1 else std_return
    sortino = (avg_return / downside_std * np.sqrt(trades_year)) if downside_std > 0 else 0.0

    # ── Calmar ────────────────────────────────────────────────────────────────
    calmar = (cagr / abs(max_dd)) if max_dd < 0 else 0.0

    return {
        "total":          len(trades),
        "wins":           len(positive),
        "losses":         len(losses),
        "timeouts":       len(timeouts),
        "win_rate":       round(win_rate,       1),
        "avg_win":        round(avg_win,        2),
        "avg_loss":       round(avg_loss,       2),
        "expectancy":     round(expectancy,     2),
        "profit_factor":  round(profit_factor,  2),
        "max_drawdown":   round(max_dd,         2),
        "total_return":   round((final - 1) * 100, 2),
        "cagr":           round(cagr,           2),
        "sharpe":         round(sharpe,         2),
        "sortino":        round(sortino,        2),
        "calmar":         round(calmar,         2),
    }


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(RESULTS_DIR, exist_ok=True)
    all_trades = []

    print("\n🔍 APEX MTF Cascade — Daily Structure + 4H Entry")
    print(f"   Daily: W1≥{D_MIN_WAVE1_PCT*100}% | Fib {D_FIB_ENTRY_MIN*100}%–{D_FIB_ENTRY_MAX*100}% | "
          f"RSI<{D_RSI_MAX_AT_TOUCH} | MA{D_TREND_MA} + slope | Regime {D_REGIME_MA}MA")
    print(f"   4H:    RSI<{FH_RSI_MAX} | MA{FH_TREND_MA} | Hold {FH_HOLD_BARS} bars (~{round(FH_HOLD_BARS*4/6.5)} trading days) | "
          f"R/R {MIN_RR}–{MAX_RR}\n")

    # Load SPY regime (daily)
    try:
        spy_daily = load_daily(REGIME_TICKER)
        spy_daily["MA200"] = spy_daily["Close"].rolling(D_REGIME_MA).mean()
        spy_regime_full    = spy_daily["Close"] > spy_daily["MA200"]
        spy_loaded         = True
    except Exception as e:
        print(f"⚠️  SPY regime load failed: {e}")
        spy_regime_full = None
        spy_loaded      = False

    for ticker in TICKERS:
        try:
            # Load both timeframes
            df_daily = load_daily(ticker)
            df_4h    = load_4h(ticker)

            # Precompute 4H indicators used in find_4h_entry
            df_4h["RSI"]  = calc_rsi(df_4h["Close"])
            df_4h["MA50"] = df_4h["Close"].rolling(FH_TREND_MA).mean()

            print(f"\n📂 {ticker}: {len(df_daily)} daily bars | {len(df_4h)} 4H bars")

            # Daily regime series aligned to daily index
            if spy_loaded and spy_regime_full is not None:
                regime = spy_regime_full.reindex(df_daily.index, method="ffill").fillna(False)
            else:
                regime = pd.Series(True, index=df_daily.index)

            # Step 1: find daily zones
            zones = scan_daily_zones(df_daily, ticker, regime)

            # Step 2: for each zone, find 4H precision entry
            setups = []
            no_4h_entry = 0
            for zone in zones:
                entry = find_4h_entry(zone, df_4h)
                if entry is not None:
                    setups.append({**zone, **entry})
                else:
                    no_4h_entry += 1

            print(f"  [MTF-4H {ticker}] 4H entries found: {len(setups)} | No 4H match: {no_4h_entry}")

            # Step 3: simulate
            if setups:
                trades = simulate_mtf_trades(df_4h, setups)
                tdf    = pd.DataFrame(trades)
                tdf.to_csv(f"{RESULTS_DIR}/{ticker}_mtf.csv", index=False)
                all_trades.extend(trades)
                m     = calc_metrics(tdf)
                grade = "🟢" if m["expectancy"] > 0 else "🔴"
                print(f"  {grade} MTF {ticker} | WR: {m['win_rate']}% | E: {m['expectancy']}%/trade | "
                      f"PF: {m['profit_factor']} | CAGR: {m['cagr']}% | "
                      f"Sharpe: {m['sharpe']} | Sortino: {m['sortino']} | "
                      f"Calmar: {m['calmar']} | MaxDD: {m['max_drawdown']}% | "
                      f"W:{m['wins']} L:{m['losses']} T:{m['timeouts']}")

        except FileNotFoundError as e:
            print(f"  ❌ {ticker}: missing data file — {e}")
            print(f"     Run Yfinancedata.py to download daily + 1H data")
        except Exception as e:
            print(f"  ❌ {ticker} ERROR: {e}")

    if all_trades:
        all_df = pd.DataFrame(all_trades)
        all_df.to_csv(f"{RESULTS_DIR}/ALL_mtf_backtest.csv", index=False)
        m = calc_metrics(all_df)
        print(f"\n{'='*75}")
        print(f"⚡ MTF COMBINED — {m['total']} trades")
        print(f"   Win Rate:      {m['win_rate']}%    |  Expectancy:    {m['expectancy']}%/trade")
        print(f"   Profit Factor: {m['profit_factor']}      |  Total Return:  {m['total_return']}%")
        print(f"   CAGR:          {m['cagr']}%     |  Max Drawdown:  {m['max_drawdown']}%")
        print(f"   Sharpe:        {m['sharpe']}      |  Sortino:       {m['sortino']}")
        print(f"   Calmar:        {m['calmar']}      |  W:{m['wins']}  L:{m['losses']}  T:{m['timeouts']}")
        print(f"{'='*75}\n")
    else:
        print("\n⚠️  No MTF trades generated. Check data files and diagnostics above.\n")
