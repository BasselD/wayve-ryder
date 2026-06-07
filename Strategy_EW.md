

# STRATEGY_EW.md — Elliott Wave + Fib + S/R Options System

## Strategy Overview

**Thesis**: Markets move in predictable fractal wave structures driven by crowd psychology. By identifying wave position and confirming with Fibonacci levels, momentum, volume, and trend alignment, we can pinpoint high-probability options entry points with defined risk in both directions.

**Two primary setups:**
- **Wave 3 LONG** → Buy calls / bull debit spread — enter at Wave 2 completion
- **Wave C SHORT** → Buy puts / bear debit spread — enter at Wave B trap bounce completion

**Planned (not yet in backtest):**
- Wave 5 long → Calls at reduced size (final push before A-B-C correction)

**Trading Universe:**

| Ticker | Type | Notes |
|---|---|---|
| NVDA | Primary long + short | High-beta AI leader, clean EW structures |
| TSLA | Primary long + short | High-beta momentum, strong W3 moves |
| AMD | Primary long + short | High-beta tech, NVDA-correlated |
| GOOGL | Secondary long + short | Large-cap tech, lower volatility |
| AAPL | Secondary long + short | Liquid, steady structures |
| META | Secondary long + short | Volatile, monitor carefully |
| **SPY** | **Regime filter ONLY** | Never traded — used to gate long setups |
| **QQQ** | **Regime filter ONLY** | Never traded — macro reference only |

> Backtesting proof: NVDA 64.3% WR, TSLA 57.1% WR, AMD 61.5% WR in v7 long-only system.
> SPY and QQQ consistently produced 0–16% win rates across all versions — indices do not produce clean EW structures at this wave degree.

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
| **SHORT — at Wave B top bar** | RSI > 45 (not already oversold — still has room to fall) |
| **SHORT — at entry confirmation bar** | RSI must be FALLING vs RSI at Wave B top (momentum turning down) |

> Rationale: RSI filter eliminates false reversals. At a genuine W2 bottom, RSI is in corrective territory and turns up on W3 launch. At a genuine Wave B top, RSI is elevated relative to the correction and turns down on Wave C launch.

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

### Macro Regime Filter (SPY 200 MA)

| Setup | Rule |
|---|---|
| **LONG only** | SPY must be ABOVE its 200-day MA on the entry date |
| **SHORT** | No regime filter — Wave C corrections occur in all market regimes |

> Rationale: Long setups in a bear market (SPY below 200 MA) face macro headwind that overrides individual stock EW structures. Short/Wave C setups profit from corrections that occur regardless of macro regime.

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

**SHORT (Wave C):**
- [ ] Clear A-B-C corrective structure — no valid alternative
- [ ] Wave A impulse down is ≥ 7%
- [ ] Wave B retracement: 50%–61.8% of Wave A (upward bounce)
- [ ] Wave B does NOT exceed Wave A origin (if it does, count is invalid)
- [ ] Wave B volume: trailing 5-bar average BELOW Wave A average
- [ ] RSI(14) at Wave B top bar: > 45
- [ ] RSI(14) at entry bar: BELOW RSI at Wave B top (momentum turning down)
- [ ] Entry confirmation bar closes BELOW Wave B top bar's low
- [ ] Entry close is BELOW the 50-day MA
- [ ] Fib level aligns with confirmed S/R (tested 2+ times)
- [ ] R:R ≥ 1.5 using T2 as reward target

### Grade B 🔶 — Half Size (2.5% of account)
- All Grade A criteria met BUT retracement is in the 61.8%–78.6% zone (deeper — higher risk)
- OR one confirmation filter (volume, RSI, or S/R alignment) is borderline — not clearly failing

### No Trade 🚫
- Ambiguous wave count with two valid alternatives
- Any EW rule unverifiable with exact price levels
- Retracement outside 50%–78.6% range
- RSI filter fails in either direction
- Price on wrong side of 50 MA at entry
- For longs: SPY below 200 MA

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

**Run history (2023–2026, ~2.9yr 4H window):**

| Run | Tickers | Trades | WR | Expectancy | PF | CAGR | MaxDD |
|---|---|---|---|---|---|---|---|
| v1.0 | 12 | 39 | 41.0% | −1.1% | 1.17 | +2.0% | −61% |
| v1.1 | 15 (+SHOP, MU, DKNG) | 51 | 45.1% | +0.02% | 1.56 | +12.35% | −61% |
| **v1.2** | **15** (MIN_RR 1.5→1.0) | **52** | **46.2%** | **+0.30%** | **1.64** | **+13.69%** | **−61%** |

v1.1 added 3 tickers from a 12-name candidate screen ([screen_candidates.py](screen_candidates.py)) — flipped expectancy positive and lifted PF/CAGR. NVDA still carries the book.

**Validated findings (in-sample — pending walk-forward):**
- **MAX_RR ≤ 2.5 cap helps.** High R:R = stop (W1 origin) sits too far below entry = loose setup. Capping lifted WR 37%→41%.
- **Loosening daily filters BACKFIRES.** Removing the volume + MA-slope filters tripled trades (39→113) but blew MaxDD to −75% and turned expectancy negative. The daily filters protect the system. **Do not loosen to chase trade count.**
- **Filter-loosening grid (v1.2 test):** MAX_RR↑ → fewer-quality trades (E goes negative). FH_RSI<60 is **inert** (loosening to 70 changes nothing — not the bottleneck). Widening fib to 38–88% adds 9 trades + best E (+0.95%) BUT drawdown → −72%. Only safe loosening found: **MIN_RR 1.5→1.0** (WR 45→46%, E +0.02→+0.30%, DD unchanged) — applied in v1.2.
- **The 4H stage kills ~63% of daily zones (87 of 138).** This is cascade geometry (a 4H reversal must print inside the daily zone's window), not an over-tight knob. Not a bug to "fix."
- **Grow universe, not filters.** Candidate screen hit rate was 5/12 (~42%) — the edge is real but selective. Added SHOP (clean target-driven wins), MU (legit, semis); DKNG added as **watch** — its profit is timeout/drift-driven, not target hits, so it's likely regime-dependent.
- **CRM, AMD, META: 0 wins across every config.** AMD was 61.5% WR in v7 daily — its edge is daily-only; 4H timing destroys it. Retained per decision; flagged for review.
- **Data ceiling**: yfinance 1H history caps at ~730 days, so 4H can't reach the 2022 bear. Sample grows via breadth only.

> ⚠️ **Two live risks**: (1) Expectancy +0.02% is barely positive — fragile. (2) MaxDD −61% / Calmar 0.2 is the real unsolved problem — universe expansion didn't touch tail risk. **Drawdown control is the next priority.** Walk-forward validation still required before any capital.

---

## CURRENT FOCUS

**Daily Engine (v7/v8)**
- [x] Elliott Wave rules defined and validated
- [x] Fibonacci levels corrected — anchor at C point confirmed
- [x] Backtest engine v8 live with long + short scanner
- [x] Win rate target hit on longs: NVDA 64.3%, TSLA 57.1%, AMD 61.5%
- [ ] Run v8 and validate Wave C short performance
- [ ] Populate v8 backtest results table above

**MTF Cascade (Backtest_MTF.py)**
- [x] MTF architecture designed — daily zones → 4H precision entry
- [x] `scan_daily_zones()` — full structural filters (W1, RSI, vol, MA, regime)
- [x] `find_4h_entry()` — 4H reversal confirmation within daily zone
- [x] `simulate_mtf_trades()` — 4H bar simulation with T1 trailing stop
- [x] Full metrics suite — CAGR, Sharpe, Sortino, Calmar, MaxDD, PF, WR
- [ ] Download data — run `Yfinancedata.py` for all 12 tickers (daily + 1H)
- [ ] Execute first MTF backtest run
- [ ] Populate MTF results table above
- [ ] Walk-forward validation on MTF signals
- [ ] Compare MTF v1 vs v7 daily: entry price delta and R:R improvement

**Next Milestones**
- [ ] Add Wave 5 scanner (third long setup — final push entry)
- [ ] Build Streamlit signal scanner / alerter for live monitoring
- [ ] Paper trade first qualifying MTF setup on Alpaca
- [ ] Set portfolio construction rules (correlation limits, max simultaneous exposure)
