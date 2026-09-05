(() => {
  "use strict";

  const CONTRACT = "trendforge.s3-watch-queue.v1";

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function metric(value, fallback = "UNKNOWN") {
    return value === null || value === undefined ? fallback : escapeHtml(value);
  }

  function rowMarkup(row) {
    const tags = (row.tags || []).slice(0, 5)
      .map((tag) => `<span class="s3-tag">${escapeHtml(tag)}</span>`).join("");
    const unknown = (row.whyUnknown || []).slice(0, 3).join(" · ") || "No optional gap";
    const profiles = (row.a3Profiles || []).map((value) => value.replace("DISC_EOD_", "")).join(", ") || "NONE";
    return `<tr>
      <td><strong>${escapeHtml(row.symbol)}</strong><small>${escapeHtml(profiles)}</small></td>
      <td><span class="chip ${row.researchState === "WATCH" ? "info" : "wait"}">${escapeHtml(row.researchState)}</span></td>
      <td>${metric(row.attentionPriority)}</td>
      <td><div class="s3-tags">${tags || '<span class="s3-tag muted">NO TAG</span>'}</div></td>
      <td>${metric(row.rvolEod)}</td>
      <td>${metric(row.rs1d)}</td>
      <td class="s3-unknown" title="${escapeHtml(unknown)}">${escapeHtml(unknown)}</td>
    </tr>`;
  }

  function panelMarkup(batch) {
    if (!batch) {
      return `<div class="s3-empty"><strong>WAIT_S3_NOT_READY</strong><span>Cheap discovery is unavailable for the current R1/R2 lineage.</span></div>`;
    }
    if (batch.schemaVersion !== CONTRACT) {
      return `<div class="s3-empty"><strong>WAIT_S3_SCHEMA_MISMATCH</strong><span>${escapeHtml(batch.schemaVersion)}</span></div>`;
    }
    const rows = Array.isArray(batch.rows) ? batch.rows : [];
    const state = batch.waitPartialScan ? "WAIT_PARTIAL_SCAN" : "WATCH_QUEUE_READY";
    return `<div class="s3-summary">
      <div><span>Queue</span><strong>${batch.totalWatchCount ?? rows.length}</strong></div>
      <div><span>Shown</span><strong>${rows.length}</strong></div>
      <div><span>Completeness</span><strong>${Math.round(Number(batch.completeness || 0) * 100)}%</strong></div>
      <div><span>Ceiling</span><strong>WATCH / WAIT</strong></div>
      <span class="chip ${batch.waitPartialScan ? "wait" : "info"}">${state}</span>
    </div>
    <div class="s3-table-wrap"><table class="s3-table">
      <thead><tr><th>Stock / A3</th><th>State</th><th>R2 order</th><th>Cheap tags</th><th>RVOL</th><th>RS 1D</th><th>Unknown / missing</th></tr></thead>
      <tbody>${rows.length ? rows.map(rowMarkup).join("") : '<tr><td colspan="7">No WATCH rows passed the current S3 ceiling.</td></tr>'}</tbody>
    </table></div>`;
  }

  function apply(batch) {
    const markup = panelMarkup(batch);
    ["s3WatchQueue", "s3WatchQueueOps"].forEach((id) => {
      const mount = document.getElementById(id);
      if (mount) mount.innerHTML = markup;
    });
    document.body.dataset.s3Mode = batch ? (batch.waitPartialScan ? "WAIT_PARTIAL_SCAN" : "LIVE_WATCH") : "WAIT";
    return batch && Array.isArray(batch.rows) ? batch.rows.length : 0;
  }

  window.TrendForgeS3CheapDiscovery = { contract: CONTRACT, apply };
})();
