/* Isolated read-only S8 history. Does not call any current-selection renderer. */
(() => {
  'use strict';
  const BASE = '/api/v1/selection/scans';
  let generation = 0;
  const esc = (v) => String(v ?? 'UNKNOWN').replace(/[&<>"']/g, c =>
    ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'}[c]));
  const node = (id) => document.getElementById(id);
  async function get(path) {
    const control = new AbortController();
    const timer = setTimeout(() => control.abort(), 15000);
    try {
      const response = await fetch(path, {cache: 'no-store', signal: control.signal,
        headers: {Accept: 'application/json'}});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } finally { clearTimeout(timer); }
  }
  function unavailable(message) {
    const panel = node('historySnapshot');
    if (panel) panel.innerHTML = `<p role="status">HISTORY UNAVAILABLE: ${esc(message)}. No current state was changed.</p>`;
  }
  async function select(runId) {
    const mine = ++generation;
    const panel = node('historySnapshot');
    if (panel) panel.innerHTML = '<p role="status">Loading historical snapshot...</p>';
    try {
      if (typeof runId !== 'string' || !runId) throw new Error('Missing run ID');
      const batch = await get(BASE + '/' + encodeURIComponent(runId));
      if (mine !== generation) return null;
      if (batch.schemaVersion !== 'trendforge.s8-scan.v1' || batch.runId !== runId || !Array.isArray(batch.rows)) {
        throw new Error('HISTORY_SCHEMA_OR_ID_MISMATCH');
      }
      if (panel) panel.innerHTML = `<h3>HISTORICAL SNAPSHOT - NOT CURRENT</h3>
        <p>Run: <code>${esc(batch.runId)}</code></p>
        <p>Decision as-of: ${esc(batch.asOf)} | Trading date: ${esc(batch.tradingDate)} | Built: ${esc(batch.builtAt)}</p>
        <p>Recorded ceiling: ${esc(batch.acceptanceCeiling)}. These are past recorded states, not today's eligibility.</p>
        <p>${batch.rows.length} saved rows. Showing the first ${Math.min(100, batch.rows.length)}; no rows were changed.</p>
        <div class="status-table-wrap"><table><thead><tr><th>Symbol</th><th>Recorded state</th><th>Recorded direction</th></tr></thead>
        <tbody>${batch.rows.slice(0, 100).map(row => `<tr><td>${esc(row.symbol)}</td><td>${esc(row.publicState)}</td><td>${esc(row.evidenceDirection)}</td></tr>`).join('')}</tbody></table></div>
        <details><summary>Recorded lineage</summary><pre>${esc(JSON.stringify(batch.lineage || {}, null, 2))}</pre></details>`;
      return batch;
    } catch (error) {
      if (mine === generation) unavailable(error.message);
      return null;
    }
  }
  async function load() {
    const mine = ++generation;
    const selectNode = node('historyRunSelect');
    if (selectNode) { selectNode.disabled = true; selectNode.innerHTML = '<option>Loading saved runs...</option>'; }
    const panel = node('historySnapshot');
    if (panel) panel.innerHTML = '<p>Choose an immutable saved scan. No current refresh or collector is invoked.</p>';
    try {
      const payload = await get(BASE + '?limit=100');
      if (mine !== generation) return null;
      if (!Array.isArray(payload.runs) || payload.runs.some(r => !r || typeof r.runId !== 'string' || !r.runId)) {
        throw new Error('HISTORY_LIST_SCHEMA_MISMATCH');
      }
      if (selectNode) {
        selectNode.innerHTML = '<option value="">Choose a saved run</option>' + payload.runs.map(r =>
          `<option value="${esc(r.runId)}">${esc(r.asOf)} | ${esc(r.runId)}</option>`).join('');
        selectNode.disabled = payload.runs.length === 0;
      }
      if (!payload.runs.length && panel) panel.innerHTML = '<p>No saved S8 scans. No history is fabricated from current data or fixtures.</p>';
      return payload;
    } catch (error) {
      if (mine === generation) {
        if (selectNode) selectNode.innerHTML = '<option>History unavailable</option>';
        unavailable(error.message);
      }
      return null;
    }
  }
  window.TrendForgeScanHistory = {load, select};
  const dropdown = node('historyRunSelect');
  if (dropdown) dropdown.addEventListener('change', () => {
    if (dropdown.value) void select(dropdown.value);
    else {
      ++generation;
      const panel = node('historySnapshot');
      if (panel) panel.innerHTML = '<p>Choose an immutable saved scan. No current state was changed.</p>';
    }
  });
  const refresh = node('historyRefresh');
  if (refresh) refresh.addEventListener('click', () => { void load(); });
})();