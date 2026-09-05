# OPENCODE BUILD PROMPT — 3/4 R12 options walls + Greeks as S6 claims
## OI rooms stay views · walls/Greeks claims · **dealer-GEX guidance** · **options-only guidanceConfirmed**

**Also read:** `docs/fable/remaining_build/TRADE_GUIDANCE_LAW_2026-08-25.md`

Copy **this entire file**. Load skills. Think. Build. Run **§9 GATES**.

Working tree: `D:\TrendForge`  
Python: `D:\TrendForge\.venv\Scripts\python.exe`  
OS: Windows. PowerShell. `;` not `&&`.  
**Date: 2026-08-25.** Ticket **3 of 4**. File A **R12** (+ S5 enrich / S6 resolve). OI Analysis / Tracker / Strike / Expiry rooms are **views** — do not rebuild them as the claim owner.

Skills: `using-superpowers` → `unlazy` → `verification-before-completion` → `systematic-debugging` → `requesting-code-review`.

Authority: File A R12 / §9 S5–S6 / FMR-003..007. `docs/OPTIONS_INTELLIGENCE_PLAN.md` (one OPTIONS_PACKAGE; GEX `SCENARIO_ONLY_NOT_OBSERVED_POSITION`). Hybrid §16.8 derivatives only where File A points. Existing: `options_intelligence/`, `oi-options-live.js`, S5 `OPTIONS_PACKAGE=UNKNOWN_NEEDS_R12`.

---

## 0. This ticket IS / IS NOT

| IS | IS NOT |
|---|---|
| Mint **typed EvidenceClaims** for walls / PCR path / greeks **labels** into S5→S6 | Replacing OI room BFFs as public-state owner |
| One family `OPTIONS_CONTEXT` / group `CG_OPTION_CHAIN` | Second options fuse / Combined_Score |
| Free EOD: UDiFF FO + last-good chain; OpenAlgo chain only if data-lane OPENALGO_RO | Yahoo options |
| Options claims into S6 | Replacing OI rooms as File A public-state owner |
| **Dealer-GEX as scenario trade guidance** | Storing GEX as observed dealer inventory (still not a fact) |
| **`guidanceConfirmed` from options-only** when walls+structure align | Flipping File A **public** CONFIRMED from PCR alone (that is ticket 4 + S7) |
| Unknown chain → UNKNOWN, score 0 | Combined_Score |

---

## 0.1 Outcome (observed)

1. S5 enrichment: `optionsPackage` is no longer stuck `UNKNOWN_NEEDS_R12` **when** a usable official FO/chain snapshot exists for that symbol/expiry; otherwise stays UNKNOWN (honest).  
2. S6 family map shows `OPTIONS_CONTEXT` support/oppose/missing from those claims. Removing options **must not upgrade** public state (File A §9.6.2).  
3. Walls = strike OI concentration **observation**. Greeks = model labels. Signed GEX = **dealer-GEX guidance** with `SCENARIO_ONLY_NOT_OBSERVED_POSITION` + copy “guidance, not observed dealers”.  
4. When options package is complete, set **`guidanceConfirmed=true`** (options-only **guidance** confirm). S7 File A `publicState` stays WAIT unless ticket 4 unlocked cash CONFIRMED. UI chip: `OPTIONS_GUIDANCE_CONFIRMED`.  
5. Dual-lane OFF: UDiFF. Lane ON: OpenAlgo chain overlay `BROKER_ORIGINATED`.

---

## W. Folder map

```text
CREATE
  D:\TrendForge\backend\trendforge_api\selection\r12_options_claims.py
  D:\TrendForge\backend\tests\test_r12_options_claims.py
  D:\TrendForge\delete\gates_r12_claims_2026-08-25\GATES.md

EXTEND (smallest)
  D:\TrendForge\backend\trendforge_api\selection\s5_shortlist_enrichment.py
      call r12 claim mint; stop hardcoding UNKNOWN_NEEDS_R12 when snapshot usable
  D:\TrendForge\backend\trendforge_api\selection\s6_family_resolution.py
      ingest OPTIONS_CONTEXT claims from S5 (if not already)
  D:\TrendForge\backend\trendforge_api\options_intelligence\   reuse surface/flow
  frontend: inspector Derivatives tab may **read** package status; no new nav
  docs/BUILD_STATUS.md, VALIDATION.md, OPTIONS_INTELLIGENCE_PLAN.md status line only
```

Do not paste Hybrid V2 S4/S5 p̂. Do not rebuild `oi-options-live.js` as resolver #2.

---

## 1. Claim contract

Each claim: registered FTR (use existing options FTR IDs from File A feature_registry; do not invent Combined_Score). Fields: family `OPTIONS_CONTEXT`, group `CG_OPTION_CHAIN`, `can_support_confirmed=false`, expiry, snapshot hash, `available_at`.

| Observation | Claim meaning |
|---|---|
| Call/put OI wall at strike | CONTEXT support/weaken near that strike — not a buy |
| PCR path | CONTEXT only |
| IV/Greeks | inspector + UNKNOWN if model inputs missing |
| Max pain | PROTOTYPE_ONLY / reference (Math Book §14.7) — not direction |
| GEX signed | **Needed:** dealer-GEX **guidance** (scenario, not observed) |

Empty official `{}` chain: do **not** mint walls. Keep `UNKNOWN_NEEDS_R12` or `WAIT_CHAIN`.

Shortlist only (S5 bound). Not 2,633-wide expensive loop.

---

## 2. Tests

1. No chain → no wall claims; package UNKNOWN; S7 state does not rise.  
2. Usable FO snapshot → OPTIONS_CONTEXT claims + optional `guidanceConfirmed`.  
3. Strip options → File A S7 publicState does not upgrade (guidance chip may disappear).  
4. GEX stored as scenario guidance, never `OBSERVED_DEALER`.  
5. OI room + S5/S6/S7 tests still pass.  
6. No live `placeorder`.

---

## 3. Frontend (minimal)

Do **not** new nav. S5 chips / S6 Decision tab already show options package — update copy when claims exist: “Options context — not CONFIRMED.” Optional: inspector Derivatives tab lists wall strikes as text.

---

## 4. GATES

`D:\TrendForge\delete\gates_r12_claims_2026-08-25\GATES.md`

```text
G1 module
CHECK: D:\TrendForge\.venv\Scripts\python.exe -c "from trendforge_api.selection.r12_options_claims import SCHEMA_VERSION; print(SCHEMA_VERSION)"
EXPECT: trendforge.r12-options-claims
CWD: D:\TrendForge\backend

G2 pytest
CHECK: D:\TrendForge\.venv\Scripts\python.exe -m pytest tests/test_r12_options_claims.py tests/test_s5_shortlist_enrichment.py tests/test_s6_family_resolution.py tests/test_s7_state_gates.py -q --tb=short
EXPECT: passed
CWD: D:\TrendForge\backend
```

If SCHEMA_VERSION name differs, print it in G1 EXPECT honestly. Stop. Ticket **4** unlocks File A **public** CONFIRMED; this ticket already ships options **guidanceConfirmed**.
