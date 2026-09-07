(() => {
  "use strict";

  const ENDPOINT = "/api/v1/selection/mcx-master";

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

  function rowMarkup(row) {
    const why = (row.why || []).slice(0, 4).map(escapeHtml).join(" · ");
    const fields = [
      row.lotSize != null ? `lot ${Number(row.lotSize)}` : "lot ?",
      row.tickSize != null ? `tick ${Number(row.tickSize)}` : "tick ?",
      row.expiry ? `exp ${escapeHtml(row.expiry)}` : "exp ?",
      row.dte != null ? `dte ${Number(row.dte)}` : null,
    ]
      .filter(Boolean)
      .map(escapeHtml)
      .map((s) => `<span class="mm-field">${s}</span>`)
      .join("");
    return `
      <div class="mm-row" data-symbol="${escapeHtml(row.symbol || "")}">
        <strong>${escapeHtml(row.symbol || "")}</strong>
        <span class="mm-readiness" data-ready="${escapeHtml(row.readiness || "")}">${escapeHtml(row.readiness || "")}</span>
        ${fields}
        <div class="mm-why">${why}</div>
      </div>`;
  }

  function render(batch) {
    const ops = $("mcxMasterOps");
    if (!ops || !batch) return;
    const meta = $("mcxMasterMeta");
    if (meta) {
      meta.textContent =
        `ready ${Number(batch.readyCount || 0)} · confirmed ${Number(batch.confirmedCount || 0)} · ` +
        Object.entries(batch.readinessCounts || {})
          .map(([k, v]) => `${k.replace("WAIT_MCX_", "W:")}=${v}`)
          .join(" ");
    }
    const rows = batch.rows || [];
    ops.innerHTML = `
      <div class="mm-meta">schema: ${escapeHtml(batch.schemaVersion || "")} ·
        ceiling: ${escapeHtml(batch.acceptanceCeiling || "")}</div>
      <div class="mm-rows">
        ${
          rows.length
            ? rows.slice(0, 30).map(rowMarkup).join("")
            : '<div class="nc-none">No official MCX master last-good — every contract seats WAIT.</div>'
        }
      </div>
      <div class="mm-copy">MCX contract safety &mdash; WAIT without master. Not COMEX. Not an order.</div>`;
  }

  async function load() {
    const ops = $("mcxMasterOps");
    if (!ops) return;
    try {
      const response = await fetch(ENDPOINT, { cache: "no-store" });
      if (!response.ok) {
        ops.textContent = `MCX master WAIT — HTTP ${response.status}`;
        return;
      }
      render(await response.json());
    } catch (error) {
      ops.textContent = `MCX master failed: ${error.message}`;
    }
  }

  window.TrendForgeMcxMaster = {
    apply: render,
    load,
    CONTRACT: "trendforge.mcx-master.v1",
  };

  function bind() {
    if (window.TrendForgeResearchSnapshot) return;
    if (!$("mcxMasterPanel")) return;
    void load();
    window.addEventListener("trendforge:selection-ready", () => {
      void load();
    });
    // MCX segment must show live master status, never fixture gold.
    document.querySelectorAll('.segment[data-mode="mcx"]').forEach((button) => {
      button.addEventListener("click", () => void load());
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
