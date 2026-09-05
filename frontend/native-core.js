(() => {
  "use strict";

  const ENDPOINT = "/api/v1/scanners/native-core";

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function shortName(scannerId) {
    return String(scannerId || "")
      .replace(/^native\./, "")
      .replace(/\.v1$/, "");
  }

  function rowMarkup(row) {
    const representativeIds = new Set(row.representativeGuidanceIds || []);
    const matched = (row.matches || []).filter(
      (m) => m.matched && representativeIds.has(m.scannerId)
    );
    const chips = matched
      .map((m) => {
        const twin = m.correlatedPossible
          ? ' <span class="nc-twin" title="Same R5 claim - correlated possible, never independent">twin</span>'
          : "";
        const relationship = String(m.candidateRelationship || "UNKNOWN").toLowerCase();
        return `<span class="nc-chip nc-${escapeHtml(relationship)}" data-scanner="${escapeHtml(m.scannerId)}" title="${escapeHtml(m.guidanceLabel || "")}">${escapeHtml(shortName(m.scannerId))}: ${escapeHtml(relationship)}</span>${twin}`;
      })
      .join(" ");
    const blocker = !chips && (row.why || []).length
      ? `<div class="nc-reps">blocker: ${escapeHtml(row.why[0])}</div>`
      : "";
    return `
      <div class="nc-row" data-symbol="${escapeHtml(row.symbol || "")}">
        <strong>${escapeHtml(row.symbol || "")}</strong>
        ${chips || '<span class="nc-none">no representative guidance</span>'}
        ${blocker}
      </div>`;
  }

  function render(run) {
    const ops = $("nativeCoreOps");
    if (!ops || !run) return;
    const rows = run.rows || [];
    const matchedRows = rows.filter((r) => (r.representativeGuidanceIds || []).length);
    ops.innerHTML = `
      <div class="nc-meta">
        schema: ${escapeHtml(run.schemaVersion || "")} ·
        ceiling: ${escapeHtml(run.acceptanceCeiling || "")} ·
        universe: ${escapeHtml(run.universe || "")} ·
        symbols: ${Number(rows.length)} ·
        matched: ${Number(matchedRows.length)} ·
        confirmedCount: ${Number(run.confirmedCount || 0)}
      </div>
      <div class="nc-rows">
        ${
          matchedRows.length
            ? matchedRows.slice(0, 40).map(rowMarkup).join("")
            : '<div class="nc-empty">No native core matches on the current hash-matched R5 spine.</div>'
        }
      </div>
      <div class="nc-copy">Native core &mdash; trade guidance, not an order.</div>`;
  }

  async function load() {
    const ops = $("nativeCoreOps");
    if (!ops) return;
    try {
      const response = await fetch(ENDPOINT, { cache: "no-store" });
      if (!response.ok) {
        ops.textContent = `Native core WAIT — HTTP ${response.status}. Runs compute from the last hash-matched R5 spine.`;
        return;
      }
      render(await response.json());
    } catch (error) {
      ops.textContent = `Native core failed: ${error.message}`;
    }
  }

  function bind() {
    if (!$("nativeCorePanel")) return;
    void load();
    window.addEventListener("trendforge:selection-ready", () => {
      void load();
    });
  }

  window.TrendForgeNativeCore = { apply: render, CONTRACT: "trendforge.scanner-native-core.v1" };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
