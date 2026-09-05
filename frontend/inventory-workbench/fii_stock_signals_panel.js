(function (root) {
  'use strict';

  const POLL_MS = 60_000;
  const MAX_PILLS = 20;
  let timer = null;
  let controller = null;

  function apiUrl() {
    if (root.TRENDFORGE_FII_STOCK_SIGNALS_API_URL) {
      return root.TRENDFORGE_FII_STOCK_SIGNALS_API_URL;
    }
    const liveUrl = root.TRENDFORGE_LIVE_API_URL || 'http://127.0.0.1:8000/api/panels/live';
    try {
      return `${new URL(liveUrl).origin}/api/institutional/fii-stock-signals`;
    } catch (_error) {
      return 'http://127.0.0.1:8000/api/institutional/fii-stock-signals';
    }
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function validate(payload) {
    if (!payload || typeof payload !== 'object') throw new Error('invalid response');
    if (!Array.isArray(payload.largeDeals) || !Array.isArray(payload.fiiHoldingChanges)) {
      throw new Error('missing signal arrays');
    }
    const validSymbol = row => /^[A-Z0-9][A-Z0-9&_.-]{0,31}$/.test(
      String(row && row.symbol || '').trim().toUpperCase()
    );
    const usableHolding = row => {
      if (!row || row.signalType !== 'FII_HOLDING_CHANGE') return false;
      if (validSymbol(row)) return true;
      const name = String(row.companyName || row.name || '').trim();
      return Boolean(name);
    };
    const largeDeals = payload.largeDeals.filter(row => row &&
      row.signalType === 'LARGE_DEAL' && validSymbol(row));
    const fiiHoldingChanges = payload.fiiHoldingChanges.filter(usableHolding);
    return {
      generatedAt: payload.generatedAt || null,
      latestFetchedAt: payload.latestFetchedAt || null,
      warning: String(payload.warning || ''),
      largeDeals,
      fiiHoldingChanges
    };
  }

  function uniqueLatest(rows) {
    const sorted = rows.slice().sort((a, b) =>
      String(b.date || '').localeCompare(String(a.date || '')) ||
      String(a.symbol || '').localeCompare(String(b.symbol || '')));
    const seen = new Set();
    return sorted.filter(row => {
      const symbol = String(row.symbol || '').trim().toUpperCase();
      const name = String(row.companyName || row.name || '').trim().toUpperCase();
      const key = symbol || name;
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function formattedTime(value) {
    const parsed = new Date(value || '');
    if (Number.isNaN(parsed.getTime())) return 'Saved-data time unavailable';
    return `Latest saved fetch ${parsed.toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata', hour12: true, dateStyle: 'medium', timeStyle: 'short'
    })} IST`;
  }

  function dealPill(row) {
    const side = String(row.side || '').toUpperCase();
    const sideClass = side === 'BUY' ? 'fii-signal-side-buy' :
      side === 'SELL' ? 'fii-signal-side-sell' : 'fii-signal-side-neutral';
    const sideText = side === 'BUY' ? '▲ BUY' : side === 'SELL' ? '▼ SELL' : 'DEAL';
    return `<span class="fii-signal-pill" data-signal-type="LARGE_DEAL" ` +
      `title="${escapeHtml(`${row.dealType || 'LARGE'} · ${row.date || ''} · ${row.sourceKey || ''}`)}">` +
      `<strong>${escapeHtml(String(row.symbol).toUpperCase())}</strong>` +
      `<small class="${sideClass}">${sideText}</small></span>`;
  }

  function holdingPill(row) {
    const change = Number(row.fiiPctChange);
    const changeClass = change > 0 ? 'fii-change-positive' :
      change < 0 ? 'fii-change-negative' : 'fii-signal-side-neutral';
    const changeText = Number.isFinite(change) ? `${change > 0 ? '+' : ''}${change.toFixed(2)}%` : 'chg n/a';
    const label = String(row.symbol || row.companyName || row.name || '').trim() || 'UNNAMED';
    const identity = String(row.identityStatus || '').replace(/_/g, ' ') || 'IDENTITY';
    const hold = row.fiiPct == null
      ? (row.holdingLevelNote || 'holding level not supplied')
      : `hold ${Number(row.fiiPct).toFixed(2)}%`;
    const title = [
      identity, row.sourceKey || '', row.date || '', hold
    ].filter(Boolean).join(' · ');
    const nameOnly = !row.symbol;
    return `<span class="fii-signal-pill${nameOnly ? ' fii-signal-name-only' : ''}" data-signal-type="FII_HOLDING_CHANGE" ` +
      `title="${escapeHtml(title)}">` +
      `<strong>${escapeHtml(label)}</strong>` +
      `<small class="${changeClass}">${escapeHtml(changeText)}</small>` +
      `<small class="fii-identity">${escapeHtml(identity)}</small></span>`;
  }

  function pillGroup(rows, renderer, emptyText) {
    const unique = uniqueLatest(rows);
    const visible = unique.slice(0, MAX_PILLS);
    if (!visible.length) return `<div class="fii-signals-empty">${escapeHtml(emptyText)}</div>`;
    const more = unique.length > MAX_PILLS
      ? `<span class="fii-signals-more">+${unique.length - MAX_PILLS} more</span>` : '';
    return `<div class="fii-signals-pills">${visible.map(renderer).join('')}${more}</div>`;
  }

  function render(payload) {
    const host = root.document && root.document.getElementById('fii-stock-signals-panel');
    if (!host) return null;
    let data;
    try {
      data = validate(payload);
    } catch (_error) {
      host.innerHTML = '<div class="fii-signals-message fii-signals-error">WAIT · FII-related stock-name data unavailable</div>';
      return null;
    }
    host.innerHTML = `
      <div class="fii-signals-layout">
        <section class="fii-signals-heading">
          <div class="fii-signals-eyebrow">FII-related stock names</div>
          <div class="fii-signals-title">Saved official + holding-change evidence</div>
          <div class="fii-signals-time">${escapeHtml(formattedTime(data.latestFetchedAt))}</div>
        </section>
        <section class="fii-signals-group">
          <div class="fii-signals-group-title">Large deals · not certified FII</div>
          ${pillGroup(data.largeDeals, dealPill, 'No qualifying saved bulk/block stock names.')}
        </section>
        <section class="fii-signals-group">
          <div class="fii-signals-group-title">FII/FPI holding change · mapped or name-only</div>
          ${pillGroup(data.fiiHoldingChanges, holdingPill, 'No saved holding-change rows.')}
        </section>
      </div>
      <div class="fii-signals-warning">${escapeHtml(data.warning)}</div>`;
    return data;
  }

  async function refresh() {
    if (controller) controller.abort();
    controller = new AbortController();
    try {
      const response = await root.fetch(apiUrl(), {
        method: 'GET', cache: 'no-store', signal: controller.signal
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return render(await response.json());
    } catch (error) {
      if (error && error.name === 'AbortError') return null;
      render(null);
      return null;
    }
  }

  function start() {
    refresh();
    if (timer) root.clearInterval(timer);
    timer = root.setInterval(() => {
      if (!root.document || root.document.visibilityState === 'visible') refresh();
    }, POLL_MS);
  }

  function stop() {
    if (controller) controller.abort();
    if (timer) root.clearInterval(timer);
    timer = null;
  }

  const api = Object.freeze({ apiUrl, escapeHtml, validate, render, refresh, start, stop });
  root.FIIStockSignalsPanel = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
