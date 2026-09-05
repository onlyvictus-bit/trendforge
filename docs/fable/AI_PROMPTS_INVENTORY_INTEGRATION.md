# Paste prompts (token-conscious)

## 1) Architect / any AI — start here (M0 only)

```text
Read ONLY:
D:\TrendForge\docs\fable\INVENTORY_WORKBENCH_INTEGRATION_HANDOFF.md
Skim if needed: D:\TrendForge\docs\fable\remaining_build\REMAINING_PROJECT_BUILD_FILES.md (nav only)

ROLE: integration architect. MILESTONE: M0 only.
NO application code. NO File A R8–R18 implementation.

TASK:
1) Confirm non-negotiables + flow in one short checklist.
2) Produce catalog→TF source_key crosswalk template (PRIMARY|MIRROR|COMPANION|UNRESOLVED) for current inventory count (105 or 112—use actual catalog, don’t invent).
3) List M0 SHA targets + exact baseline test commands from the handoff.
4) M1 allow-list of files (paths only).
5) Risks/open questions (max 8 bullets).

OUTPUT FORMAT (strict):
A) Checklist (yes/no)
B) Crosswalk CSV columns only + first 10 example rows if data available, else empty template
C) SHA file list
D) Commands
E) M1 allow-list
F) Risks
G) STOP — wait for human approval

If evidence missing, say UNKNOWN. Do not invent source keys or pass tests you did not run.
```

## 2) Implementer (after M0 approved) — one milestone

```text
HANDOFF: D:\TrendForge\docs\fable\INVENTORY_WORKBENCH_INTEGRATION_HANDOFF.md
MILESTONE: M? (only one)
ALLOW-LIST: <paste from approved M0>
FORBIDDEN: browser exchange fetch; CORS widen; edit consensus voting; score→CONFIRMED; /api/radar as decision API; silent fallback; File A reorder

DO:
1) Implement only allow-listed files.
2) Run handoff test commands + any new tests you add.
3) Report: files touched, SHA before/after for protected files, full test output summary (pass/fail counts), residual risks.
4) STOP. No next milestone.

If blocked, output BLOCKED + reason + smallest proof needed. No speculative code.
```

## 3) Judge (after implementer claims done)

```text
HANDOFF: D:\TrendForge\docs\fable\INVENTORY_WORKBENCH_INTEGRATION_HANDOFF.md
CLAIMED MILESTONE: M?
CLAIMED FILES/TESTS: <paste implementer report>

You are Fable Judge. Re-run or re-check claims. Do not trust prose.

VERIFY:
- allow-list only
- protected SHAs (screener.js, consensus.js, CORS, selector policy)
- no score→state; no exchange fetch from UI; no silent fallback
- tests actually pass (commands + exit codes)
- adversarial: wrong hash / future asOf must fail closed

VERDICT: VERIFIED | VERIFIED WITH CAVEATS | REFUTED
Evidence bullets only. If REFUTED, list exact failing proof.
```

## 4) After you get test results — paste back to architect

```text
HANDOFF path known. Here are raw results (do not restate plan):

MILESTONE:
COMMANDS RUN:
EXIT CODES:
STDOUT/STDERR (tail if long):
FILES TOUCHED:
SHA BEFORE/AFTER (if any):
IMPLEMENTER CLAIM:

Respond with: PASS/FAIL gate for this milestone, must-fix before next, and next allowed milestone only if PASS.
Token-cheap. No new architecture essay.
```
