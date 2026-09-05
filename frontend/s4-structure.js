(() => {
  "use strict";

  const CONTRACT = "trendforge.s4-structure-pack.v1";

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function rowMarkup(row) {
    const tags = (row.setupTags || [])
      .map((tag) => `<span class="s4-tag${tag.companionOnly ? " muted" : ""}" title="${escapeHtml(tag.correlationGroup)}">${escapeHtml(tag.tag)}</span>`)
      .join("");
    const patterns = (row.patternLane || [])
      .map((p) => `<span class="s4-tag pattern" title="display lane - never votes">${escapeHtml(p.pattern)}</span>`)
      .join("");
    return `<tr>
      <td><strong>${escapeHtml(row.symbol)}</strong></td>
      <td><span class="chip ${row.researchState === "REJECT" ? "bad" : "wait"}">${escapeHtml(row.researchState)}</span></td>
      <td><div class="s4-tags">${tags || '<span class="s4-tag muted">NO CLAIMED SETUP</span>'}${patterns}</div></td>
      <td class="s4-trigger">${escapeHtml(row.nextTrigger)}</td>
      <td class="s4-invalidation">${escapeHtml(row.invalidationCondition)}</td>
      <td><small>${escapeHtml((row.r14RunHash || "").slice(0, 12) || "NO_R14")}</small></td>
    </tr>`;
  }

  function panelMarkup(pack) {
    if (!pack) {
      return `<div class="s4-empty"><strong>WAIT_S4_NOT_READY</strong><span>No hash-matched R5 structure batch backs the pack for this lineage.</span></div>`;
    }
    if (pack.schemaVersion !== CONTRACT) {
      return `<div class="s4-empty"><strong>WAIT_S4_SCHEMA_MISMATCH</strong><span>${escapeHtml(pack.schemaVersion)}</span></div>`;
    }
    const rows = Array.isArray(pack.rows) ? pack.rows : [];
    const claimed = rows.filter(
      (r) => r.priceStructureRepresentativeClaimId || r.compressionRepresentativeClaimId
    ).length;
    return `<div class="s4-summary">
      <div><span>Pack rows</span><strong>${rows.length}</strong></div>
      <div><span>With structure claims</span><strong>${claimed}</strong></div>
      <div><span><code>confirmedCount</code> (pinned)</span><strong>${pack.confirmedCount ?? 0}</strong></div>
      <div><span>Ceiling</span><strong>LIVE_S4_WAIT_REJECT_ONLY</strong></div>
      <span class="chip wait">labels are not trade geometry</span>
    </div>
    <div class="s4-table-wrap"><table class="s4-table">
      <thead><tr><th>Symbol</th><th>Research state</th><th>Closed-bar setup tags</th><th>Next trigger (WAIT label)</th><th>Invalidation condition</th><th>R14 lineage</th></tr></thead>
      <tbody>${rows.length ? rows.map(rowMarkup).join("") : '<tr><td colspan="6">No hash-matched R5 rows for this lineage.</td></tr>'}</tbody>
    </table></div>`;
  }

  function apply(pack) {
    const markup = panelMarkup(pack);
    const mount = document.getElementById("s4StructurePanel");
    const opsMount = document.getElementById("s4StructureOps");
    if (mount) mount.innerHTML = markup;
    if (opsMount) opsMount.innerHTML = markup;
    document.body.dataset.s4Mode = pack ? "LIVE_WAIT_PACK" : "WAIT";
    return pack && Array.isArray(pack.rows) ? pack.rows.length : 0;
  }

  window.TrendForgeS4Structure = { contract: CONTRACT, apply };
})();
