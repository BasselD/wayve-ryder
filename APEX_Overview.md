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

- ✅ Strategy fully defined and coded as **four backtest engines** (daily, 4-hour, a combined two-timeframe "cascade," and a faster short-hold "scalper"), tested on years of data across 12–30 stocks depending on the engine
- ✅ The main engines are **positive in testing** — but the edge is thin and leans heavily on a few names (NVDA in particular)
- ⚠️ **The honest problem:** worst-case drawdowns in testing run deep (roughly **−45% to −70%** peak-to-trough). That is the #1 thing standing between "interesting backtest" and "tradeable system," and it is not solved yet
- 🔄 **Currently strengthening:** cutting that drawdown, and validating on *unseen* data (the tests so far are "in-sample" — the strategy has never been tested through a real bear market)
- ⏳ **Next:** paper trading (simulated live trades) before any real money

> **Important:** These are historical-test results on the *underlying stocks*, not live returns and not actual options P&L (which would be worse). The system is in the validation stage — **no live trading yet.** Every claim is backed by data, and we mark anything uncertain clearly.

---

*Built by APEX — an AI-augmented research and trading system. Analysis-only until trades are explicitly approved.*

---

## Acronym Dictionary

| Acronym | Full Name | Plain English |
|---|---|---|
| **ATR** | Average True Range | How much a stock typically moves per day — used to size stops |
| **CAGR** | Compound Annual Growth Rate | Your average yearly return if all gains are reinvested |
| **CTA** | Commodity Trading Advisor | Professional trend-following fund managers |
| **DTE** | Days to Expiry | How many days until an options contract expires |
| **E** | Expectancy | Average return per trade across all outcomes (wins + losses + timeouts) |
| **EW** | Elliott Wave | Theory that markets move in predictable 5-wave patterns |
| **Fib** | Fibonacci | Mathematical ratios (38.2%, 61.8%, 161.8%) used to predict pullback zones and price targets |
| **MA50 / MA200** | Moving Average 50 / 200 | Average closing price over last 50 or 200 days — used to identify trend direction |
| **MaxDD** | Maximum Drawdown | Worst peak-to-trough loss in the backtest period. -36% means you were once down 36% from your high |
| **MTF** | Multi-Timeframe | Analysing multiple chart timeframes (e.g. daily + 4H) together to confirm a signal |
| **0DTE** | Zero Days to Expiry | Options that expire the same day — highest risk/reward |
| **OHLCV** | Open / High / Low / Close / Volume | The five standard data points on any price bar |
| **PF** | Profit Factor | Total profit ÷ total loss. PF 4.0 = you make $4 for every $1 lost |
| **QQQ** | Invesco QQQ ETF | ETF tracking the Nasdaq 100 — used as our market regime filter |
| **R:R** | Risk-to-Reward | How much you stand to win vs how much you risk. 2:1 = risk $1 to make $2 |
| **RSI** | Relative Strength Index | Momentum indicator 0–100. Below 30 = oversold, above 70 = overbought |
| **Sharpe** | Sharpe Ratio | Return per unit of total risk. >1 good, >2 great, >3 exceptional |
| **Sortino** | Sortino Ratio | Like Sharpe but only penalises downside volatility — more relevant for trading |
| **Calmar** | Calmar Ratio | CAGR ÷ MaxDD. Measures return relative to worst drawdown |
| **SPX** | S&P 500 Index | Index of the 500 largest US companies — the main US market benchmark |
| **T1** | Target 1 | The price level where we take profit (set at 1.618× the W1 move from W2 low) |
| **VIX** | Volatility Index | The market's "fear gauge." High VIX = panic/uncertainty, low VIX = calm |
| **W0/W1/W2/W3** | Wave 0 / 1 / 2 / 3 | EW labels: W0 = swing bottom, W1 = impulse up, W2 = pullback, W3 = breakout we trade |
| **WR** | Win Rate | Percentage of trades that hit the profit target (T1) |
