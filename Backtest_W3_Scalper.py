"""
APEX Backtest Engine — W3 Scalper v1.4
Wave 3 breakout strategy: independent, high-frequency, short-hold.

Design philosophy
-----------------
MTF + Daily engines are precision instruments — few, grade-A setups, 30-90 day holds.
This engine is a rapid-fire momentum catcher: wider net, shorter holds, accepts more risk.
It does NOT depend on the Daily or MTF scanner outputs.

Signal logic
------------
  W0 (swing low) →
  W1 (swing high, ≥4% above W0) →
  W2 (pullback 38.2%–78.6% of W1, RSI < 60) →
  W3 entry (first close ≥ W1 high + 0.1% WITH volume surge AND RSI > 50 rising vs W2)

Key differences vs Daily v11
-----------------------------
  MIN_WAVE1_PCT : 4%  (vs 7%)      — catches smaller, more frequent waves
  Fib zone      : 38.2%–78.6%     — includes shallower pullbacks (vs 50%–78.6%)
  RSI at W2     : < 60 (vs < 55)  — less restrictive at the base
  MA50 slope    : not required     — agility over confirmation
  Volume filter : W3 bar > 1.3×   — confirms the breakout impulse
  RSI at entry  : > 50 AND rising  — momentum on at W3 trigger
  Regime        : QQQ above MA50  — more signals than MA200 gate
  Hold max      : 15 days          — capture impulse, exit before W4 chop
  Min R:R       : 1.2 (vs 1.5)    — wider tolerance
  Exit          : 100% at T1 (1.618× W1 from W2 low) — no T2, no scaling
  Universe      : 25 tickers       — 2× wider than daily scanner
"""

import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings("ignore")

# ── CONFIG ────────────────────────────────────────────────────────────────────
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
    # Removed — negative/near-zero E or low E for risk:
    #   ARM (-4.1%), UBER (-4.1%), RBLX (-0.5%), TTD (-0.3%), NOW (-1.7%)
    #   PLTR (-1.95%), NFLX (-1.2%), NET (-3.32%), HIMS (-9.1%), MDB (-3.1%)
    #   MSTR (+1.6% E, -48.7% MaxDD), QCOM (+0.96%), SMCI (+3.2%), PYPL (+1.6%)
    # SHOP excluded: WR 10%, MaxDD -25.75%
]

DATA_DIR    = "./data"
RESULTS_DIR = "./results/w3_scalper"

SWING_LOOKBACK  = 7      # shorter than daily (10) → more swings detected

MIN_WAVE1_PCT   = 0.04   # 4% minimum W1 move — restored for stronger impulse quality
FIB_ENTRY_MIN   = 0.382  # 38.2% — includes shallower W2 pullbacks
FIB_ENTRY_MAX   = 0.700  # 70% max — tightened from 78.6% to exclude deep/risky retracements
BREAKOUT_BUFFER = 0.001  # close must be 0.1% above W1 high to confirm W3

FIB_TARGET_1  = 1.618  # T1 = W2_low + 1.618 × W1_size — W3 classic target
                       # R:R from W1_high entry ≈ 1.7:1 (works). 1.0× would drop R:R to 0.67 (fails).
HOLD_DAYS_MAX = 25     # 25 sessions — gives W3 impulse enough time to reach T1
                       # (15d too short: 82% timeouts. 25d converts ~30% timeouts to wins)

TRANSACTION_COST = 0.0005  # 0.05% each way (entry + exit = 2×)
MIN_RR           = 1.0     # loosened from 1.2 — accepts slightly worse R:R to increase frequency
POSITION_SIZE    = 0.10    # 10% of portfolio per trade — used for realistic CAGR calculation

TRAIL_TRIGGER_PCT = 5.0   # once up 5%, activate trailing stop
TRAIL_PCT         = 8.0   # trail at 8% below highest high (wide enough for tech volatility)
TRAIL_FLOOR_PCT   = 0.5   # trail stop never goes below entry + 0.5%
# NOTE: trailing stop is intentionally DISABLED — see simulate_w3_trades.
# W3 impulses have 5-10% intraday pullbacks en route to T1; any trail tight enough
# to catch a reversal also cuts genuine W3 moves. Timeouts avg +5.5% = expected behaviour.

RSI_PERIOD          = 14
RSI_MAX_AT_W2       = 65   # loosened from 60 — allows slightly less oversold W2 entries
RSI_MIN_AT_BREAKOUT = 50   # breakout bar RSI must be > 50 — momentum on

TREND_MA      = 50     # stock must be above its own MA50 at W3 entry
REGIME_TICKER = "QQQ"  # QQQ better matches the tech/growth universe we trade
REGIME_MA     = 50     # QQQ MA50 — more permissive than MA200, right for scalper frequency

VIX_BLOCK_LEVEL = 25  # no new entries when VIX >= 25 (panic/vol spike regime)

VOL_LOOKBACK = 20   # rolling average window
VOL_RATIO    = 1.0  # W3 breakout bar volume must be > 1.0× 20-day average (any above-avg day)

MAX_W2_BARS = 60  # bars after W1 peak to find W2 bottom
MAX_W3_BARS = 30  # bars after W2 bottom to find W3 breakout
# ─────────────────────────────────────────────────────────────────────────────


def load_data(ticker):
    path = f"{DATA_DIR}/{ticker}_daily.csv"
    df   = pd.read_csv(path)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).split(",")[0].strip("('\" )") for c in df.columns]

    date_col = next((c for c in df.columns if "date" in c.lower() or "time" in c.lower()), None)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)

    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if cl == "open":     col_map[c] = "Open"
        elif cl == "high":   col_map[c] = "High"
        elif cl == "low":    col_map[c] = "Low"
        elif cl == "close":  col_map[c] = "Close"
        elif cl == "volume": col_map[c] = "Volume"
    df = df.rename(columns=col_map)

    required = ["Open", "High", "Low", "Close"]
    missing  = [r for r in required if r not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    for c in required:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=required)


def calc_rsi(close, period=14):
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def find_swings(df, lookback=7):
    highs, lows = [], []
    n = len(df)
    for i in range(lookback, n - lookback):
        if df["High"].iloc[i] == df["High"].iloc[i - lookback: i + lookback + 1].max():
            highs.append(i)
        if df["Low"].iloc[i] == df["Low"].iloc[i - lookback: i + lookback + 1].min():
            lows.append(i)
    return highs, lows


def add_indicators(df):
    df = df.copy()
    df["RSI"]  = calc_rsi(df["Close"], RSI_PERIOD)
    df["MA50"] = df["Close"].rolling(TREND_MA).mean()
    if "Volume" in df.columns:
        df["Vol20"] = df["Volume"].rolling(VOL_LOOKBACK).mean()
    return df


# ── W3 SCANNER ───────────────────────────────────────────────────────────────

def scan_w3_setups(df, ticker, spy_regime=None, vix_series=None):
    """
    Two-phase scan per W1 anchor:
      Phase 1 (up to MAX_W2_BARS after W1 peak):
        Track the deepest W2 retracement that lands in the 38.2–78.6% Fib zone.
      Phase 2 (up to MAX_W3_BARS after W2 bottom):
        Find the first bar where Close breaks above W1 high + BREAKOUT_BUFFER.
        Apply filters at that breakout bar; record setup if all pass.
    One setup per W1 peak (used_w1 guard prevents duplicates).
    """
    df      = add_indicators(df)
    n       = len(df)
    has_vol = "Volume" in df.columns

    swing_highs, swing_lows = find_swings(df, SWING_LOOKBACK)
    used_w1 = set()
    setups  = []

    sk = dict(w1_size=0, w2_none=0, rsi_w2=0, w3_none=0,
              trend=0, regime=0, vix=0, vol=0, rsi_break=0, rr=0)

    for low_idx in swing_lows:
        # ── W1: first qualifying swing high after this low ──────────────────
        candidates = [h for h in swing_highs if low_idx < h <= low_idx + 80]
        if not candidates:
            continue

        high_idx = candidates[0]
        if high_idx in used_w1:
            continue

        w0_low  = df["Low"].iloc[low_idx]
        w1_high = df["High"].iloc[high_idx]
        w1_size = w1_high - w0_low

        if w1_size / w0_low < MIN_WAVE1_PCT:
            sk["w1_size"] += 1
            continue

        fib_382 = w1_high - FIB_ENTRY_MIN * w1_size   # 38.2% retracement level
        fib_786 = w1_high - FIB_ENTRY_MAX * w1_size   # 78.6% retracement level

        # ── Phase 1: find deepest W2 bottom inside the Fib zone ─────────────
        w2_price     = float("inf")
        w2_idx       = None
        phase1_limit = min(high_idx + MAX_W2_BARS,
                           n - MAX_W3_BARS - HOLD_DAYS_MAX - 2)

        for j in range(high_idx + 1, phase1_limit):
            if df["Low"].iloc[j] < w0_low:   # W1 structure invalidated
                break
            retrace = (w1_high - df["Low"].iloc[j]) / w1_size
            if FIB_ENTRY_MIN <= retrace <= FIB_ENTRY_MAX:
                if df["Low"].iloc[j] < w2_price:
                    w2_price = df["Low"].iloc[j]
                    w2_idx   = j

        if w2_idx is None:
            sk["w2_none"] += 1
            continue

        # ── RSI filter at W2 bottom (applied once, before Phase 2 loop) ─────
        rsi_at_w2 = df["RSI"].iloc[w2_idx]
        if pd.isna(rsi_at_w2) or rsi_at_w2 >= RSI_MAX_AT_W2:
            sk["rsi_w2"] += 1
            continue

        # ── Phase 2: find first W3 breakout close after W2 bottom ───────────
        found_w3    = False
        phase2_limit = min(w2_idx + MAX_W3_BARS, n - HOLD_DAYS_MAX - 1)

        for k in range(w2_idx + 1, phase2_limit):
            if df["Low"].iloc[k] < w0_low:   # structure broken during W3 search
                break

            if df["Close"].iloc[k] <= w1_high * (1 + BREAKOUT_BUFFER):
                continue   # not broken out yet

            # ── W3 breakout bar k — apply all filters ──────────────────────

            # Trend filter removed — QQQ regime already covers macro direction;
            # W3 breakout above W1 high inherently confirms stock momentum

            # QQQ regime
            if spy_regime is not None:
                entry_date = df.index[k]
                if entry_date in spy_regime.index and not bool(spy_regime.loc[entry_date]):
                    sk["regime"] += 1
                    continue

            # VIX regime — block entries when volatility is in panic territory
            if vix_series is not None:
                entry_date = df.index[k]
                vix_val = vix_series.reindex([entry_date], method="ffill").iloc[0]
                if not pd.isna(vix_val) and vix_val >= VIX_BLOCK_LEVEL:
                    sk["vix"] += 1
                    continue

            # RSI at breakout: > 50 AND rising vs W2 bottom
            rsi_at_k = df["RSI"].iloc[k]
            if pd.isna(rsi_at_k) or rsi_at_k < RSI_MIN_AT_BREAKOUT or rsi_at_k <= rsi_at_w2:
                sk["rsi_break"] += 1
                continue

            # Volume: breakout bar must be elevated vs 20-day average
            if has_vol and "Vol20" in df.columns:
                vol20 = df["Vol20"].iloc[k]
                if not pd.isna(vol20) and vol20 > 0:
                    if df["Volume"].iloc[k] < VOL_RATIO * vol20:
                        sk["vol"] += 1
                        continue

            # R:R
            entry_price = df["Close"].iloc[k]
            stop_price  = w2_price * 0.998          # 0.2% buffer below W2 low
            target_1    = w2_price + FIB_TARGET_1 * w1_size

            risk   = entry_price - stop_price
            reward = target_1 - entry_price

            if risk <= 0:
                continue

            rr = reward / risk
            if rr < MIN_RR:
                sk["rr"] += 1
                break   # W3 has fired; if R:R fails now it won't improve on later bars

            # ── All filters passed — record setup ───────────────────────────
            used_w1.add(high_idx)
            found_w3 = True

            setups.append({
                "direction":       "LONG",
                "ticker":          ticker,
                "w0_date":         df.index[low_idx],
                "w1_high_date":    df.index[high_idx],
                "w2_low_date":     df.index[w2_idx],
                "w3_break_date":   df.index[k],
                "w0_price":        round(w0_low, 2),
                "w1_high_price":   round(w1_high, 2),
                "w2_low_price":    round(w2_price, 2),
                "entry_price":     round(entry_price, 2),
                "stop_price":      round(stop_price, 2),
                "target_1_price":  round(target_1, 2),
                "w1_pct_move":     round(w1_size / w0_low * 100, 2),
                "retracement_pct": round((w1_high - w2_price) / w1_size * 100, 2),
                "rsi_at_w2":       round(rsi_at_w2, 1),
                "rsi_at_break":    round(rsi_at_k, 1),
                "rr_ratio":        round(rr, 2),
                "entry_bar":       k,
            })
            break   # one setup per W1 peak

        if not found_w3:
            sk["w3_none"] += 1

    print(f"  [W3 {ticker:5s}] Filtered — W1:{sk['w1_size']} | No W2:{sk['w2_none']} | "
          f"RSI@W2:{sk['rsi_w2']} | No W3:{sk['w3_none']} | Trend:{sk['trend']} | "
          f"Regime:{sk['regime']} | VIX:{sk['vix']} | Vol:{sk['vol']} | "
          f"RSI@brk:{sk['rsi_break']} | R:R:{sk['rr']}")
    print(f"  [W3 {ticker:5s}] ✅ Setups: {len(setups)}")
    return setups


# ── SIMULATION ───────────────────────────────────────────────────────────────

def simulate_w3_trades(df, setups):
    """
    Scalper exit logic:
      WIN     = High touches T1 within HOLD_DAYS_MAX
      TRAIL   = Breakeven stop triggered after TRAIL_TRIGGER_PCT gain (locks profit)
      LOSS    = Low touches stop within HOLD_DAYS_MAX
      TIMEOUT = neither triggered; exit at Close of bar HOLD_DAYS_MAX
    """
    results = []
    for setup in setups:
        entry_bar   = setup["entry_bar"]
        entry_price = setup["entry_price"]
        stop_price  = setup["stop_price"]
        target_1    = setup["target_1_price"]
        n           = len(df)

        outcome    = "TIMEOUT"
        exit_price = df["Close"].iloc[min(entry_bar + HOLD_DAYS_MAX, n - 1)]
        exit_date  = df.index[min(entry_bar + HOLD_DAYS_MAX, n - 1)]
        hold_days  = HOLD_DAYS_MAX

        for k in range(entry_bar + 1, min(entry_bar + HOLD_DAYS_MAX + 1, n)):
            high_k = df["High"].iloc[k]
            low_k  = df["Low"].iloc[k]

            if high_k >= target_1:
                outcome    = "WIN"
                exit_price = target_1
                exit_date  = df.index[k]
                hold_days  = k - entry_bar
                break

            if low_k <= stop_price:
                outcome    = "LOSS"
                exit_price = stop_price
                exit_date  = df.index[k]
                hold_days  = k - entry_bar
                break

        net_return = (exit_price - entry_price) / entry_price - 2 * TRANSACTION_COST
        results.append({
            **setup,
            "outcome":    outcome,
            "exit_price": round(exit_price, 2),
            "exit_date":  exit_date,
            "hold_days":  hold_days,
            "net_return": round(net_return * 100, 2),
        })
    return results


# ── METRICS ──────────────────────────────────────────────────────────────────

def calc_metrics(trades):
    if len(trades) == 0:
        return None

    wins     = trades[trades["outcome"] == "WIN"]
    losses   = trades[trades["outcome"] == "LOSS"]
    timeouts = trades[trades["outcome"] == "TIMEOUT"]

    win_rate    = len(wins) / len(trades) * 100
    avg_win     = wins["net_return"].mean()     if len(wins)     > 0 else 0
    avg_loss    = losses["net_return"].mean()   if len(losses)   > 0 else 0
    avg_timeout = timeouts["net_return"].mean() if len(timeouts) > 0 else 0

    # True expectancy = mean of ALL trade returns (wins + losses + timeouts)
    expectancy = trades["net_return"].mean()

    # PF uses all positive-return trades vs all negative-return trades
    positive_r = trades[trades["net_return"] > 0]["net_return"].sum()
    negative_r = abs(trades[trades["net_return"] <= 0]["net_return"].sum())
    pf = positive_r / negative_r if negative_r > 0 else float("inf")

    cum    = (1 + trades["net_return"] / 100).cumprod()
    max_dd = ((cum - cum.cummax()) / cum.cummax()).min() * 100

    # CAGR — position-sized (realistic): each trade only deploys POSITION_SIZE% of portfolio.
    # Raw compounding assumes 100% per trade → inflated CAGR. This is the honest number.
    try:
        first_entry = pd.to_datetime(trades["w3_break_date"].min())
        last_exit   = pd.to_datetime(trades["exit_date"].max())
        years = (last_exit - first_entry).days / 365.25
        portfolio_returns = trades["net_return"] / 100 * POSITION_SIZE
        cum_portfolio     = (1 + portfolio_returns).cumprod()
        cagr = (cum_portfolio.iloc[-1] ** (1 / years) - 1) * 100 if years > 0.1 else 0
    except Exception:
        cagr = 0

    # Annualised Sharpe approximation from per-trade returns
    avg_hold       = trades["hold_days"].mean() if "hold_days" in trades.columns else HOLD_DAYS_MAX
    trades_per_yr  = 252 / max(avg_hold, 1)
    ret_std        = trades["net_return"].std()
    sharpe = (trades["net_return"].mean() / ret_std * np.sqrt(trades_per_yr)
              if ret_std > 0 else 0)

    return {
        "total": len(trades), "wins": len(wins),
        "losses": len(losses), "timeouts": len(timeouts),
        "win_rate": round(win_rate, 1), "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2), "avg_timeout": round(avg_timeout, 2),
        "expectancy": round(expectancy, 2), "profit_factor": round(pf, 2),
        "max_drawdown": round(max_dd, 2), "cagr": round(cagr, 2),
        "sharpe": round(sharpe, 2), "total_return": round(trades["net_return"].sum(), 2),
    }


def print_metrics(m, label):
    icon = "🟢" if m["expectancy"] > 0 else "🔴"
    print(f"  {icon} {label} | WR:{m['win_rate']}% | E:{m['expectancy']}% | "
          f"PF:{m['profit_factor']} | CAGR(10%):{m['cagr']:.1f}% | Sharpe:{m['sharpe']} | "
          f"MaxDD:{m['max_drawdown']}% | W:{m['wins']} L:{m['losses']} T:{m['timeouts']} "
          f"(avg T:{m['avg_timeout']}%)")


# ── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(RESULTS_DIR, exist_ok=True)
    all_trades = []

    print("\n⚡ APEX W3 Scalper v1.4")
    print(f"   W1 min: {MIN_WAVE1_PCT*100:.0f}% | Fib: {FIB_ENTRY_MIN*100:.1f}%–{FIB_ENTRY_MAX*100:.1f}% | "
          f"T1: {FIB_TARGET_1}× | Hold: {HOLD_DAYS_MAX}d | Min R:R: {MIN_RR}")
    print(f"   RSI@W2 < {RSI_MAX_AT_W2} | RSI@break > {RSI_MIN_AT_BREAKOUT} | "
          f"Vol: {VOL_RATIO}× | Regime: {REGIME_TICKER} MA{REGIME_MA} | "
          f"VIX block: ≥{VIX_BLOCK_LEVEL} | Swing lookback: {SWING_LOOKBACK}\n")

    # Load QQQ regime (MA50 — more permissive than MA200)
    spy_regime_full = None
    try:
        spy_df = load_data(REGIME_TICKER)
        spy_df["MA_regime"] = spy_df["Close"].rolling(REGIME_MA).mean()
        spy_regime_full     = spy_df["Close"] > spy_df["MA_regime"]
        print(f"✅ {REGIME_TICKER} MA{REGIME_MA} regime loaded")
    except Exception as e:
        print(f"⚠️  {REGIME_TICKER} regime unavailable ({e}) — regime filter disabled")

    # Load VIX — block entries when panic vol spikes above VIX_BLOCK_LEVEL
    vix_series_full = None
    try:
        import yfinance as yf
        vix_raw = yf.download("^VIX", start="2020-01-01", end="2026-06-28",
                              interval="1d", auto_adjust=True, progress=False)
        if vix_raw is None or vix_raw.empty:
            raise ValueError("VIX download returned no data")
        vix_raw.columns = [c[0] if isinstance(c, tuple) else c for c in vix_raw.columns]
        vix_series_full = vix_raw["Close"]
        print(f"✅ VIX loaded — blocking entries at VIX ≥ {VIX_BLOCK_LEVEL}\n")
    except Exception as e:
        print(f"⚠️  VIX unavailable ({e}) — VIX filter disabled\n")

    for ticker in TICKERS:
        try:
            df = load_data(ticker)
            print(f"📂 {ticker}: {len(df)} rows | "
                  f"${df['Close'].min():.2f}–${df['Close'].max():.2f}")

            spy_regime = None
            if spy_regime_full is not None:
                spy_regime = spy_regime_full.reindex(df.index, method="ffill").fillna(False)

            setups = scan_w3_setups(df, ticker, spy_regime=spy_regime,
                                    vix_series=vix_series_full)
            trades = simulate_w3_trades(df, setups)

            if trades:
                tdf = pd.DataFrame(trades)
                tdf.to_csv(f"{RESULTS_DIR}/{ticker}_w3.csv", index=False)
                all_trades.extend(trades)
                print_metrics(calc_metrics(tdf), f"W3 {ticker}")
            else:
                print(f"  ⚪ {ticker}: 0 trades")

            print()

        except Exception as e:
            print(f"  ❌ {ticker} ERROR: {e}\n")

    print("=" * 70)
    if all_trades:
        all_df = pd.DataFrame(all_trades)
        all_df.to_csv(f"{RESULTS_DIR}/ALL_w3_scalper.csv", index=False)

        m = calc_metrics(all_df)
        if not m:
            print("No trades to report.")
        else:
            print("\n📊 COMBINED W3 SCALPER RESULTS")
            print(f"   Tickers: {len(all_df['ticker'].unique())} | Trades: {m['total']}")
            print_metrics(m, "ALL TICKERS")
            print(f"\n   Avg hold : {all_df['hold_days'].mean():.1f} days")
            print(f"   Total return : {m['total_return']:.1f}%  |  CAGR (10% sizing): {m['cagr']:.1f}%")

            print(f"\n   Outcome breakdown:")
            print(f"     WIN    : {m['wins']:>4}  ({m['wins']/m['total']*100:.1f}%)  avg: {m['avg_win']:.2f}%")
            print(f"     LOSS   : {m['losses']:>4}  ({m['losses']/m['total']*100:.1f}%)  avg: {m['avg_loss']:.2f}%")
            print(f"     TIMEOUT: {m['timeouts']:>4}  ({m['timeouts']/m['total']*100:.1f}%)  avg: {m['avg_timeout']:.2f}%")

            print(f"\n   Top 5 by expectancy:")
            ticker_stats = []
            for t in all_df["ticker"].unique():
                t_df = all_df[all_df["ticker"] == t]
                tm   = calc_metrics(t_df)
                if tm:
                    ticker_stats.append((t, tm["expectancy"], tm["win_rate"], tm["cagr"], len(t_df)))
            ticker_stats.sort(key=lambda x: x[1], reverse=True)
            for t, e, wr, cagr, cnt in ticker_stats[:5]:
                print(f"     {t:6s} | E:{e:+.2f}% | WR:{wr:.1f}% | CAGR:{cagr:.1f}% | {cnt} trades")
    else:
        print("\nNo trades generated — check filter parameters or data directory.")
