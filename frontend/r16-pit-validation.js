(() => {
  "use strict";

  const CONTRACT = "trendforge.r16-pit-view.v1";
  const OBSERVATIONS_PATH = "/api/v1/selection/pit/observations?limit=50";
  let summaryPayload = { status: null, metrics: null };
  let observationsPayload = null;
  let observationsState = "NOT_LOADED";
  let observationsRequest = null;

  function esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function fmt(value, digits = 2) {
    return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "UNAVAILABLE";
  }

  function pct(value) {
    return Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(1)}%` : "UNAVAILABLE";
  }

  function stateClass(value) {
    return value === "PIT_APPROVED" || value === "READY" ? "good" : "wait";
  }

  function metricCard(metric) {
    return `<article class="r16-cell">
      <div class="r16-cell-head">
        <strong>${esc(metric.direction || "UNKNOWN")} � ${esc(metric.horizonSessions || "?")} sessions</strong>
        <span class="tag ${metric.foldCount >= 3 ? "good" : "wait"}">${esc(metric.foldCount || 0)} folds</span>
      </div>
      <div class="r16-grid">
        <span>Eligible observations<strong>${esc(metric.eligibleObservationCount ?? 0)}</strong></span>
        <span>Resolved target/stop<strong>${esc(metric.resolvedCount ?? 0)}</strong></span>
        <span>Censored<strong>${pct(metric.censorRate)}</strong></span>
        <span>Missing S8 dates<strong>${pct(metric.missingS8Rate)}</strong></span>
        <span>Average net R<strong>${fmt(metric.averageNetR)}</strong></span>
        <span>Bootstrap width<strong>${fmt(metric.bootstrapWidth, 3)}</strong></span>
      </div>
      <p class="r16-cell-note">Cost model: ${esc(metric.costModelVersion || "UNAVAILABLE")} � calendar: ${metric.calendarVerified ? "VERIFIED" : "WAIT"} � conclusion: ${esc(metric.profileConclusion || "INCONCLUSIVE")}</p>
    </article>`;
  }

  function observationRow(row) {
    return `<tr>
      <td>${esc(row.symbol || "")}</td>
      <td>${esc(row.direction || "NEUTRAL")}</td>
      <td>${esc(row.horizonSessions || "")}</td>
      <td><span class="tag ${row.status === "TARGET" ? "good" : row.status === "STOP" ? "bad" : "wait"}">${esc(row.status || "UNKNOWN")}</span></td>
      <td>${fmt(row.mfeR)}</td>
      <td>${fmt(row.maeR)}</td>
      <td>${esc(row.censorReason || "")}</td>
    </tr>`;
  }

  function apply(payload) {
    summaryPayload = {
      status: payload?.status || null,
      metrics: payload?.metrics || null
    };
    if (payload && Object.prototype.hasOwnProperty.call(payload, "observations")) {
      observationsPayload = payload.observations;
      observationsState = "LOADED";
    }
    const status = summaryPayload.status;
    const panel = document.getElementById("s9PitHomeworkPanel");
    const lock = document.getElementById("q5ValidationLock");
    if (!panel || !lock) return;

    if (!status) {
      panel.innerHTML = '<div class="s9-wait">WAIT_R16_STATUS_UNAVAILABLE</div><p>The backend validation status could not be read.</p>';
      lock.textContent = "PIT_NOT_APPROVED � R16 backend status unavailable � Not an order.";
      return;
    }

    const blockers = Array.isArray(status.blockers) ? status.blockers : [];
    const metrics = Array.isArray(summaryPayload.metrics?.metrics)
      ? summaryPayload.metrics.metrics
      : [];
    const observations = Array.isArray(observationsPayload?.observations)
      ? observationsPayload.observations
      : [];
    const blockerMarkup = blockers.length
      ? `<ul class="r16-blockers">${blockers.map((code) => `<li>${esc(code)}</li>`).join("")}</ul>`
      : "<p>No dataset/replay blocker is currently recorded.</p>";
    const metricMarkup = metrics.length
      ? `<div class="r16-cells">${metrics.map(metricCard).join("")}</div>`
      : '<div class="s9-wait">WAIT_R16_METRICS_NOT_AVAILABLE</div>';
    const rows = observations.slice(0, 30);
    const table = rows.length
      ? `<div class="r16-table-wrap"><table class="s9-table">
          <thead><tr><th>Symbol</th><th>Hypothesis</th><th>Horizon</th><th>Outcome</th><th>MFE R</th><th>MAE R</th><th>Reason</th></tr></thead>
          <tbody>${rows.map(observationRow).join("")}</tbody>
        </table></div>`
      : observationsState === "NOT_LOADED"
        ? '<p data-r16-observations-state="NOT_LOADED">Open the Evidence Inspector to load immutable path labels.</p>'
        : observationsState === "LOADING"
          ? '<div class="s9-wait" data-r16-observations-state="LOADING">WAIT_R16_OBSERVATIONS_LOADING</div>'
          : observationsState === "FAILED"
            ? '<div class="s9-wait" data-r16-observations-state="FAILED">WAIT_R16_OBSERVATIONS_UNAVAILABLE</div>'
            : "<p>No immutable observations have been stored.</p>";

    panel.innerHTML = `
      <div class="r16-summary">
        <span><small>Dataset</small><strong>${esc(status.datasetStatus)}</strong></span>
        <span><small>Validation</small><strong class="${stateClass(status.validationStatus)}">${esc(status.validationStatus)}</strong></span>
        <span><small>Exact cells</small><strong>${esc(status.exactCellCount ?? 0)}</strong></span>
        <span><small>Latest dataset</small><strong>${esc(status.latestDatasetRunId || "NONE")}</strong></span>
      </div>
      <div class="r16-notice">Evidence strength is not win probability. R16 validation does not authorize CONFIRMED, quantity, broker execution or orders.</div>
      <section class="r16-section"><h4>Why validation is held</h4>${blockerMarkup}</section>
      <section class="r16-section"><h4>Exact-cell validation</h4>${metricMarkup}</section>
      <section class="r16-section"><h4>Latest immutable path labels</h4>${table}</section>
    `;

    lock.innerHTML = `<strong>${esc(status.validationStatus)}</strong> � dataset ${esc(status.datasetStatus)} � ${esc(blockers[0] || "NO_RECORDED_BLOCKER")} � Not an order.`;
  }

  async function loadObservations() {
    if (observationsState === "LOADED") return observationsPayload;
    if (observationsRequest) return observationsRequest;
    observationsState = "LOADING";
    apply(summaryPayload);
    observationsRequest = fetch(OBSERVATIONS_PATH, {
      cache: "no-store",
      headers: { Accept: "application/json" }
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("HTTP " + response.status);
        observationsPayload = await response.json();
        observationsState = "LOADED";
        return observationsPayload;
      })
      .catch(() => {
        observationsPayload = null;
        observationsState = "FAILED";
        return null;
      })
      .finally(() => {
        observationsRequest = null;
        apply(summaryPayload);
      });
    return observationsRequest;
  }

  function bindLazyLoad() {
    const inspector = document.getElementById("q5Inspector");
    if (!inspector) return;
    inspector.addEventListener("toggle", () => {
      if (inspector.open) void loadObservations();
    });
    if (inspector.open) void loadObservations();
  }

  window.TrendForgeR16PitValidation = { apply, loadObservations, CONTRACT };
  bindLazyLoad();
})();
