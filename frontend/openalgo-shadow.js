(() => {
  "use strict";

  const CONTRACT = "trendforge.openalgo-shadow.v1";

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function show(value, fallback = "—") {
    return value === null || value === undefined || value === "" ? fallback : escapeHtml(value);
  }

  function json(value) {
    try { return escapeHtml(JSON.stringify(value)); }
    catch (_error) { return "UNSERIALIZABLE"; }
  }

  function voteMarkup(vote) {
    const status = vote.applicability || "UNAVAILABLE";
    return `<div class="oa-vote" data-state="${escapeHtml(status)}">
      <div><strong>${escapeHtml(vote.voteId || vote.vote_id)}</strong><span>${escapeHtml(status)}</span></div>
      <p>${escapeHtml(vote.purpose || "")}</p>
      <code>${json(vote.rawValue ?? vote.raw_value)}</code>
      <small>${escapeHtml(vote.interpretation || "")}</small>
    </div>`;
  }

  function rowMarkup(row) {
    const blockers = row.missingOrConflicting || row.missing_or_conflicting || [];
    const votes = row.optionVotes || row.option_votes || [];
    const concentration = row.optionConcentration || row.option_concentration || {};
    const profile = row.openalgoProfileState || row.openalgo_profile_state || "WAIT";
    const baseState = row.basePublicState || row.base_public_state || "WAIT";
    const publicState = row.publicState || row.public_state || baseState;
    const qty = Number(row.researchQuantity || row.research_quantity || 0);
    const unit = row.qtyUnit || row.qty_unit || "shares";
    return `<article class="oa-shadow-card" data-profile="${escapeHtml(profile)}">
      <header>
        <div><strong>${escapeHtml(row.symbol)}</strong><small>${escapeHtml(row.evidenceDirection || row.evidence_direction || "UNKNOWN")}</small></div>
        <span class="chip ${profile === "WATCH" ? "info" : "wait"}">${escapeHtml(profile)}</span>
      </header>
      <div class="oa-state-law">Base ${escapeHtml(baseState)} → public ${escapeHtml(publicState)} unchanged</div>
      <div class="oa-metrics">
        <span><small>REST</small><strong>${show(row.restQualityState || row.rest_quality_state)}</strong></span>
        <span><small>Age</small><strong>${show(row.restAgeSeconds ?? row.rest_age_seconds)}s</strong></span>
        <span><small>Entry</small><strong>${show(row.researchEntry ?? row.research_entry)}</strong></span>
        <span><small>Stop</small><strong>${show(row.researchStop ?? row.research_stop)}</strong></span>
        <span><small>T1 / T2</small><strong>${show(row.researchT1 ?? row.research_t1)} / ${show(row.researchT2 ?? row.research_t2)}</strong></span>
        <span><small>Research qty</small><strong>${qty} ${escapeHtml(unit)}</strong></span>
      </div>
      <div class="oa-concentration">${Number(concentration.voteCount || concentration.vote_count || votes.length)} purpose views · ${Number(concentration.datasetRootCount || concentration.dataset_root_count || 0)} dataset root · ${Number(concentration.independentConfirmationCount || concentration.independent_confirmation_count || 0)} independent confirmations</div>
      <div class="oa-votes">${votes.map(voteMarkup).join("") || '<p class="oa-empty">Option-purpose views unavailable.</p>'}</div>
      <div class="oa-blockers"><strong>Missing / conflicting</strong><span>${blockers.length ? blockers.map(escapeHtml).join(" · ") : "none"}</span></div>
      <div class="oa-next"><strong>Next</strong><span>${escapeHtml(row.nextCondition || row.next_condition || "Keep evidence current.")}</span></div>
    </article>`;
  }

  function inspectorMarkup(payload) {
    const rows = payload.rows || [];
    const entries = rows.flatMap((row) => (row.optionVotes || row.option_votes || []).map((vote) => ({ row, vote })));
    return `<details class="oa-inspector-details">
      <summary>OpenAlgo lineage and formula inspector</summary>
      <div class="oa-inspector-meta">baseRunHash ${escapeHtml(payload.baseRunHash || payload.base_run_hash || "—")} · base unchanged ${String(payload.baseOutputUnchanged ?? payload.base_output_unchanged ?? true)} · executable ${String(payload.executable === true)}</div>
      ${entries.map(({ row, vote }) => `<div class="oa-lineage">
        <strong>${escapeHtml(row.symbol)} · ${escapeHtml(vote.voteId || vote.vote_id)}</strong>
        <span>formula ${escapeHtml(vote.formulaVersion || vote.formula_version)}</span>
        <span>root ${escapeHtml(vote.datasetRootId || vote.dataset_root_id)}</span>
        <span>snapshot ${escapeHtml(vote.snapshotId || vote.snapshot_id)}</span>
        <span>raw ${escapeHtml(vote.rawContentHash || vote.raw_content_hash)}</span>
      </div>`).join("") || '<p class="oa-empty">No live lineage rows. Disabled mode performs no network or storage work.</p>'}
    </details>`;
  }

  function apply(payload) {
    const panel = document.getElementById("openAlgoShadowPanel");
    const meta = document.getElementById("openAlgoShadowMeta");
    const rows = document.getElementById("openAlgoShadowRows");
    const inspector = document.getElementById("openAlgoShadowInspector");
    if (!panel || !meta || !rows || !inspector) return;
    if (!payload || payload.schemaVersion !== CONTRACT || !payload.activation) {
      meta.textContent = "WAIT_R17_DTO";
      meta.className = "tag wait";
      rows.innerHTML = '<p class="oa-empty">R17 OpenAlgo shadow DTO is unavailable.</p>';
      inspector.innerHTML = "";
      return;
    }
    const stage = payload.activation.stage || "DISABLED";
    const blockers = payload.activation.blockerCodes || payload.activation.blocker_codes || [];
    meta.textContent = `${stage} · ${blockers.join(" · ") || "proof complete"}`;
    meta.className = `tag ${stage === "SHADOW_LIVE" ? "good" : "wait"}`;
    const records = payload.rows || [];
    rows.innerHTML = records.length
      ? records.map(rowMarkup).join("")
      : `<div class="oa-disabled"><strong>${escapeHtml(stage)}</strong><span>No OpenAlgo network, socket or storage activity. R1-R16 remains unchanged.</span></div>`;
    inspector.innerHTML = inspectorMarkup(payload);
  }

  window.TrendForgeOpenAlgoShadow = { apply, contract: CONTRACT };
})();
