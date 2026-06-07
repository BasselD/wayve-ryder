# APEX — Project Map (internal)

Quick reference for what every file does. For the partner-facing summary, see **[APEX_Overview.md](APEX_Overview.md)**.

---

## The 3 Backtest Engines

All three test the **same strategy** (Elliott Wave + Fibonacci). They differ only in **timeframe** and **entry timing**.

| File | Timeframe | Direction | Hold | Status |
|---|---|---|---|---|
| **Backtest_Daily.py** | Daily only | Long **+ Short** | 90 days | Proven original (v10). Only engine with Wave C shorts. |
| **Backtest_4H.py** | 4H only | Long only | ~40 days | Stepping-stone experiment. **Largely superseded by MTF.** |
| **Backtest_MTF.py** | Daily **+** 4H | Long only | ~98 days | Current focus. Daily picks the zone, 4H times the entry. |

### How they relate

- **Backtest_Daily.py** is the mature baseline — finds Wave 1→2 setups on daily bars, enters on the daily close. Carries the v7 fib-anchor breakthrough.
- **Backtest_4H.py** ran the same logic purely on 4H bars. Too noisy on its own. Kept as a reference baseline only.
- **Backtest_MTF.py** is the evolution: it is **NOT** a merge of the other two. It's a two-step cascade — daily chart validates the setup (quality), 4H chart times the entry (precision). This is where active development happens.

> **Shorts live only in Backtest_Daily.py.** MTF and 4H are long-only. If Wave C shorts need MTF treatment, that's a future port.

---

## Support Files

| File | Purpose |
|---|---|
| **Yfinancedata.py** | Downloads daily + 1H price data from yfinance into `./data/`. Run this first. |
| **screen_candidates.py** | Research tool — screens new candidate tickers through the MTF engine without touching production. Does not modify config. |

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
1. python Yfinancedata.py        # download / refresh data
2. python Backtest_MTF.py         # run the main engine
3. (optional) python screen_candidates.py   # evaluate new tickers
```

> On Windows, prefix runs with `PYTHONIOENCODING=utf-8` so the emoji in console output don't error.

---

## Current State (MTF v1.1)

- 15 tickers, ~2.9 years of 4H data
- Combined: 51 trades | WR 45% | Expectancy +0.02% | PF 1.56 | CAGR +12.3% | **MaxDD −61%**
- **Open priorities:** drawdown control (the −61% is the real blocker), walk-forward validation.
