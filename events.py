"""
events.py — Event-awareness helpers for the APEX engines.

EARNINGS VETO RULE (added 2026-07-05, data-driven):
    Block Daily/MTF entries when the ticker's next earnings report is
    <= EARNINGS_VETO_DAYS calendar days away. W3 Scalper is EXEMPT.

Evidence (458 historical trades, results/event_analysis_trades.csv):
    - Entries 0-10d before earnings: WR 58-59%, avg +2.5% to +4.1%/trade
    - Entries >10d from earnings:    WR 67-73%, avg +6.7% to +7.4%/trade
    - 46% of MTF stop-outs exited within 3 days AFTER an earnings print
      (earnings gaps blowing through the structural stop)
    - Post-earnings entries are FINE (best bucket +9.9%) — veto is
      pre-earnings only, scanning continues past the print
    - W3 exempt: its 0-5d bucket wins 65.5% at +6.8% — breakout momentum
      is sometimes earnings-driven, filtering it costs money

No lookahead bias: earnings dates are publicly scheduled weeks in advance,
so a live trader would know them at entry time.

Usage:
    from events import load_earnings_calendar, earnings_veto, days_to_next_earnings
    cal = load_earnings_calendar()
    if earnings_veto("NVDA", entry_date, cal):
        continue  # skip this entry, keep scanning

Refresh the calendar (also called by Yfinancedata.py):
    python events.py
"""

import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ── CONFIG ─────────────────────────────────────────────────────────────────────
EARNINGS_CSV       = "./data/earnings_dates.csv"
EARNINGS_VETO_DAYS = 10   # veto entries with earnings <= this many calendar days ahead


def load_earnings_calendar(path=EARNINGS_CSV):
    """
    Load the cached earnings calendar.

    Returns {ticker: sorted numpy array of datetime64 earnings dates}.
    Returns {} with a LOUD warning if the file is missing — the veto silently
    turning itself off is exactly the failure mode the QQQ regime bug had.
    """
    if not os.path.exists(path):
        print(f"⚠️  EVENTS: {path} not found — EARNINGS VETO DISABLED. "
              f"Run `python events.py` to build it.")
        return {}
    cal = pd.read_csv(path, parse_dates=["earnings_date"])
    return {t: g["earnings_date"].sort_values().values
            for t, g in cal.groupby("ticker")}


def days_to_next_earnings(ticker, date, cal):
    """Calendar days from `date` to the ticker's next earnings. None if unknown."""
    ed = cal.get(ticker)
    if ed is None or len(ed) == 0:
        return None
    d64 = np.datetime64(pd.Timestamp(date).normalize())
    future = ed[ed >= d64]
    if len(future) == 0:
        return None
    return int((future[0] - d64) / np.timedelta64(1, "D"))


def earnings_veto(ticker, date, cal, window=EARNINGS_VETO_DAYS):
    """
    True if an entry on `date` should be blocked (earnings within `window` days).

    Unknown ticker / no future dates => no veto (but check calendar_is_stale()
    in live use so 'no data' can't masquerade as 'no earnings').
    """
    d = days_to_next_earnings(ticker, date, cal)
    return d is not None and d <= window


def calendar_is_stale(cal, ticker, asof=None):
    """
    True if the calendar has no earnings date on/after `asof` for this ticker —
    meaning days_to_next_earnings() would return None not because earnings
    don't exist but because the cache is outdated. Live scanner must warn.
    """
    ed = cal.get(ticker)
    if ed is None or len(ed) == 0:
        return True
    asof = np.datetime64(pd.Timestamp(asof or pd.Timestamp.today()).normalize())
    return ed.max() < asof


def refresh_earnings_calendar(tickers, path=EARNINGS_CSV, limit=40):
    """Download earnings dates via yfinance for `tickers` and cache to CSV."""
    import time
    import yfinance as yf

    rows, fails = [], []
    for tk in tickers:
        try:
            ed = yf.Ticker(tk).get_earnings_dates(limit=limit)
            if ed is None or len(ed) == 0:
                fails.append(tk)
                continue
            for ts in ed.index:
                rows.append({"ticker": tk,
                             "earnings_date": pd.Timestamp(ts).tz_localize(None).normalize()})
            time.sleep(0.4)
        except Exception as e:
            fails.append(f"{tk}: {e}")

    cal = pd.DataFrame(rows).drop_duplicates()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cal.to_csv(path, index=False)
    print(f"✅ Saved {len(cal)} earnings dates for {cal['ticker'].nunique()} tickers -> {path}")
    if fails:
        print(f"⚠️  Failed: {fails}")
    return cal


if __name__ == "__main__":
    # Refresh for the union of every engine's universe (matches the trade logs)
    ALL_TICKERS = ["AAPL", "ABNB", "ADBE", "AMD", "AMZN", "ANET", "APP", "AVGO",
                   "CELH", "COIN", "CRM", "CRWD", "DASH", "DDOG", "DKNG", "FTNT",
                   "GOOGL", "HOOD", "LRCX", "META", "MRVL", "MSFT", "MU", "NFLX",
                   "NVDA", "ORCL", "PANW", "PLTR", "SHOP", "SMCI", "SNOW", "TSLA",
                   "XYZ", "ZS"]
    refresh_earnings_calendar(ALL_TICKERS)
