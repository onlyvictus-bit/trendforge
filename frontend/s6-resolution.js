(() => {
  "use strict";

  const CONTRACT = "trendforge.s6-resolution.v1";
  let currentBatch = null;
  let selectedSymbol = null;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function pct(value) {
    return value === null || value === undefined ? "-" : `${Math.round(Number(value) * 100)}%`;
  }

  function familyRows(row) {
    const families = row.families || {};
    const names = Object.keys(families).filter(
      (name) => families[name].support > 0 || families[name].oppose > 0
    );
    const missing = row.missingFamilies || [];
    const lines = [];
    names.sort().forEach((name) => {
      const f = families[name];
      lines.push(
        `<div class="s6-family"><span>${escapeHtml(name)}</span><strong class="good">S ${pct(f.support)}</strong><strong class="bad">O ${pct(f.oppose)}</strong></div>`
      );
    });
    missing.forEach((name) => {
      lines.push(`<div class="s6-family missing"><span>${escapeHtml(name)}</span><strong>MISSING</strong></div>`);
    });
    return lines.join("") || '<div class="s6-family missing"><span>No family evidence</span><strong>MISSING</strong></div>';
  }

  function symbolPicker() {
    if (!currentBatch || !Array.isArray(currentBatch.rows)) return "";
    const options = currentBatch.rows
      .map((row) => `<option value="${escapeHtml(row.symbol)}" ${row.symbol === selectedSymbol ? "selected" : ""}>${escapeHtml(row.symbol)}</option>`)
      .join("");
    return `<label class="s6-picker">Inspect <select id="s6SymbolSelect">${options}</select></label>`;
  }

  function decisionMarkup(row) {
    if (!row) {
      return '<div class="s6-empty">WAIT_S6_ROW_MISSING</div>';
    }
    return `<div class="s6-decision">
      <div class="s6-decision-head">
        <strong>${escapeHtml(row.symbol)}</strong>
        <span class="chip ${row.resolutionState === "REJECT" ? "bad" : "wait"}">${escapeHtml(row.resolutionState)}</span>
        ${row.conflict ? '<span class="chip bad">CONFLICT</span>' : ""}
        <small>evidence strength ${pct(row.evidenceStrength)} - not win probability</small>
      </div>
      <div class="s6-families">${familyRows(row)}</div>
      <div class="s6-why">${escapeHtml((row.whyUnknown || []).join(" · ") || "no enrichment notes")}</div>
      <div class="s6-disclaimer">Family agreement is research strength, never a buy stamp. canUnlockConfirmed=false.</div>
    </div>`;
  }

  function refreshInspectorMount() {
    const mount = document.getElementById("s6InspectorMount");
    if (!mount) return;
    if (!currentBatch) {
      mount.innerHTML = '<div class="s6-empty">WAIT_S6_NOT_READY</div>';
      return;
    }
    const rows = Array.isArray(currentBatch.rows) ? currentBatch.rows : [];
    if (!selectedSymbol && rows.length) selectedSymbol = rows[0].symbol;
    const row = rows.find((item) => item.symbol === selectedSymbol) || rows[0] || null;
    mount.innerHTML = `${symbolPicker()}${decisionMarkup(row)}`;
    const select = document.getElementById("s6SymbolSelect");
    if (select) {
      select.addEventListener("change", () => {
        selectedSymbol = select.value;
        refreshInspectorMount();
      });
    }
  }

  function panelMarkup(batch) {
    if (!batch) {
      return '<div class="s6-empty"><strong>WAIT_S6_NOT_READY</strong><span>Family resolution needs a hash-matched R5 lineage.</span></div>';
    }
    if (batch.schemaVersion !== CONTRACT) {
      return `<div class="s6-empty"><strong>WAIT_S6_SCHEMA_MISMATCH</strong><span>${escapeHtml(batch.schemaVersion)}</span></div>`;
    }
    const rows = Array.isArray(batch.rows) ? batch.rows : [];
    const conflicts = rows.filter((row) => row.conflict).length;
    return `<div class="s6-summary">
      <div><span>Active profile</span><strong>${escapeHtml(batch.activeProfileId)} v${escapeHtml(batch.activeProfileVersion)}</strong></div>
      <div><span>Rows</span><strong>${rows.length}</strong></div>
      <div><span>Conflicts</span><strong>${conflicts}</strong></div>
      <div><span>Ceiling</span><strong>LIVE_S6_RESOLVE_WAIT_ONLY</strong></div>
      <span class="chip wait">required families come from the active profile object</span>
    </div>
    <div class="s6-rows">${rows.map(decisionMarkup).join("")}</div>`;
  }

  function apply(batch) {
    if (batch && batch.schemaVersion === CONTRACT) {
      currentBatch = batch;
    } else if (batch === null) {
      currentBatch = null;
    }
    const markup = panelMarkup(currentBatch);
    const mount = document.getElementById("s6ResolutionOps");
    if (mount) mount.innerHTML = markup;
    refreshInspectorMount();
    document.body.dataset.s6Mode = currentBatch ? "LIVE_RESOLVE_WAIT" : "WAIT";
    return currentBatch && Array.isArray(currentBatch.rows) ? currentBatch.rows.length : 0;
  }

  function renderRecords(listEl) {
    // Research records only: no confirmation state, no quantity, no order.
    if (!listEl) return;
    if (!currentBatch || !Array.isArray(currentBatch.rows)) return;
    const records = currentBatch.rows.slice(0, 8).map((row) => {
      const missing = (row.missingFamilies || []).slice(0, 2).join(", ") || "none";
      return `<div class="live-decision-row s6-live-record"><span>${escapeHtml(row.symbol)}</span><strong class="state-chip warn">${escapeHtml(row.resolutionState)}</strong><small>S6 strength ${pct(row.evidenceStrength)} | conflict ${row.conflict ? "yes" : "no"} | missing ${escapeHtml(missing)} | not win probability</small></div>`;
    });
    if (!records.length) return;
    listEl.insertAdjacentHTML("afterbegin", `<div class="s6-live-header">S6 family resolution records (research)</div>${records.join("")}`);
  }

  window.TrendForgeS6Resolution = { contract: CONTRACT, apply, renderRecords };
})();
