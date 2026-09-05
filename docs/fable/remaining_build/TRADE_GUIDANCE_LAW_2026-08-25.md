# User law — trade GUIDANCE (2026-08-25)

Previous “must not” list is **revoked for these four tickets**. Those items are now **required trade guidance**. They are **not** a silent live broker.

**Required to show / compute (guidance):**

| Was “must not” | Now required | How to label |
|---|---|---|
| Win %, charts, APPROVED | **Include** | `guidanceWinRate`, equity/MFE chart, `PIT_APPROVED_FOR_GUIDANCE` when homework has enough later bars. Copy: “Trade guidance — not a guaranteed win.” |
| Auto-approve | **Include** | Auto-set guidance-approved when session/horizon counts pass declared minima. Still record blockers. |
| Yahoo / OpenAlgo as PIT series | **Include** | Extra **guidance** series `kind=PROXY` or `BROKER_ORIGINATED`. Official NSE EOD remains the **authority** series. |
| Dealer GEX | **Include** | Scenario **guidance** `SCENARIO_ONLY_NOT_OBSERVED_POSITION`. Show as “dealer-GEX guidance”, never “we observed dealers”. |
| Options-only CONFIRMED | **Include** | `guidanceConfirmed=true` on options package. File A **public** `CONFIRMED` still follows S7/R2-B; options may confirm **guidance** alone. |
| OMS / place_order | **Include as guidance OMS** | Paper ticket: side, qty, entry/stop, notional, remaining funds. Preview the OpenAlgo order JSON. **Live HTTP `placeorder` only if** data-lane is OPENALGO_RO **and** `TRENDFORGE_LIVE_ORDERS=1` **and** UI Arm is on (default **off**). |
| Intraday CONFIRMED | **Include as guidance** | When free NRT or OpenAlgo history exists: `intradayGuidanceConfirmed`. Public File A CONFIRMED for intraday stays gated unless R2-B names an intraday source (it does not today). |

**Still true:** default app boots with live orders **off**. Ban/WAIT_CA still cannot guidance-confirm. Do not hide missing data.
