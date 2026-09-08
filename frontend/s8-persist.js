(() => {
  "use strict";

  const CONTRACT = "trendforge.s8-scan.v1";

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function apply(batch) {
    if (!batch) {
      const stale = document.getElementById("s8HistoryPanel");
      if (stale) stale.innerHTML = '<p role="status">LATEST SAVED SCAN UNAVAILABLE - previous metadata cleared. Use History for saved runs.</p>';
      return;
    }
    const panel = document.getElementById("s8HistoryPanel");
    if (!panel) return;
    const lineage = batch.lineage || {};
    const missing = lineage.missingStages || [];

    panel.innerHTML = `
      <strong>Latest saved research snapshot - not a live quote</strong>
      <div class="s8-meta">
        runId: ${escapeHtml(batch.runId || "")} ·
        asOf: ${escapeHtml(batch.asOf || "")} ·
        confirmedCount: ${Number(batch.confirmedCount || 0)} ·
        ceiling: ${escapeHtml(batch.acceptanceCeiling || "")}
      </div>
      <div class="s8-lineage">
        lineage: ${escapeHtml(
          Object.entries({
            R1: lineage.r1RunHash,
            R2: lineage.r2RunHash,
            R14: lineage.r14RunHash,
            R5: lineage.r5RunHash,
            S2: lineage.s2RunId,
            S3: lineage.s3RunId,
            S4: lineage.s4PackId,
            S5: lineage.s5RunId,
            S6: lineage.s6RunId,
            S7: lineage.s7RunId
          })
            .map(([k, v]) => `${k}=${v ? String(v).slice(0, 10) : "ABSENT"}`)
            .join(" · ")
        )}
        ${missing.length ? ` · WAIT_STAGE_ABSENT: ${escapeHtml(missing.join(","))}` : ""}
      </div>
      <div class="s8-note">Reconstructable research run &mdash; not an order. Not a win rate.</div>`;
  }

  window.TrendForgeS8Persist = { apply, CONTRACT };
})();
