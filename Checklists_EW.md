# CHECKLISTS_EW.md — Pre-Trade Checklists

Companion to [Strategy_EW.md](Strategy_EW.md). Run the matching checklist before every trade. Any unchecked box = not Grade A.

---

## PRE-TRADE CHECKLIST — LONG (Wave 3)

```
WAVE COUNT
[ ] Wave 1 start and end price confirmed and recorded
[ ] Wave 1 impulse is ≥ 7% (if smaller → NO TRADE)
[ ] Wave 2 retracement measured: 50%–78.6% of Wave 1
[ ] Wave 2 does NOT exceed Wave 1 origin (Rule 1)
[ ] No alternative valid count exists
[ ] Wave 3 is not the shortest wave (Rule 2) — confirm after W3 develops

FIBONACCI
[ ] Fib drawn A=W1_start, B=W1_end, C=W2_low
[ ] W2 retracement: 50%–61.8% = Grade A | 61.8%–78.6% = Grade B
[ ] T1 = W2_low + W1_length (record price level: _______)
[ ] T2 = W2_low + W1_length × 1.618 (record price level: _______)
[ ] Invalidation = W1 origin (record price level: _______)

CONFIRMATION FILTERS
[ ] RSI(14) at W2 bottom bar: < 55 (record value: _______)
[ ] RSI(14) at entry bar: ABOVE RSI at W2 bottom
[ ] Wave 2 trailing 5-bar volume BELOW Wave 1 average volume
[ ] Entry bar close ABOVE W2 bottom bar's high (reversal confirmed)
[ ] Entry bar close ABOVE 50-day MA
[ ] 50-day MA is RISING (slope over last 5 bars > 0) — code enforces this
[ ] QQQ close ABOVE QQQ 200-day MA on entry date (the long regime gate is QQQ, not SPY)

SUPPORT & RESISTANCE
[ ] Key S/R level on DAILY chart aligns with W2 retracement zone
[ ] S/R level tested minimum 2 times previously
[ ] Fib level and S/R within 0.5% of each other

EVENT RISK
[ ] Next earnings date checked: ____________
[ ] Earnings MORE than 10 calendar days away — if ≤10d → NO TRADE (earnings veto)
    (IV is also pumped pre-earnings — you'd overpay for the option even if direction is right)

OPTIONS
[ ] Grade assigned: A (5%) / B (2.5%) / NO TRADE
[ ] Strike: ATM or 1 OTM call
[ ] Expiry: ≥ 90 DTE minimum
[ ] R:R ≥ 1.5 confirmed (reward = T2 − entry | risk = entry − stop)
[ ] Max position: 5% of account (Grade A) | 2.5% (Grade B)
[ ] T1 price level noted for partial exit trigger
[ ] Stop (invalidation) price level noted

RESULT: [ ] TRADE  [ ] NO TRADE — Reason: ___________
```

---

## PRE-TRADE CHECKLIST — SHORT (Wave C)

> ⚠️ **The Wave C short is currently a net loser** (latest backtest: 4 trades, 0% win rate). It lives only in `Backtest_Daily.py` and is flagged for a fix-or-retire decision. **Do not trade it live** until it is re-validated. This checklist documents the intended rules as coded.

```
WAVE COUNT
[ ] Wave A start (high) and end (low) price confirmed and recorded
[ ] Wave A impulse down is ≥ 7% (if smaller → NO TRADE)
[ ] Wave B retracement measured: 50%–78.6% of Wave A (upward)
[ ] Wave B does NOT exceed Wave A origin — if it does → NO TRADE (count invalid)
[ ] Corrective pattern identified: Zigzag / Flat / Triangle (note which)
[ ] No alternative valid count exists

FIBONACCI
[ ] Fib drawn A=WA_start(high), B=WA_end(low), C=WB_high
[ ] Wave B retracement: 50%–61.8% = Grade A | 61.8%–78.6% = Grade B
[ ] T1 = WB_high − WA_length (record price level: _______)
[ ] T2 = WB_high − WA_length × 1.618 (record price level: _______)
[ ] Invalidation = Wave A origin (record price level: _______)

CONFIRMATION FILTERS
[ ] RSI(14) at Wave B top bar: > 55 if SPY BEAR regime / > 65 if SPY BULL regime (record value: _______)
    (matches Backtest_Daily.py: RSI_MIN_AT_WB_TOP=55, RSI_BULL_WB_TOP=65)
[ ] RSI(14) at entry bar: BELOW RSI at Wave B top (momentum turning down)
[ ] Wave B trailing 5-bar volume BELOW Wave A average volume
[ ] Entry bar close BELOW Wave B top bar's low (reversal confirmed)
[ ] Entry bar close BELOW 50-day MA
[ ] Wave B spans ≥ 5 bars from Wave A low (no one-day spike reversals)

REGIME GATE (dual-regime, per Backtest_Daily.py)
[ ] Stock is BELOW its own 200-day MA (mandatory — above MA200 = NO TRADE)
[ ] SPY BELOW its 200-day MA → Grade A (RSI bar = 55)
[ ] SPY ABOVE its 200-day MA → Grade B, and stock must be ≥5% below its own MA200 (RSI bar = 65)
[ ] Neither condition met → NO TRADE

SUPPORT & RESISTANCE
[ ] Key S/R level on DAILY chart aligns with Wave B retracement zone
[ ] S/R level tested minimum 2 times previously
[ ] Fib level and S/R within 0.5% of each other

EVENT RISK
[ ] Next earnings date checked: ____________
[ ] Earnings MORE than 10 calendar days away — if ≤10d → NO TRADE (earnings veto)

OPTIONS
[ ] Grade assigned: A (5%) / B (2.5%) / NO TRADE
[ ] Strike: ATM or 1 OTM put
[ ] Expiry: ≥ 90 DTE minimum
[ ] R:R ≥ 1.5 confirmed (reward = entry − T1 | risk = stop − entry) — shorts size R:R to T1, exit 100% at T1
[ ] Max position: 5% of account (Grade A) | 2.5% (Grade B)
[ ] T1 price level noted for partial exit trigger
[ ] Stop (invalidation) price level noted

RESULT: [ ] TRADE  [ ] NO TRADE — Reason: ___________
```
