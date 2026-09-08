(() => {
  "use strict";

  const CONTRACT = "trendforge.r18-model-governance.v1";
  const PATH = "/api/research/ml/governance";
  let generation = 0;

  function esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  // An unavailable response is UNKNOWN, not an observed MODEL_NOT_APPROVED result.
  function render(payload) {
    if (window.TrendForgeStatusProvenance) window.TrendForgeStatusProvenance.governance(payload);
    const panel = document.getElementById("r18ModelGovernancePanel");
    if (!panel) return;
    const blockers = Array.isArray(payload?.blockers) ? payload.blockers : ["MODEL_STATUS_UNAVAILABLE"];
    const schemaState = typeof payload?.schema?.applied === "boolean" ? (payload.schema.applied ? "READY" : "NOT APPLIED") : "UNKNOWN";
    const drift = Array.isArray(payload?.driftEvents) ? payload.driftEvents.length : "UNKNOWN";
    const rollbacks = Array.isArray(payload?.rollbackHistory) ? payload.rollbackHistory.length : "UNKNOWN";
    panel.innerHTML = `<div class="panel-head"><h3>Model governance</h3><span class="tag wait">${esc(payload?.modelState || "UNKNOWN")}</span></div>
      <div class="body">
        <div class="r16-summary">
          <span><small>R16 dataset</small><strong>${esc(payload?.datasetStatus || "UNKNOWN")}</strong></span>
          <span><small>PIT validation</small><strong>${esc(payload?.r16ValidationStatus || "UNKNOWN")}</strong></span>
          <span><small>Governance schema</small><strong>${schemaState}</strong></span>
          <span><small>Dataset age</small><strong>${esc(payload?.datasetAgeDays ?? "UNAVAILABLE")}</strong></span>
        </div>
        <div class="r18-counts">
          <span>Models <strong>${esc(Array.isArray(payload?.models) ? payload.models.length : "UNKNOWN")}</strong></span>
          <span>Evaluations <strong>${esc(Array.isArray(payload?.evaluations) ? payload.evaluations.length : "UNKNOWN")}</strong></span>
          <span>Human reviews <strong>${esc(Array.isArray(payload?.reviews) ? payload.reviews.length : "UNKNOWN")}</strong></span>
          <span>Drift events <strong>${esc(drift)}</strong></span>
          <span>Rollbacks <strong>${esc(rollbacks)}</strong></span>
        </div>
        <div class="callout bad"><strong>RESEARCH SIMULATION ONLY - NO BROKER ORDER</strong><br>${esc(blockers.join(" | "))}</div>
        <details><summary>Governance inspector</summary>
          <p>Automatic promotion: DISABLED. Human promotion remains blocked until R16 is PIT_APPROVED.</p>
          <p>Probability: HIDDEN | Win rate: HIDDEN | Performance: HIDDEN</p>
          <p>Drift: feature, prediction and calibration. A breach may demote and restore the previous signed champion.</p>
        </details>
      </div>`;
  }

  async function load() {
    const mine = ++generation;
    render(null);
    const control = typeof AbortController === "function" ? new AbortController() : null;
    const timer = control ? setTimeout(() => control.abort(), 15000) : null;
    try {
      const response = await fetch(PATH, { cache: "no-store", headers: { Accept: "application/json" },
        ...(control ? { signal: control.signal } : {}) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      if (mine !== generation) return null;
      render(payload);
      return payload;
    } catch (error) {
      if (mine !== generation) return null;
      render(null);
      const panel = document.getElementById("r18ModelGovernancePanel");
      if (panel) panel.insertAdjacentHTML("afterbegin", `<p role="status">Model status unavailable: ${esc(error.message)}. No approval inferred.</p>`);
      return null;
    } finally {
      if (timer !== null) clearTimeout(timer);
    }
  }

  window.TrendForgeR18ModelGovernance = { CONTRACT, PATH, load, render };
  const refresh = document.getElementById("previewRefresh");
  if (refresh) refresh.addEventListener("click", () => { void load(); });
  void load();
})();
