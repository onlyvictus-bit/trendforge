# File A draft — R2-B named activation (EXECUTED 2026-08-25)

**Status:** EXECUTED (2026-08-25, ticket 4 of 4,
`R2B_CONFIRMED_AMENDMENT_OPENCODE_PROMPT.md`). The execution checklist below
was satisfied by `selection/r2b_live.py` v2 (observed five-source last-good
flip), S7 amendment gates, and the guidance OMS. Overlay now live:
public CONFIRMED = PRF-003 EOD only; guidance OMS paper tickets + order
preview; gated live placement (env + OPENALGO_RO lane + UI arm, default off);
intraday GUIDANCE confirmation only.

Original draft text follows unchanged for the record.

---

**Status (historical):** DRAFT. Do **not** set `sourceActivationReady=true` from this file until
the execution checklist below is ticked in a later review.

**Purpose:** say which official sources may later support **CONFIRMED**, and
which must stay WAIT/veto, so production can use **useful data at each step**
without qty or broker.

**Still false after this draft exists:** `executable`, qty, broker, Hybrid S4–S9
paste into `r5_live.py`.

---

## Useful data you already get (before CONFIRMED)

| Step | Status | What you can use today |
|---|---|---|
| R2-A list | live | WATCH/WAIT/REJECT names |
| R5 tags | live WAIT | NR7/breakout tags, not buys |
| R14 CA join | live WAIT | adjusted vs WAIT_CA |
| R0-B proof (this change) | 5 proven, MWPL wait | cash/ban/FO/index/CA contracts named and breaker-proven |
| R2-B ledger | live WAIT | `GET /api/v1/selection/named-activation` shows WAIT_PROOF vs NOT_AUTHORIZED |
| CONFIRMED | **not live** | needs this amendment **executed** |

---

## A. R0-B proof split (done in code, 2026-08-22)

**Confirm-path (may be named for later CONFIRMED):** proven when all R0-B
dimensions PASS, including **shared NSE domain** retry/breaker (live in
`DomainCircuitBreaker` fail=3 / cooldown=900s, HTTP retry max 3).

1. `nse_bhavcopy_eod` — cash EOD spine  
2. `nse_fno_ban` — hard F&O ban veto  
3. `nse_fo_bhavcopy` — FO EOD OI/price  
4. `nse_index_close_eod` — index/VIX **companion**, not a 124th voter  
5. `nse_corporate_filings_actions` — CA terms for R14  

`canVote` stays **false** until this amendment is executed.

**Not confirm-eligible (keep using as WAIT/veto data only):**

6. `nse_mwpl_percentages` — **no verified official percentage file**. Parser
   exists for a future artifact. Ban CSV must never be treated as MWPL %.
   Cash ranking continues with `MWPL_MISSING`. Do not invent a URL.

---

## B. Named activation list (execute later)

When executed, **only** the five confirm-path keys above may set
`may_support_confirmed` on claims that already pass R14 + R5 closed-bar
rules. MWPL never supports CONFIRMED.

Then, and only then:

- compiler `sourceActivationReady` may become true **if** `gate_permission`
  is granted for those five keys only  
- `gateAuthorized` may leave 0 for that named set  
- FTR-040 / R5 `LIVE_WAIT_REJECT_ONLY` needs a matching ceiling change  
- `confirmedCount` may leave 0 for matching rows  
- qty remains 0; `executable` remains false  

---

## Tests required before execute (flag flip)

1. `sourceActivationReady=false` ⇒ live CONFIRMED count still 0 (keep forever as regression).  
2. After execute: missing R14 WAIT_CA ⇒ still no CONFIRMED.  
3. After execute: MWPL missing ⇒ cash may still CONFIRMED if named path passes; MWPL cannot be the confirming family.  
4. Ban list hit ⇒ REJECT/WAIT, never CONFIRMED.  
5. Index companion mismatch ⇒ WAIT_INDEX, not invented Nifty.  
6. qty fields remain 0 / null.  
7. POST named-activation still 405.

---

## What you do next (operator)

1. Use today’s proven five sources as **research data** (already flowing).  
2. Do **not** ask to flip the flag yet.  
3. When you want the first CONFIRMED stamp: review this draft, tick the tests,
   then a later change-set executes §B. That change-set is the real signature.
