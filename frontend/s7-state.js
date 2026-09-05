(() => {
  "use strict";

  const CONTRACT = "trendforge.s7-state.v1";

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function chip(state) {
    return `<span class="s7-chip" data-state="${escapeHtml(state)}">${escapeHtml(state)}</span>`;
  }

  function tradabilityMarkup(row) {
    const outcome = row.tradabilityOutcome || "WAIT";
    const reason = row.tradabilityReason || "WAIT_TRADABILITY_NOT_EVALUATED";
    const components = row.tradability?.components || [];
    const componentRows = components
      .map(
        (item) => `<tr>
          <td>${escapeHtml(item.component)}</td>
          <td><span class="tradability-chip" data-outcome="${escapeHtml(item.outcome)}">${escapeHtml(item.outcome)}</span></td>
          <td>${escapeHtml(item.reasonCode)}</td>
          <td>${escapeHtml(item.dataDate || "unknown")}</td>
          <td>${escapeHtml(item.sourceKey || "not applicable")}</td>
        </tr>`,
      )
      .join("");
    return `<div class="tradability-summary">
      <span class="tradability-chip" data-outcome="${escapeHtml(outcome)}">Tradability ${escapeHtml(outcome)}</span>
      <strong>${escapeHtml(reason)}</strong>
    </div>
    <details class="tradability-inspector">
      <summary>Restriction evidence</summary>
      <div class="tradability-hash">lineage: ${escapeHtml(row.tradabilityHash || "missing")}</div>
      <div class="tradability-table-wrap"><table class="tradability-table">
        <thead><tr><th>Check</th><th>Result</th><th>Reason</th><th>Data date</th><th>Source</th></tr></thead>
        <tbody>${componentRows || '<tr><td colspan="5">No typed tradability components.</td></tr>'}</tbody>
      </table></div>
    </details>`;
  }

  function cardMarkup(row) {
    const why = (row.why || []).slice(0, 4).map(escapeHtml).join(" · ");
    const missing = (row.missingFamilies || row.missingFamiles || []).length
      ? `missing: ${(row.missingFamilies || []).map(escapeHtml).join(", ")}`
      : "";
    const trigger = row.nextTrigger
      ? `<div class="s7-trigger">next: ${escapeHtml(row.nextTrigger)}</div>`
      : "";
    const invalidation = row.invalidationCondition
      ? `<div class="s7-invalidation">invalid: ${escapeHtml(row.invalidationCondition)}</div>`
      : "";
    const confirmedNote =
      row.publicState === "CONFIRMED"
        ? `<div class="s7-confirmed-note">research CONFIRMED — guidance OMS below</div>`
        : "";
    const qty =
      Number(row.researchQuantity || 0) > 0
        ? `<span class="s7-qty">researchQty ${Number(row.researchQuantity)}</span>`
        : "";
    return `
      <div class="s7-card" data-symbol="${escapeHtml(row.symbol || "")}">
        <div class="s7-head">
          <strong>${escapeHtml(row.symbol || "")}</strong>
          ${chip(row.publicState)}
          <span class="s7-dir">${escapeHtml(row.evidenceDirection || "")}</span>
          <span class="s7-strength">${Number(row.evidenceStrength || 0).toFixed(2)} strength</span>
          ${qty}
        </div>
        <div class="s7-why">${why}</div>
        <div class="s7-missing">${missing}</div>
        ${tradabilityMarkup(row)}
        ${trigger}
        ${invalidation}
        ${confirmedNote}
        <div class="s7-note">Research state &mdash; not an order.</div>
      </div>`;
  }

  function apply(batch) {
    if (!batch) return;
    const panel = document.getElementById("s7StatePanel");
    if (panel) {
      const rows = batch.rows || [];
      panel.innerHTML = `
        <div class="s7-meta">
          schema: ${escapeHtml(batch.schemaVersion || CONTRACT)} ·
          ceiling: ${escapeHtml(batch.acceptanceCeiling || "")} ·
          confirmedCount: ${Number(batch.confirmedCount || 0)} ·
          draftEligible: ${Number(batch.draftConfirmedEligibleCount || 0)} ·
          intradayGuidance: ${batch.intradayGuidanceConfirmed ? "ON (guidance only)" : "OFF"}
        </div>
        <div class="s7-cards">
          ${rows.map(cardMarkup).join("") || '<div class="s7-empty">No S7 rows for current lineage.</div>'}
        </div>`;
    }
    const ops = document.getElementById("s7StateOps");
    if (ops) {
      const rows = batch.rows || [];
      ops.innerHTML = rows
        .slice(0, 12)
        .map((row) => `<div class="s7-opline">${escapeHtml(row.symbol)} → ${chip(row.publicState)}</div>`)
        .join("");
    }
    const modeChip = document.getElementById("confirmedModeChip");
    if (modeChip) {
      if (batch.sourceActivationReady) {
        modeChip.textContent = "CONFIRMED EOD PRF-003 ONLY";
        modeChip.classList.remove("bad");
        modeChip.classList.add("wait");
        modeChip.title =
          "Named five official sources observed current; PRF-003 EOD only. NO BROKER ORDERS.";
      } else {
        modeChip.textContent = "CONFIRMED LOCKED";
        modeChip.title = "sourceActivationReady=false";
      }
    }
  }

  window.TrendForgeS7State = { apply, CONTRACT };
})();
