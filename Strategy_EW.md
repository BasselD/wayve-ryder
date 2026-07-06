

# STRATEGY_EW.md — Elliott Wave + Fib + S/R Options System

## Strategy Overview

**Thesis**: Markets move in predictable fractal wave structures driven by crowd psychology. By identifying wave position and confirming with Fibonacci levels, momentum, volume, and trend alignment, we can pinpoint high-probability options entry points with defined risk in both directions.

**Two primary setups:**
- **Wave 3 LONG** → Buy calls / bull debit spread — enter at Wave 2 completion
- **Wave C SHORT** → Buy puts / bear debit spread — enter at Wave B trap bounce completion

**Planned (not yet in backtest):**
- Wave 5 long → Calls at reduced size (final push before A-B-C correction)

**Trading Universe** — differs per engine (see each engine's `TICKERS` list; this is the source of truth):

| Engine | Universe (as coded) |
|---|---|
| **Daily** (v11) | NVDA, GOOGL, TSLA, AAPL, AMD, MSFT, AMZN, META, SMCI, PLTR, CRM, NFLX (12) |
| **4H** | Same 12 as Daily |
| **MTF** (v1.2) | NVDA, GOOGL, TSLA, AAPL, AMD, MSFT, AMZN, SMCI, PLTR, NFLX, SHOP, MU, DKNG (13) — **META and CRM removed** (0 wins across every MTF config) |
| **W3 Scalper** (v1.4) | 30 names — the Daily core plus AVGO, COIN, MRVL, PANW, ORCL, ABNB, CRWD, APP, ANET, FTNT, SNOW, HOOD, DASH, XYZ, DDOG, ZS, ADBE, CELH, LRCX (curated by in-sample expectancy — see the removed-ticker comment block in the file) |

| Regime ticker | Role |
|---|---|
| **QQQ** | **Long/entry regime gate** — Daily/4H/MTF use QQQ 200-day MA; W3 Scalper uses QQQ 50-day MA. Never traded. |
| **SPY** | **Short-side regime gate only** — `Backtest_Daily.py` loads SPY 200-day MA for the Wave C dual-regime gate. Never traded. |

> 📌 **UNVERIFIED legacy claim:** older notes cited "NVDA 64.3% / TSLA 57.1% / AMD 61.5% WR in v7." Those numbers are not reproduced by any current engine and predate the rewrite — treat them as historical, not current. Latest verified per-engine metrics live in the run-history table below and in [README.md](README.md).
> Indices (SPY/QQQ) are used as regime filters, not traded — they don't produce clean EW structures at this wave degree.

---

## LAYER 1 — Elliott Wave Rules

### The Three Unbreakable Laws
Structural laws. Any violation = count is WRONG. Start over immediately.

| Rule | Law | Invalidation |
|---|---|---|
| **Rule 1** | Wave 2 never retraces more than 100% of Wave 1 | Price breaks below Wave 1 origin |
| **Rule 2** | Wave 3 is never the shortest impulse wave | Wave 3 shorter than Wave 1 AND Wave 5 |
| **Rule 3** | Wave 4 never enters Wave 1's price territory | Wave 4 low breaks below Wave 1 high |

### Wave Characteristics

| Wave | Character | Volume | Action |
|---|---|---|---|
| Wave 1 | Weak, unnoticed | Average | Watch only |
| Wave 2 | Sharp pullback, fear | **Declining** | **Prepare long entry** |
| Wave 3 | Strongest, explosive | **Highest** | **BUY CALLS — primary long trade** |
| Wave 4 | Choppy, overlapping | Declining | Take partial profits, watch for W5 |
| Wave 5 | Final push, RSI divergence | Below Wave 3 | Close calls, prepare for A-B-C |
| Wave A | First correction leg down | Rising | Watch — prepares the short setup |
| Wave B | Trap bounce, partial retrace | **Declining** | **BUY PUTS — primary short trade** |
| Wave C | Violent decline = Wave A length | Rising | **Ride puts to target** |

### Corrective Patterns (for Wave C short setups)

**Zigzag (5-3-5)** — Sharpest correction. Wave C = Wave A length exactly. Most tradeable for puts — high R:R.

**Flat (3-3-5)** — Wave B retraces ~100% of Wave A. Wave C is the danger move. Common bull trap — watch for exhaustion at Wave B high.

**Triangle (3-3-3-3-3)** — Only in Wave 4 or Wave B position. Signals one final thrust after breakout. Wait for the breakout candle before entering.

### No Trade Rule
> If two valid wave counts exist simultaneously → **NO TRADE.** Do not force a count. Ambiguity kills accounts.

---

## LAYER 2 — Fibonacci Levels

### Critical Anchor Rule (Fixed in v7)
**Extensions project from the C point (Wave 2 low for longs, Wave B high for shorts) — NOT from the B point.**

```
LONG:  A = W1 start | B = W1 end | C = W2 low  → extend UP from C
SHORT: A = Wave A start (high) | B = Wave A end (low) | C = Wave B high → extend DOWN from C
```

### Key Fib Relationships — LONG

| Level | Meaning |
|---|---|
| W2 retracement 50% | Primary entry zone — Grade A |
| W2 retracement 61.8% | Primary entry zone — Grade A |
| W2 retracement 78.6% | Deep but valid — Grade B, reduce size |
| W2 retracement >78.6% | DO NOT ENTER — W1 significance breaks down |
| W2 retracement >100% | Rule 1 violated — no trade, wave count is invalid |
| **T1: W2_low + W1_length × 1.0** | First target — close 50% of position |
| **T2: W2_low + W1_length × 1.618** | Final target — close remaining 50% |
| Extended T2: W2_low + W1_length × 2.618 | Strong trend continuation scenario |

### Key Fib Relationships — SHORT (Wave C)

| Level | Meaning |
|---|---|
| Wave B retracement 50% | Primary short entry zone — Grade A |
| Wave B retracement 61.8% | Primary short entry zone — Grade A |
| Wave B retracement 78.6% | Deep bounce — Grade B, reduce size |
| Wave B retracement >78.6% | Potential new impulse up — NO TRADE |
| Wave B exceeds Wave A origin | Wave count invalid — NO TRADE |
| **T1: WB_high − WA_length × 1.0** | First target — close 50% |
| **T2: WB_high − WA_length × 1.618** | Final target — close remaining 50% |

### Fib Hard Rules
- **F1**: Draw Fib only from CONFIRMED swing points — never assumed ones
- **F2**: A Fib level alone is insufficient — must align with at least one confirmation filter
- **F3**: Entry zone = 50%–78.6% only. Outside this range = no trade
- **F4**: Entry zone = Fib level ± 0.5% of price (a zone, not a pin)
- **F5**: Always anchor extensions from C point. Anchoring from B overstates targets significantly

---

## LAYER 3 — Support & Resistance

### S/R Strength Ranking

| Type | Strength | Notes |
|---|---|---|
| Round numbers ($400, $450, $500) | ⭐⭐⭐⭐⭐ | Psychological magnets — always mark |
| Prior major highs/lows | ⭐⭐⭐⭐⭐ | Multi-month turning points |
| Prior breakout levels | ⭐⭐⭐⭐ | Old resistance = new support (and vice versa) |
| Gap fill levels | ⭐⭐⭐ | Daily chart gaps price tends to revisit |
| 50/200 daily moving averages | ⭐⭐⭐ | Dynamic S/R when price has respected recently |

### S/R Hard Rules
- **SR1**: Mark S/R on DAILY chart first, confirm on 4H. Ignore 1H-only levels as primary.
- **SR2**: A level must be tested at least TWICE to be confirmed S/R.
- **SR3**: The more tests a level survives, the stronger — until it breaks and flips.

---

## LAYER 4 — Confirmation Filters

These filters are validated in the backtest engine (v5+) and are NON-NEGOTIABLE for Grade A setups.

### RSI Filter (RSI-14)

| Setup | RSI Rule |
|---|---|
| **LONG — at W2 bottom bar** | RSI < 55 (corrective territory — not in a fresh bull push) |
| **LONG — at entry confirmation bar** | RSI must be RISING vs RSI at W2 bottom (momentum turning up) |
| **SHORT — at Wave B top bar (SPY BEAR regime)** | RSI > 55 — bounce above neutral; room to fall in bear context |
| **SHORT — at Wave B top bar (SPY BULL regime)** | RSI > 65 — bull bounces run hotter; higher bar required |
| **SHORT — at entry confirmation bar** | RSI must be FALLING vs RSI at Wave B top (momentum turning down) |

> Rationale: RSI filter eliminates false reversals. At a genuine W2 bottom, RSI is in corrective territory and turns up on W3 launch. At a genuine Wave B top, RSI must be elevated (not already weakening) and then turn down on the confirmation bar — both conditions together confirm the trap is sprung, not just drifting. The higher bull-regime threshold (**65 vs 55**, per `Backtest_Daily.py`: `RSI_BULL_WB_TOP = 65`, `RSI_MIN_AT_WB_TOP = 55`) reflects that in a bull market, Wave B bounces routinely carry RSI into the 60s before exhausting; only when RSI reaches that higher level in a bull context is the reversal meaningful.

### Volume Filter

| Setup | Rule |
|---|---|
| **LONG — Wave 2 bars** | Trailing 5-bar volume average must be BELOW Wave 1 average volume |
| **SHORT — Wave B bars** | Trailing 5-bar volume average must be BELOW Wave A average volume |

> Rationale: W2 and Wave B should come on declining volume — crowd conviction is fading. High volume during the retracement/bounce suggests continuation, not exhaustion.

### Trend Alignment Filter (50 MA)

| Setup | Rule |
|---|---|
| **LONG** | Entry confirmation close must be ABOVE the 50-day MA |
| **SHORT** | Entry confirmation close must be BELOW the 50-day MA |

> Rationale: Trading with the 50 MA direction reduces counter-trend noise. Checked at entry bar (not W1 formation) so major bull runs that start below the MA qualify once the trend is confirmed.

### Macro Regime Filter

> **What the code actually uses:** the **long / entry regime is gated on QQQ**, not SPY. All four engines set `REGIME_TICKER = "QQQ"` (Daily/4H/MTF gate on QQQ 200-day MA; W3 Scalper gates on QQQ 50-day MA). QQQ is the tech-index proxy that matches the growth universe we trade. **SPY is used only for the short side** — `Backtest_Daily.py` loads SPY *separately* for the Wave C dual-regime gate below. (Note: `Yfinancedata.py` does not download QQQ by default — fetch it, or the regime silently falls back to "always on.")

| Setup | Rule |
|---|---|
| **LONG only** | **QQQ** must be ABOVE its 200-day MA on the entry date (50-day MA for the W3 Scalper) |
| **SHORT — Grade A** | **SPY** BELOW its 200-day MA (bear regime) AND stock below its own 200 MA |
| **SHORT — Grade B** | **SPY** ABOVE its 200-day MA BUT stock is ≥5% below its own 200 MA (structural underperformer) |
| **SHORT — NO TRADE** | SPY above 200 MA AND stock <5% below own 200 MA, OR stock above its own 200 MA |

> Rationale: Longs gate on QQQ because the universe is tech/growth — QQQ tracks that beta far better than the broad S&P. Shorts gate on SPY (the macro benchmark) because the Wave C short thesis is about *market-wide* risk-off, not sector rotation. Empirically, winning shorts fired in a bear SPY regime while failing shorts fired in bull regimes; Wave C corrections in bull markets are shallow, fast, and frequently become new impulse highs — especially in secular growth names. The dual-regime gate keeps Grade A shorts reserved for genuine bear markets while allowing Grade B shorts on structural stock-level breakdowns within a bull macro environment.
>
> ⚠️ **Reality check:** on the latest run the short side fired only 4 trades at **0% win rate** — the Wave C short is currently a net loser and is flagged for a fix-or-retire decision. Do not trade it live.

### Earnings Veto Filter (added 2026-07-05)

| Setup | Rule |
|---|---|
| **Daily (long + short) and MTF entries** | NO entry if the ticker's next earnings report is ≤ **10 calendar days** away (`events.py`: `EARNINGS_VETO_DAYS = 10`) |
| **Post-earnings** | No restriction — scanning continues; an entry right after the print is allowed |
| **W3 Scalper** | **EXEMPT** — no earnings filter |

> Rationale (tested on 458 historical trades — `results/event_analysis_trades.csv`): entries 0–10 days before earnings won 58–59% at +2.5–4.1%/trade vs 67–73% at +6.7–7.4% when clear of earnings; **46% of MTF stop-outs exited within 3 days after an earnings print** (gaps blowing through the structural stop). Post-earnings entries were the *best* bucket (+9.9%) so only the pre-earnings window is vetoed. W3 is exempt because its pre-earnings entries performed fine (65.5% WR) — breakout momentum is sometimes earnings-driven. For live options the rule matters even more than the equity backtest shows: entering long premium right before earnings means paying peak IV. Calendar cache: `data/earnings_dates.csv`, refresh with `python events.py`.
>
> Impact when added (same data window, 2026-07-05): MTF 47→41 trades, WR 51.1→56.1%, E +1.05→+2.04%, PF 2.11→2.79. Daily LONG 135→122 trades, E +3.6→+5.04%, PF 2.53→3.27, MaxDD −72.3→−44.6%.

---

## SETUP GRADING

### Grade A ✅ — Full Size (5% of account)

**LONG (Wave 3):**
- [ ] Clear, unambiguous wave count — no valid alternative exists
- [ ] All three EW rules verified with measured price levels
- [ ] Wave 1 impulse is ≥ 7% (smaller = noise, not a valid impulse wave)
- [ ] Wave 2 retracement: 50%–61.8% of Wave 1
- [ ] Wave 2 volume: trailing 5-bar average BELOW Wave 1 average
- [ ] RSI(14) at W2 bottom bar: < 55
- [ ] RSI(14) at entry bar: ABOVE RSI at W2 bottom (momentum turning up)
- [ ] Entry confirmation bar closes ABOVE W2 bottom bar's high
- [ ] Entry close is ABOVE the 50-day MA
- [ ] SPY is ABOVE the 200-day MA on entry date
- [ ] Fib level aligns with confirmed S/R (tested 2+ times)
- [ ] R:R ≥ 1.5 using T2 as reward target
- [ ] Next earnings report is MORE than 10 calendar days away (earnings veto)

**SHORT — Grade A (Wave C) — SPY BEAR regime, 5% of account:**
- [ ] Clear A-B-C corrective structure — no valid alternative
- [ ] SPY is BELOW its 200-day MA (macro bear regime confirmed)
- [ ] Wave A impulse down is ≥ 7%
- [ ] Wave B retracement: 50%–61.8% of Wave A (upward bounce)
- [ ] Wave B does NOT exceed Wave A origin (if it does, count is invalid)
- [ ] Wave B spans ≥ 5 bars (no one-day spike reversals)
- [ ] Wave B volume: trailing 5-bar average BELOW Wave A average
- [ ] RSI(14) at Wave B top bar: > 55 (bounce above neutral in bear context — room to resume decline)
- [ ] RSI(14) at entry bar: BELOW RSI at Wave B top (momentum turning down)
- [ ] Entry confirmation bar closes BELOW Wave B top bar's low
- [ ] Entry close is BELOW the 50-day MA
- [ ] Stock is BELOW its own 200-day MA
- [ ] Fib level aligns with confirmed S/R (tested 2+ times)
- [ ] R:R ≥ 1.5 to T1 (exit 100% at T1 — Wave C rarely reaches 161.8%)
- [ ] Next earnings report is MORE than 10 calendar days away (earnings veto)

**SHORT — Grade B (Wave C) — SPY BULL regime, 2.5% of account:**
- [ ] All structural rules met (Wave A ≥7%, Wave B 50–78.6%, ≥5 bars, count unambiguous)
- [ ] SPY is ABOVE its 200-day MA (bull regime — harder execution bar applies)
- [ ] Stock is ≥ 5% BELOW its own 200-day MA (structural underperformer, not a temporary dip)
- [ ] RSI(14) at Wave B top bar: > 65 (higher threshold required — bull bounces run hotter before exhausting)
- [ ] RSI(14) at entry bar: BELOW RSI at Wave B top
- [ ] Entry confirmation bar closes BELOW Wave B top bar's low
- [ ] Entry close is BELOW the 50-day MA
- [ ] R:R ≥ 1.5 to T1

### Grade B 🔶 — Half Size (2.5% of account)
- **LONGS**: All Grade A criteria met BUT retracement is 61.8%–78.6% (deeper W2 — higher risk)
- **SHORTS in BULL regime**: see Grade B short checklist above
- OR one confirmation filter (volume, RSI, or S/R alignment) is borderline — not clearly failing

### No Trade 🚫
- Ambiguous wave count with two valid alternatives
- Any EW rule unverifiable with exact price levels
- Retracement outside 50%–78.6% range
- RSI filter fails in either direction
- Price on wrong side of 50 MA at entry
- For longs: QQQ below 200 MA
- For shorts: SPY above 200 MA AND stock less than 5% below its own 200 MA
- Earnings within 10 calendar days (Daily/MTF setups — W3 Scalper exempt)

---

## OPTIONS EXECUTION RULES

### Strike Selection

| Setup | Strike Rule |
|---|---|
| Wave 3 long | ATM or 1 strike OTM call. Target = T2 (W2_low + W1_len × 1.618). |
| Wave C short | ATM or 1 strike OTM put. Target = T2 (WB_high − WA_len × 1.618). |
| Bull debit spread | Buy ATM call, sell call at T1 level. Reduces cost 40–60%, caps upside at T1. |
| Bear debit spread | Buy ATM put, sell put at T1 level. Reduces cost 40–60%, caps downside at T1. |

### Expiry Rules
- **EX1**: Buy minimum 90 DTE options on new positions. Plan to exit by day 75–80.
- **EX2**: Never buy options expiring in less than 21 days on a new position.
- **EX3**: Prefer monthly expirations (3rd Friday) over weeklies for defined-duration trades.
- **EX4**: Wave 3 (daily chart) typically resolves in 15–30 bars. 90 DTE provides adequate buffer.

### Position Sizing
- **PS1**: No single position exceeds 5% of account (Grade A) or 2.5% (Grade B)
- **PS2**: Maximum 3 open options positions simultaneously (long + short combined)
- **PS3**: Never average down on a losing options position
- **PS4**: Long + short positions can be held simultaneously if on different tickers

### Stop Loss & Target Management

**LONG stops:**
- **SL1**: Stop = W1 origin × 0.999 — wave count is invalidated if W2 exceeds W1 start
- **SL2**: Wave count invalidated = close position immediately, no debate, no holding

**SHORT stops:**
- **SL3**: Stop = Wave A origin × 1.001 — wave count invalidated if Wave B exceeds Wave A start
- **SL4**: Wave count invalidated = close position immediately

**Both directions — target management:**
- **T1**: Close 50% of position. Move stop to breakeven (entry price) immediately.
- **T2**: Close remaining 50%. Full exit.
- **After T1 hit**: Worst case is breakeven on full position. The trade cannot become a full loss.

**Fib extension anchors (critical):**
- LONG T1: `W2_low + W1_length × 1.0`
- LONG T2: `W2_low + W1_length × 1.618`
- SHORT T1: `WB_high − WA_length × 1.0`
- SHORT T2: `WB_high − WA_length × 1.618`

---

## PRE-TRADE CHECKLISTS

The full LONG (Wave 3) and SHORT (Wave C) pre-trade checklists live in **[Checklists_EW.md](Checklists_EW.md)** — run the matching one before every trade. Any unchecked box = not Grade A.

---

### MTF v1 — Multi-TimeFrame Cascade (Backtest_MTF.py)

**Architecture**: Daily scanner validates W1–W2 structure → 4H sub-scanner times entry inside the daily fib zone. Entry fires on the 4H reversal bar (not the daily close), so entry sits closer to the W2 bottom. Targets anchored to the 4H W2 low. Config lives in `Backtest_MTF.py` — see that file for exact parameter values.

**Run history (4H window rolls forward with yfinance's ~730-day 1H cap):**

| Run | Tickers | Trades | WR | Expectancy | PF | CAGR | MaxDD |
|---|---|---|---|---|---|---|---|
| v1.0 | 12 | 39 | 41.0% | −1.1% | 1.17 | +2.0% | −61% |
| v1.1 | 15 | 51 | 45.1% | +0.02% | 1.56 | +12.35% | −61% |
| v1.2 (recorded) | 15 | 52 | 46.2% | +0.30% | 1.64 | +13.69% | −61% |
| v1.2 — verified 2026-07-05 | 13 | 47 | 51.1% | +1.05% | 2.11 | +18.4% | −57.2% |
| **v1.3 — earnings veto, 2026-07-05** | **13** | **41** | **56.1%** | **+2.04%** | **2.79** | **+19.2%** | **−63.1%** |

> The v1.2 verified row differs from the earlier recorded v1.2 because (a) the 1H data window rolled forward ~13 months, and (b) QQQ regime now actually loads (earlier runs may have silently fallen back to "regime always on" when QQQ wasn't downloaded). **Config is unchanged** — this is a data-window effect, not a parameter change. Ticker count is 13 (META and CRM are excluded from MTF), not 15. NVDA still carries the book (WR 60%, E +5.4%, PF 4.4).
>
> **v1.3** adds the earnings veto (no entry ≤10d before the ticker's earnings — see the Earnings Veto Filter in Layer 4). Same data window as the v1.2 verified row, so the improvement (WR +5 pts, expectancy nearly doubled) is attributable to the veto alone. The 6 removed trades were net losers.

**Validated findings (in-sample — pending walk-forward):**
- **MAX_RR ≤ 2.5 cap helps.** High R:R = stop (W1 origin) sits too far below entry = loose setup. Capping lifted WR 37%→41%.
- **Loosening daily filters BACKFIRES.** Removing the volume + MA-slope filters tripled trades (39→113) but blew MaxDD to −75% and turned expectancy negative. The daily filters protect the system. **Do not loosen to chase trade count.**
- **Filter-loosening grid (v1.2 test):** MAX_RR↑ → fewer-quality trades (E goes negative). FH_RSI<60 is **inert** (loosening to 70 changes nothing — not the bottleneck). Widening fib to 38–88% adds 9 trades + best E (+0.95%) BUT drawdown → −72%. Only safe loosening found: **MIN_RR 1.5→1.0** (WR 45→46%, E +0.02→+0.30%, DD unchanged) — applied in v1.2.
- **The 4H stage kills ~63% of daily zones (87 of 138).** This is cascade geometry (a 4H reversal must print inside the daily zone's window), not an over-tight knob. Not a bug to "fix."
- **Grow universe, not filters.** Candidate screen hit rate was 5/12 (~42%) — the edge is real but selective. Added SHOP (clean target-driven wins), MU (legit, semis); DKNG added as **watch** — its profit is timeout/drift-driven, not target hits, so it's likely regime-dependent.
- **CRM, AMD, META: 0 wins across every config.** AMD was 61.5% WR in v7 daily — its edge is daily-only; 4H timing destroys it. Retained per decision; flagged for review.
- **Data ceiling**: yfinance 1H history caps at ~730 days, so 4H can't reach the 2022 bear. Sample grows via breadth only.

> ⚠️ **Live risks (updated to verified numbers)**: (1) Expectancy is +1.05%/trade on only **47 trades** — thin sample, and NVDA alone (E +5.4%) carries it; strip NVDA and the edge is marginal. (2) **MaxDD −57.2% / Calmar 0.32 remains the unsolved problem** — universe expansion never touched tail risk. (3) All numbers are **in-sample** on a window that has *never contained a real bear market* (the 730-day 1H cap can't reach 2022). **Drawdown control + walk-forward validation are required before any capital.**

---

### W3 Scalper (Backtest_W3_Scalper.py) — v1.4

**Independent** fast-momentum engine (does not consume Daily/MTF output). Looser filters, wider universe (30 names), short holds (~25d). Hunts the Wave 3 breakout directly: W0 low → W1 high (≥4%) → W2 pullback (38.2–70%, RSI<65) → enter on first close above W1 high + 0.1% with volume surge and rising RSI. Exits 100% at T1 (1.618× W1 from W2 low); QQQ MA50 regime gate; blocks entries at VIX ≥ 25.

**Verified 2026-07-05 (in-sample):** 30 tickers | **271 trades | WR 33.2% | E +6.56%/trade | PF 4.11 | CAGR +33.9% (10% sizing) | MaxDD −43.2%** | avg hold 19.2d.

> ⚠️ **Read the WR honestly:** win rate is only 33% and **54.6% of trades are TIMEOUTS** (avg +4.62%). The positive expectancy comes largely from small-positive timeouts drifting up, not from clean T1 hits — this is momentum drift capture, not a high-hit-rate system. Its ticker universe is curated by in-sample expectancy (removed-ticker comment block in the file), which is a real overfitting risk. Top names by E: APP, HOOD, CELH, AMD, MU.

---

## CURRENT FOCUS

**Daily Engine (v11)**
- [x] Elliott Wave rules defined and validated
- [x] Fibonacci levels corrected — anchor at C point confirmed
- [x] Backtest engine v11 live with long + short scanner (dual-regime short gate + RSI gate added)
- [ ] **Fix or retire the Wave C short** — 5 trades, 0% WR, net loser on the latest run
- [ ] Populate a full per-ticker Daily results table

**MTF Cascade (Backtest_MTF.py)**
- [x] MTF architecture designed — daily zones → 4H precision entry
- [x] `scan_daily_zones()` — full structural filters (W1, RSI, vol, MA, regime)
- [x] `find_4h_entry()` — 4H reversal confirmation within daily zone
- [x] `simulate_mtf_trades()` — 4H bar simulation with T1 trailing stop
- [x] Full metrics suite — CAGR, Sharpe, Sortino, Calmar, MaxDD, PF, WR
- [x] Download data — `Yfinancedata.py` (now includes QQQ + SPY regime tickers)
- [x] Execute MTF backtest run — results table above (verified 2026-07-05)
- [x] Populate MTF results table above
- [ ] **Walk-forward / out-of-sample validation** on MTF signals — still the gating step before capital
- [ ] Compare MTF vs Daily: entry-price delta and R:R improvement

**Next Milestones**
- [ ] **Drawdown control** — portfolio-level (correlation caps, position sizing, max-DD stop). Blocks everything.
- [ ] **Model option P&L** — current backtests are underlying-only
- [x] Console live scanner exists (`Scanner_Live.py`) — W3 + Daily signal cards
- [ ] Add Wave 5 scanner (third long setup — final push entry)
- [ ] Upgrade the scanner to a Streamlit dashboard / alerter
- [ ] Paper trade first qualifying setup on Alpaca
