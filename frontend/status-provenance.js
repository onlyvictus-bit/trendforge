/* Presentation only. Never a source registry, freshness gate or state resolver. */
(() => {
  'use strict';
  let mode = 'FIXTURE';
  let snapshot = null;
  let receivedAt = null;
  let lastError = '';
  let model = null;
  let view = 'all-stocks';
  let tool = '';

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (ch) =>
    ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'}[ch]));
  const text = (id, value) => {
    const node = document.getElementById(id);
    if (node) node.textContent = String(value ?? 'UNKNOWN');
  };
  const stamp = (value) => typeof value === 'string' && Number.isFinite(Date.parse(value))
    ? value : 'UNKNOWN';

  function render() {
    const a = snapshot?.attention;
    const usable = mode === 'SNAPSHOT';
    const s7 = usable ? snapshot?.s7State : null;
    const sameRun = !!a?.runHash && s7?.r2RunHash === a.runHash;
    const activation = sameRun && typeof s7.sourceActivationReady === 'boolean'
      ? (s7.sourceActivationReady ? 'OBSERVED (snapshot)' : 'LOCKED (snapshot)') : 'UNKNOWN';
    const labels = {
      FIXTURE: 'FIXTURE PREVIEW - NOT MARKET EVIDENCE',
      LOADING: 'REFRESHING - RETAINED VALUES ARE NOT REVALIDATED',
      SNAPSHOT: 'STORED RESEARCH SNAPSHOT - NOT A LIVE QUOTE',
      STALE: 'STALE / RETAINED SNAPSHOT - REFRESH FAILED'
    };
    text('snapshotMode', labels[mode]);
    text('runtimeSelectionMode', mode === 'SNAPSHOT' ? 'STORED SNAPSHOT' : mode);
    text('snapshotRunId', a?.runId || 'NONE');
    text('snapshotAsOf', stamp(snapshot?.structure?.decisionAt || a?.builtAt));
    text('snapshotReceivedAt', receivedAt || 'NOT RECEIVED');
    text('sourceActivationStatus', 'Activation: ' + activation);
    text('universeProvenance', a ? (usable ? 'STORED UNIVERSE' : 'RETAINED - NOT REVALIDATED') : 'FIXTURE UNIVERSE');
    if (a) {
      const rows = a.rows || [];
      text('headerRowCount', rows.length);
      text('headerDecisionCount', rows.length);
      text('headerBuyCount', rows.filter(r => r.evidenceDirection === 'BULLISH').length);
      text('headerSellCount', rows.filter(r => r.evidenceDirection === 'BEARISH').length);
      text('lastUpdated', stamp(a.builtAt));
      text('asOfTime', stamp(snapshot?.structure?.decisionAt || a.builtAt));
    }
    const counts = {};
    for (const row of a?.rows || []) {
      const key = row.freshness || 'UNKNOWN';
      counts[key] = (counts[key] || 0) + 1;
    }
    const freshness = a ? Object.entries(counts).map(([k, v]) => `${k}: ${v}`).join(', ') : 'UNKNOWN';
    text('snapshotFreshness', `${freshness || 'NO ROWS'} at snapshot creation; fetching does not revalidate source freshness.`);
    const date = document.getElementById('researchDate');
    if (date) {
      date.disabled = true;
      date.value = /^\d{4}-\d{2}-\d{2}$/.test(a?.tradingDate || '') ? a.tradingDate : '';
      date.title = 'Loaded snapshot trading date. Browse saved runs with History; this field does not query historical data.';
    }
    let viewLabel;
    if (view === 'history') viewLabel = 'HISTORICAL SAVED RUNS - read-only; never replace the current selection.';
    else if (view === 'tool' && tool === 'm_factor_history') viewLabel = 'FIXTURE HISTORY - demonstration only. Use History for persisted S8 runs.';
    else if (['all-stocks', 'radar', 'stock', 'sources'].includes(view)) viewLabel = labels[mode];
    else viewLabel = 'MIXED RESEARCH VIEW - only labelled API-backed panels contain observed data; other illustrations are fixtures.';
    text('viewProvenance', viewLabel);
    const errors = {...(snapshot?.errors || {})};
    if (s7 && !sameRun) errors.S7 = 'LINEAGE_MISMATCH_OR_MISSING: activation not projected';
    if (lastError) errors.refresh = lastError;
    const failures = document.getElementById('snapshotFailures');
    if (failures) failures.innerHTML = Object.entries(errors).length
      ? Object.entries(errors).map(([path, reason]) => `<p><code>${esc(path)}</code>: ${esc(reason)}</p>`).join('')
      : '<p>No request failure recorded. This does not establish data completeness or production readiness.</p>';
    const axes = [
      ['Code implemented', 'CODE CHECKPOINT', 'See docs/CURRENT_STATE.md; implementation is not runtime approval.'],
      ['Tests passed', 'NOT MEASURED BY THIS PAGE', 'Use dated CI and docs/VALIDATION.md; no permanent green badge.'],
      ['Data observed', usable ? 'SNAPSHOT RECEIVED' : 'NOT CURRENTLY VERIFIED', a?.runId || 'No R1/R2 snapshot received.'],
      ['Source freshness', 'SEPARATE SOURCE CHECK', freshness + '; measured at the recorded snapshot time, not page refresh.'],
      ['Research activation', activation, 'S7 snapshot only; never inferred from downloads, history or implementation.'],
      ['PIT validation', usable ? snapshot?.r16Status?.validationStatus || 'UNKNOWN' : 'UNKNOWN', 'R16 status response; not trading permission.'],
      ['Model approval', model?.modelState || 'UNKNOWN', 'Separate R18 response; request failure is UNKNOWN, not an approval result.'],
      ['Execution', 'SEPARATE CONTROLS - NOT ASSESSED', 'This read-only panel cannot arm orders or infer permission from any other row.']
    ];
    const body = document.getElementById('capabilityStatusBody');
    if (body) body.innerHTML = axes.map(([name, state, why]) =>
      `<tr><th scope="row">${esc(name)}</th><td>${esc(state)}</td><td>${esc(why)}</td></tr>`).join('');
    const banner = document.getElementById('statusProvenance');
    if (banner) banner.dataset.mode = mode;
  }

  window.TrendForgeStatusProvenance = {
    begin() { mode = 'LOADING'; lastError = ''; render(); },
    accept(payload, at = new Date().toISOString()) {
      snapshot = payload; receivedAt = at; mode = 'SNAPSHOT'; lastError = ''; render();
    },
    fail(message) { mode = snapshot ? 'STALE' : 'FIXTURE'; lastError = String(message); render(); },
    setView(nextView, nextTool = '') { view = nextView; tool = nextTool; render(); },
    governance(payload) { model = payload; render(); },
    inspect() { return {mode, runId: snapshot?.attention?.runId || null, receivedAt, view}; }
  };
  render();
})();