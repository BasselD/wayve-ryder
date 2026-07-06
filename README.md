# APEX — Project Map (internal)

Quick reference for what every file does. For the partner-facing summary, see **[APEX_Overview.md](APEX_Overview.md)**.

---

## The 4 Backtest Engines

All four test the **same strategy** (Elliott Wave + Fibonacci). They differ in **timeframe**, **entry timing**, and **hold horizon**.

| File | Timeframe | Direction | Hold | Status |
|---|---|---|---|---|
| **Backtest_Daily.py** (v11) | Daily only | Long **+ Short** | ~90 days | Mature baseline. Only engine with Wave C shorts (shorts currently net-losing). |
| **Backtest_4H.py** | 4H only | Long only | ~40 days | Stepping-stone experiment. **Superseded by MTF** (negative expectancy on its own). |
| **Backtest_MTF.py** (v1.2) | Daily **+** 4H | Long only | ~98 days | **Primary engine.** Daily picks the zone, 4H times the entry. |
| **Backtest_W3_Scalper.py** (v1.4) | Daily | Long only | ~25 days | Independent fast momentum catcher — wider net (~30 tickers), shorter holds, higher trade count. |

### How they relate

- **Backtest_Daily.py** is the mature baseline — finds Wave 1→2 setups on daily bars, enters on the daily close. Carries the fib-anchor-at-C fix. Adds a dual-regime gate for Wave C shorts (v11).
- **Backtest_4H.py** ran the same logic purely on 4H bars. Too noisy on its own (negative expectancy). Kept as a reference baseline only.
- **Backtest_MTF.py** is the evolution of Daily + 4H: **NOT** a merge — a two-step cascade. Daily chart validates the setup (quality), 4H chart times the entry (precision). Main development focus.
- **Backtest_W3_Scalper.py** is a separate, independent engine — it does **not** consume Daily/MTF output. It hunts the Wave 3 breakout itself with looser filters, a wider universe, and short holds. Most of its positive expectancy comes from small-positive timeouts, not clean target hits — read its metrics with that in mind.

> **Shorts live only in Backtest_Daily.py**, and they currently lose money (0% WR on the latest run). MTF, 4H, and W3 Scalper are all long-only.

---

## Support Files

| File | Purpose |
|---|---|
| **Yfinancedata.py** | Downloads daily + 1H price data from yfinance into `./data/`. Run this first. **Note:** its ticker list does not include the QQQ regime ticker or the full W3 Scalper universe — download those separately or they fall back to "regime always on." |
| **screen_candidates.py** | Research tool — screens new candidate tickers through the MTF engine without touching production. Does not modify config. |
| **Scanner_Live.py** | On-demand live scanner. Refreshes data, then runs the W3 Scalper + Daily v11 logic against the latest bars and prints ranked trade cards + a "pending breakout" watchlist. Cards show days-to-earnings and flag vetoed Daily signals. Writes `./signals/signals_YYYY-MM-DD.csv`. |
| **events.py** | Earnings calendar + pre-earnings entry veto (no Daily/MTF entry ≤10d before that ticker's earnings; W3 exempt). Caches `./data/earnings_dates.csv` — refresh with `python events.py`. |

---

## Strategy & Config Docs

| File | Purpose |
|---|---|
| **CLAUDE.md** | APEX agent configuration (identity, rules, output conventions). Loads every session. |
| **Strategy_EW.md** | Full Elliott Wave strategy spec + backtest log / version history. |
| **Checklists_EW.md** | Pre-trade checklists (long + short). |
| **APEX_Overview.md** | Plain-language one-pager for partners. |

---

## Data & Output Folders (git-ignored)

| Folder | Contents |
|---|---|
| `./data/` | Downloaded price CSVs (`{ticker}_daily.csv`, `{ticker}_1h.csv`) |
| `./results/` | Backtest output CSVs (`results/mtf/`, `results/4h/`) |

---

## Typical Workflow

```
1. python Yfinancedata.py        # download / refresh data (also grab QQQ + W3 universe)
2. python Backtest_MTF.py         # run the primary engine
3. python Backtest_Daily.py       # baseline (long + short)
4. python Backtest_W3_Scalper.py  # fast scalper (pulls ^VIX itself)
5. (optional) python screen_candidates.py   # evaluate new tickers
6. (on demand) python Scanner_Live.py        # live signal cards
```

> On Windows, prefix runs with `PYTHONIOENCODING=utf-8` so the emoji in console output don't error.

---

## Current State — verified 2026-07-05 (in-sample, single pass, earnings veto active on Daily + MTF)

| Engine | Tickers | Trades | WR | E/trade | PF | CAGR | MaxDD |
|---|---|---|---|---|---|---|---|
| **MTF (primary, v1.3)** | 13 | 41 | 56.1% | +2.04% | 2.79 | +19.2% | −63.1% |
| Daily LONG | 12 | 122 | 52.5% | +5.04% | 3.27 | — | −44.6% |
| Daily SHORT | 12 | 4 | 0.0% | −15.6% | 0.0 | — | −24.3% |
| 4H (superseded, no veto) | 12 | 135 | 39.3% | −1.82% | 1.02 | — | −68.5% |
| W3 Scalper (veto-exempt) | 30 | 271 | 33.2% | +6.56% | 4.11 | +33.9%¹ | −43.2% |

¹ CAGR at 10% position sizing. All figures are **underlying-equity** backtests, in-sample, no walk-forward. NVDA carries the MTF book (WR 60%, E +5.4%). MaxDD compounds each trade at 100% of equity — at realistic 10% sizing the health check measured roughly −8% to −13%, but **concurrency (up to 17 simultaneous correlated positions) is unmanaged**.

- **Open priorities (in order):** (1) concurrency / portfolio-level position caps — the real tail risk; (2) walk-forward / out-of-sample validation; (3) edge-decay tripwire (expectancy halved over 18 months — see `research/edge_decay_analysis_2026-07-05.md`); (4) model actual option P&L; (5) fix or retire the losing Daily short side.
