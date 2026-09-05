(() => {
  "use strict";

  const CONTRACT = "trendforge.r18-model-governance.v1";
  const PATH = "/api/research/ml/governance";

  function esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function render(payload) {
    const panel = document.getElementById("r18ModelGovernancePanel");
    if (!panel) return;
    const blockers = Array.isArray(payload?.blockers) ? payload.blockers : ["MODEL_STATUS_UNAVAILABLE"];
    const schemaReady = payload?.schema?.applied === true;
    const drift = Array.isArray(payload?.driftEvents) ? payload.driftEvents : [];
    const rollbacks = Array.isArray(payload?.rollbackHistory) ? payload.rollbackHistory : [];
    panel.innerHTML = `<div class="panel-head"><h3>Model governance</h3><span class="tag wait">${esc(payload?.modelState || "MODEL_NOT_APPROVED")}</span></div>
      <div class="body">
        <div class="r16-summary">
          <span><small>R16 dataset</small><strong>${esc(payload?.datasetStatus || "BUILDING")}</strong></span>
          <span><small>PIT validation</small><strong>${esc(payload?.r16ValidationStatus || "PIT_NOT_APPROVED")}</strong></span>
          <span><small>Governance schema</small><strong>${schemaReady ? "READY" : "NOT APPLIED"}</strong></span>
          <span><small>Dataset age</small><strong>${esc(payload?.datasetAgeDays ?? "UNAVAILABLE")}</strong></span>
        </div>
        <div class="r18-counts">
          <span>Models <strong>${esc(payload?.models?.length || 0)}</strong></span>
          <span>Evaluations <strong>${esc(payload?.evaluations?.length || 0)}</strong></span>
          <span>Human reviews <strong>${esc(payload?.reviews?.length || 0)}</strong></span>
          <span>Drift events <strong>${esc(drift.length)}</strong></span>
          <span>Rollbacks <strong>${esc(rollbacks.length)}</strong></span>
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
    try {
      const response = await fetch(PATH, { cache: "no-store", headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      render(payload);
      return payload;
    } catch (error) {
      render({ modelState: "MODEL_NOT_APPROVED", blockers: [`WAIT_R18_API: ${error.message}`] });
      return null;
    }
  }

  window.TrendForgeR18ModelGovernance = { CONTRACT, PATH, load, render };
  const refresh = document.getElementById("previewRefresh");
  if (refresh) refresh.addEventListener("click", () => { void load(); });
  void load();
})();
