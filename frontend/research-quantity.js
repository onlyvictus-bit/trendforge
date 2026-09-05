(() => {
  "use strict";

  const CONTRACT = "trendforge.research-qty.v1";

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function bySymbol(batch) {
    const map = new Map();
    for (const row of batch.rows || []) {
      map.set(String(row.symbol || "").toUpperCase(), row);
    }
    return map;
  }

  function apply(qtyBatch, s7Batch) {
    if (!qtyBatch) return;
    const rows = qtyBatch.rows || [];
    const funds = qtyBatch.researchFunds || qtyBatch.research_funds || {};
    const qtyPanel = document.getElementById("researchQtyPanel");
    const fundsPanel = document.getElementById("researchFundsPanel");
    const posCard = document.getElementById("researchPositionCard");
    const eligible = rows.filter((row) => row.draftConfirmedEligible || row.draft_confirmed_eligible);
    const sized = rows.filter((row) => Number(row.researchQuantity || row.research_quantity || 0) > 0);
    if (qtyPanel) {
      qtyPanel.innerHTML = `
        <div class="rq-meta">
          schema: ${escapeHtml(qtyBatch.schemaVersion || CONTRACT)} ·
          ceiling: ${escapeHtml(qtyBatch.acceptanceCeiling || qtyBatch.acceptance_ceiling || "")} ·
          confirmedCount: ${Number(qtyBatch.confirmedCount || qtyBatch.confirmed_count || 0)} ·
          executable: ${String(qtyBatch.executable === true)}
        </div>
        <div class="rq-note">Research size — not an order.</div>
        <div class="rq-rows">
          ${
            (eligible.length ? eligible : rows.slice(0, 8))
              .map((row) => {
                const qty = Number(row.researchQuantity || row.research_quantity || 0);
                const side = row.side || "FLAT";
                const eligibleFlag = row.draftConfirmedEligible || row.draft_confirmed_eligible;
                const copy = eligibleFlag
                  ? `${escapeHtml(side)} ${qty} ${escapeHtml(row.qtyUnit || row.qty_unit || "shares")}`
                  : "qty 0 — not at confirmation";
                return `<div class="rq-line" data-symbol="${escapeHtml(row.symbol)}">
                  <strong>${escapeHtml(row.symbol)}</strong> ${copy}
                  <span class="rq-reason">${escapeHtml(row.reason || "")}</span>
                </div>`;
              })
              .join("") || '<div class="rq-empty">No research-qty rows.</div>'
          }
        </div>`;
    }
    if (fundsPanel) {
      fundsPanel.innerHTML = `
        <strong>Research funds</strong>
        <p>capital ₹${escapeHtml(funds.capitalInr ?? funds.capital_inr ?? 100000)} ·
           reserved ₹${escapeHtml(funds.reservedRiskInr ?? funds.reserved_risk_inr ?? 0)} ·
           remaining ₹${escapeHtml(funds.remainingCapitalInr ?? funds.remaining_capital_inr ?? 100000)}</p>
        <div class="rq-note">Research funds / position — calculated, not a broker account.</div>`;
    }
    if (posCard) {
      const first = sized[0];
      posCard.innerHTML = first
        ? `<strong>Research position</strong>
           <p>${escapeHtml(first.symbol)} ${escapeHtml(first.side)} qty ${escapeHtml(first.researchQuantity || first.research_quantity)}
           @ ${escapeHtml(first.researchEntry || first.research_entry || "—")} stop ${escapeHtml(first.researchStop || first.research_stop || "—")}</p>
           <div class="rq-note">Hypothetical. executable=false. Not an order.</div>`
        : `<strong>Research position</strong><p>none — not at confirmation</p>`;
    }
    const qtyMap = bySymbol(qtyBatch);
    document.querySelectorAll(".s7-card[data-symbol]").forEach((card) => {
      const row = qtyMap.get((card.dataset.symbol || "").toUpperCase());
      if (!row) return;
      let line = card.querySelector(".rq-join");
      if (!line) {
        line = document.createElement("div");
        line.className = "rq-join";
        card.appendChild(line);
      }
      const eligibleFlag = row.draftConfirmedEligible || row.draft_confirmed_eligible;
      const qty = Number(row.researchQuantity || row.research_quantity || 0);
      line.textContent = eligibleFlag
        ? `${row.side || "FLAT"} ${qty} — not an order`
        : "qty 0 — not at confirmation";
    });
  }

  window.TrendForgeResearchQty = { apply, CONTRACT };
})();
