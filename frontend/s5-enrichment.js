(() => {
  "use strict";

  const CONTRACT = "trendforge.s5-enrichment.v1";

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

  function chip(label, value, tone) {
    return `<span class="s5-chip ${tone || ""}" title="${escapeHtml(label)}">${escapeHtml(value)}</span>`;
  }

  function rowMarkup(row) {
    const delivery = row.delivery || {};
    const fo = row.foPackage || {};
    const opt = row.optionsPackage || {};
    const deal = row.namedDeal || {};
    const shp = row.shpContext || {};
    const mf = row.delayedMf;
    return `<tr>
      <td><strong>${escapeHtml(row.symbol)}</strong></td>
      <td>${chip(delivery.status, delivery.status === "FORBIDDEN_ON_INTRADAY" ? "N/A EOD-only" : metric(delivery.z, "UNKNOWN"), delivery.status === "DELIVERY_Z_PIT20" ? "info" : "")}</td>
      <td>${chip("FO package", escapeHtml(fo.quadrant || fo.status), fo.quadrant ? "info" : "")}</td>
      <td>${chip("Options package", escapeHtml(opt.status), opt.status === "UNKNOWN_NEEDS_R12" ? "" : "info")}</td>
      <td>${chip("Named deal", escapeHtml(deal.code), deal.isFiiClaim ? "warn" : "")}</td>
      <td>${mf ? chip("Delayed MF", escapeHtml(mf.code), "delayed") : '<span class="s5-chip muted">MF UNKNOWN</span>'}</td>
      <td>${metric(shp.promoterPct, "-")}% / ${metric(shp.publicPct, "-")}% <small>fiiΔ null</small></td>
      <td class="s5-unknown" title="${escapeHtml((row.whyUnknown || []).join(" · "))}">${escapeHtml((row.whyUnknown || []).slice(0, 3).join(" · ") || "none")}</td>
    </tr>`;
  }

  function panelMarkup(batch) {
    if (!batch) {
      return `<div class="s5-empty"><strong>WAIT_S5_NOT_READY</strong><span>Bounded enrichment needs a hash-matched S4 structure pack.</span></div>`;
    }
    if (batch.schemaVersion !== CONTRACT) {
      return `<div class="s5-empty"><strong>WAIT_S5_SCHEMA_MISMATCH</strong><span>${escapeHtml(batch.schemaVersion)}</span></div>`;
    }
    const rows = Array.isArray(batch.rows) ? batch.rows : [];
    return `<div class="s5-summary">
      <div><span>Shortlist source</span><strong>${escapeHtml(batch.shortlistSource)}</strong></div>
      <div><span>Enriched</span><strong>${rows.length} / ${batch.shortlistCount ?? rows.length}</strong></div>
      <div><span>Market FII net</span><strong>${metric(batch.marketFii && batch.marketFii.netCrore, "UNKNOWN")} <small>MARKET_WIDE_NOT_PER_STOCK</small></strong></div>
      <div><span>Ceiling</span><strong>LIVE_S5_ENRICH_WAIT_ONLY</strong></div>
      <span class="chip wait">options stay UNKNOWN_NEEDS_R12 until a fresh chain is proven</span>
    </div>
    <div class="s5-table-wrap"><table class="s5-table">
      <thead><tr><th>Stock</th><th>Delivery z (EOD)</th><th>FO OI package</th><th>OPTIONS_PACKAGE</th><th>Named deal</th><th>Delayed MF</th><th>SHP promoter/public</th><th>Why unknown</th></tr></thead>
      <tbody>${rows.length ? rows.map(rowMarkup).join("") : '<tr><td colspan="8">No structure-claimed shortlist names for this lineage.</td></tr>'}</tbody>
    </table></div>`;
  }

  function apply(batch) {
    const markup = panelMarkup(batch);
    ["s5EnrichmentPanel", "s5EnrichmentOps"].forEach((id) => {
      const mount = document.getElementById(id);
      if (mount) mount.innerHTML = markup;
    });
    document.body.dataset.s5Mode = batch ? "LIVE_ENRICH_WAIT" : "WAIT";
    return batch && Array.isArray(batch.rows) ? batch.rows.length : 0;
  }

  window.TrendForgeS5Enrichment = { contract: CONTRACT, apply };
})();
