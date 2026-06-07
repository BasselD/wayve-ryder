# APEX — Strategy Overview

*A one-page summary of what we're building and how it works.*

---

## What APEX Is

APEX is an automated system that finds high-probability **options trades on large US tech stocks** (NVDA, TSLA, AMZN, and ~12 others). It studies years of price history to identify a specific, repeatable pattern — then tells us exactly when to buy, where to take profit, and where to cut losses.

Every trade is **researched and tested before any real money is involved.** Nothing goes live without passing historical testing first.

---

## The Core Idea: "Buy the Pullback in a Strong Trend"

Markets move in waves. After a stock makes a strong move up (a "Wave 1"), it almost always pulls back briefly (a "Wave 2") before continuing higher (a "Wave 3" — the big, profitable move). APEX is built to **catch that pullback and ride the next surge.**

```
        Wave 3  ←  the move we want to capture
          ╱
   pullback (Wave 2)  ←  WHERE WE BUY
     ╲  ╱
  Wave 1
   ╱
 start
```

We only buy when the pullback lands in a precise, historically-reliable zone — and only when several independent signals confirm the trend is still healthy.

---

## The Quality Filters (why most setups get rejected)

APEX is **deliberately picky.** Out of hundreds of potential setups, only ~1 in 10 passes every check. A trade must clear all of these:

| Filter | What it checks | Why it matters |
|---|---|---|
| **Trend strength** | The initial up-move was ≥7% | Filters out noise; we want real momentum |
| **Pullback depth** | Price retraced to a specific 50–79% zone | The historically reliable "buy zone" |
| **Momentum** | Selling pressure is fading, then turns up | Confirms the dip is ending, not deepening |
| **Volume** | The pullback came on *declining* volume | Shows the crowd's conviction to sell is weak |
| **Trend direction** | Price is above its long-term average | We only trade *with* the broader trend |
| **Market health** | The overall market (S&P 500) is healthy | Avoids fighting a falling market |
| **Reward vs. risk** | Profit potential is 1.5–2.5× the risk | Every trade must be worth the downside |

If even one filter fails → **no trade.** Discipline over activity.

---

## The Two-Timeframe Approach (our edge)

This is what makes APEX smarter than a basic system. We use **two views of the chart together:**

1. **The daily chart** decides *whether* a setup is worth taking (the slow, high-quality filter above).
2. **The 4-hour chart** decides *exactly when* to enter — pinpointing the bottom of the pullback for a better price.

**The result:** the quality of a patient, long-term signal — with the precision of a sharp, well-timed entry.

---

## Risk Management (built in, not optional)

- **Every trade has a pre-defined exit** — both a profit target and a stop-loss — set *before* entering.
- **Take profits in two stages:** sell half at the first target, let the rest run to the second.
- **After the first target hits, the trade can't become a loss** (stop moves to breakeven).
- **Position limits:** no single trade risks more than 5% of the account.

---

## Where We Are Today

- ✅ Strategy fully defined, coded, and tested on ~3 years of market data across 15 stocks
- ✅ The system is **profitable in testing** and improving with each refinement
- 🔄 **Currently strengthening:** reducing the worst-case drawdown and validating results on unseen data before any live capital
- ⏳ **Next:** paper trading (simulated live trades) before real money

> **Important:** These are historical-test results, not live returns. The system is in the validation stage — no live trading yet. Every claim is backed by data, and we mark anything uncertain clearly.

---

*Built by APEX — an AI-augmented research and trading system. Analysis-only until trades are explicitly approved.*
