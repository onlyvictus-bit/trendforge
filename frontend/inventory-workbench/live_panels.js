// One TrendForge snapshot for Sector, Consensus and Screener. Live sessions
// fail closed; closed sessions may show clearly-labelled saved research data.
(function (root) {
  'use strict';

  const CONTRACT = 'trendforge.livePanels.v1';
  const API_URL = () => root.TRENDFORGE_LIVE_API_URL ||
    'http://127.0.0.1:8000/api/panels/live';
  const MANUAL_REFRESH_API_URL = () => root.TRENDFORGE_MANUAL_REFRESH_API_URL ||
    API_URL().replace(/\/api\/panels\/live(?:\?.*)?$/, '/api/market-data/refresh');
  const POLL_MS = 60_000;

  const LIVE_OWNED_KEYS = new Set([
    'nse_variations_gainers', 'nse_variations_loosers',
    'nse_volume_gainers', 'nse_most_active_volume',
    'nse_most_active_value', 'nse_all_indices',
    'nse_oi_spurts', 'nse_most_active_underlying',
    'nse_large_deals_snapshot', 'nse_preopen_fo'
  ]);
  const CLOSED_RESEARCH_OVERLAY_KEYS = new Set([
    'nse_bhavcopy_eod', 'nse_large_deals', 'nse_trade_to_trade',
    'nse_board_meetings', 'nse_most_active_futures',
    'nse_most_active_options', 'nse_ipo_issue_calendar',
    'nse_pr_market_snapshot',
    // Phase-1 30-pack READY sources (research overlay)
    'nse_fno_ban', 'nse_participant_oi', 'nse_mto_delivery',
    'nse_short_selling', 'bse_fo_bhavcopy', 'amfi_nav', 'nse_preopen_cash',
    // Phase-2 30-pack
    'bse_insider_trading', 'nse_option_chain_nifty', 'nse_option_chain_banknifty',
    'lbma_gold_silver_fix', 'eia_natgas_storage', 'usda_wasde_cornell',
    'nse_fii_derivatives_stats',
    // Phase-3 multi-step
    'rbi_fbil_usdinr', 'nse_index_option_chain_v3',
    'cdsl_fpi_fortnightly', 'dgcis_trade_data',
    // Finish set
    'yahoo_cme_proxy', 'yahoo_lme_proxy',
    'mcx_market_watch', 'mcx_option_chain', 'mcx_top_participants',
    'mcx_warehouse_stocks', 'mcx_delivery_reports', 'ncdex_bhavcopy',
    'amfi_portfolio_disclosure', 'nse_bulk_deals_today_csv',
    'nse_bulk_deal_symbol', 'nse_quote_equity_trade_info',
    'screener_in_fii_holding_change', 'tickertape_fii_holding_change_3m',
    'dhan_fii_holding_change', 'equitymaster_fii_buys_reference'
  ]);
  const OVERLAY_OWNED_KEYS = new Set([
    ...LIVE_OWNED_KEYS,
    ...CLOSED_RESEARCH_OVERLAY_KEYS
  ]);

  // These sources can alter a price score or consensus vote. Their catalog
  // samples are never allowed into panel calculations when live data is absent.
  const NO_STATIC_CALCULATION_KEYS = new Set([
    ...LIVE_OWNED_KEYS,
    'nse_bhavcopy_eod', 'bse_bhavcopy_eod', 'nse_fo_bhavcopy',
    'nse_sector_constituents',
    'nse_oi_spurts_contracts',
    'nse_live_equity_derivatives_stock_opt', 'nse_option_chain_equity',
    'nse_asm', 'nse_gsm',
    'nse_large_deals', 'nse_block_deal', 'nse_block_deal_live',
    'nse_pit_symbol', 'bse_bulk_deals', 'bse_block_deals'
  ]);

  let catalogInventory = [];
  let generation = 0;
  let activeController = null;
  let timer = null;
  let lastRefreshAt = 0;

  function formatCollectorSchedule(payload) {
    const times = Array.isArray(payload && payload.scheduledTimesIst)
      ? payload.scheduledTimesIst.filter(Boolean) : [];
    const count = Number(payload && payload.sourceCount);
    const schedule = times.length ? `Auto ${times.join(' · ')} IST` : 'Auto schedule unavailable';
    return Number.isFinite(count) ? `${schedule} · ${count} sources` : schedule;
  }

  async function collectorRequest(url, options) {
    const response = await root.fetch(url, {
      cache: 'no-store',
      ...(options || {})
    });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const payload = await response.json();
        if (payload && payload.detail) detail = payload.detail;
      } catch (_error) {
        // Keep the HTTP status when the response is not JSON.
      }
      throw new Error(detail);
    }
    return response.json();
  }

  function getManualRefreshStatus() {
    return collectorRequest(`${MANUAL_REFRESH_API_URL()}/status`);
  }

  function waitMs(milliseconds) {
    return new Promise(resolve => root.setTimeout(resolve, Math.max(0, milliseconds)));
  }

  async function pollManualRefresh(options) {
    const pollIntervalMs = Number.isFinite(options && options.pollIntervalMs)
      ? options.pollIntervalMs : 1500;
    const maxPolls = Number.isFinite(options && options.maxPolls)
      ? options.maxPolls : 600;
    const onStatus = options && typeof options.onStatus === 'function'
      ? options.onStatus : () => {};
    for (let attempt = 0; attempt < maxPolls; attempt++) {
      if (attempt || pollIntervalMs > 0) await waitMs(pollIntervalMs);
      const status = await getManualRefreshStatus();
      onStatus(status);
      if (String(status.state || '').toUpperCase() !== 'RUNNING') return status;
    }
    throw new Error('Refresh is still running; check collector status again shortly');
  }

  async function requestManualRefresh(options) {
    const onStatus = options && typeof options.onStatus === 'function'
      ? options.onStatus : () => {};
    const started = await collectorRequest(MANUAL_REFRESH_API_URL(), { method: 'POST' });
    onStatus(started);
    if (String(started.state || '').toUpperCase() !== 'RUNNING') return started;
    return pollManualRefresh(options || {});
  }

  async function refreshAfterManualCompletion(payload) {
    if (String(payload && payload.state || '').toUpperCase() !== 'COMPLETED') {
      return null;
    }
    const updates = [refresh({ refresh: true, force: true })];
    if (root.FIIStockSignalsPanel &&
        typeof root.FIIStockSignalsPanel.refresh === 'function') {
      updates.push(root.FIIStockSignalsPanel.refresh());
    }
    return Promise.all(updates);
  }

  function collectorResultText(payload) {
    const state = String(payload && payload.state || 'OFFLINE').toUpperCase();
    if (state === 'RUNNING') return `Downloading ${payload.sourceCount || ''} sources…`.trim();
    if (state === 'COMPLETED') {
      return `Saved ${payload.successfulCount || 0} · fallback ${payload.lastGoodCount || 0} · failed ${payload.failedCount || 0}`;
    }
    if (state === 'LEASE_HELD') return 'Collector already running';
    if (state === 'IDLE') return 'Ready';
    return payload && (payload.error || payload.reason) || state.replace(/_/g, ' ');
  }

  function renderCollectorControl(payload) {
    if (!root.document) return;
    const button = root.document.getElementById('manual-refresh-button');
    const schedule = root.document.getElementById('collector-schedule');
    const result = root.document.getElementById('collector-result');
    if (schedule) schedule.textContent = formatCollectorSchedule(payload || {});
    if (result) result.textContent = collectorResultText(payload || {});
    if (button) {
      const running = String(payload && payload.state || '').toUpperCase() === 'RUNNING';
      button.disabled = running;
      button.setAttribute('aria-busy', running ? 'true' : 'false');
      button.title = running ? 'Market-data refresh is running' : 'Download every registered source now';
    }
  }

  async function bindManualRefreshControl() {
    if (!root.document) return;
    const button = root.document.getElementById('manual-refresh-button');
    if (!button || button.dataset.bound === 'true') return;
    button.dataset.bound = 'true';
    button.addEventListener('click', async () => {
      try {
        const finalStatus = await requestManualRefresh({ onStatus: renderCollectorControl });
        renderCollectorControl(finalStatus);
        await refreshAfterManualCompletion(finalStatus);
      } catch (error) {
        renderCollectorControl({ state: 'FAILED', error: String(error && error.message || error) });
      }
    });
    try {
      const initial = await getManualRefreshStatus();
      renderCollectorControl(initial);
      if (String(initial.state || '').toUpperCase() === 'RUNNING') {
        const finalStatus = await pollManualRefresh({ onStatus: renderCollectorControl });
        renderCollectorControl(finalStatus);
        await refreshAfterManualCompletion(finalStatus);
      }
    } catch (error) {
      renderCollectorControl({ state: 'OFFLINE', error: String(error && error.message || error) });
    }
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function keysOf(item) {
    return String(item && item.active_source_keys || item && item.source_key || '')
      .split('|').map(key => key.trim()).filter(Boolean);
  }

  function validateSnapshot(snapshot) {
    if (!snapshot || snapshot.contract !== CONTRACT) {
      throw new Error(`live panels contract must be ${CONTRACT}`);
    }
    if (!snapshot.snapshotId || !snapshot.market || !snapshot.panels) {
      throw new Error('live panels snapshot is missing identity, market, or panel states');
    }
    for (const name of ['sector', 'consensus', 'screener']) {
      if (!snapshot.panels[name] || !snapshot.panels[name].state) {
        throw new Error(`live panels snapshot is missing ${name} state`);
      }
    }
    return snapshot;
  }

  function buildPanelInventory(base, snapshot, panelName) {
    const merged = clone(Array.isArray(base) ? base : []);
    const byKey = new Map();
    const downloadedKeys = new Set(Object.keys(snapshot && snapshot.sources || {}));
    const panelState = panelName && snapshot && snapshot.panels && snapshot.panels[panelName]
      ? String(snapshot.panels[panelName].state || '').toUpperCase() : null;
    const marketSession = snapshot && snapshot.market
      ? String(snapshot.market.session || '').toUpperCase() : null;
    const useClosedResearch = panelState === 'MARKET_CLOSED' && marketSession === 'MARKET_CLOSED';

    for (const item of merged) {
      for (const key of keysOf(item)) if (!byKey.has(key)) byKey.set(key, item);
      if (keysOf(item).some(key =>
        NO_STATIC_CALCULATION_KEYS.has(key) || downloadedKeys.has(key))) {
        // Catalog samples can be days old. Clear them in every session before
        // applying the API overlay; otherwise an old high-priority intraday
        // board can silently outrank a current downloaded EOD row after close.
        item.records_sample = [];
        item.sample_row = {};
        item.panel_input_state = useClosedResearch
          ? 'CLOSED_STATIC_SAMPLE_BLOCKED' : 'STATIC_SAMPLE_BLOCKED';
        item.live_source_status = useClosedResearch
          ? 'NO_CURRENT_DOWNLOAD' : item.live_source_status;
      }
    }

    const panelAllowsCalculation = !panelName ||
      ['LIVE', 'PARTIAL', 'PRE_OPEN', 'STALE', 'MARKET_CLOSED', 'WAIT'].includes(panelState);
    const mayUseOverlay = Boolean(snapshot && snapshot.market && panelAllowsCalculation);
    for (const overlay of mayUseOverlay && Array.isArray(snapshot.inventoryOverlay)
      ? snapshot.inventoryOverlay : []) {
      const key = String(overlay.source_key || overlay.active_source_keys || '').trim();
      const item = byKey.get(key);
      if (!item) continue;
      item.records_sample = clone(overlay.records_sample || []);
      item.sample_row = {};
      item.data_date = overlay.data_date;
      item.fetched_at = overlay.fetched_at;
      item.records_scope = overlay.records_scope || 'live_normalized_records';
      item.source_row_count = overlay.source_row_count;
      item.normalized_row_count = overlay.normalized_row_count;
      const researchOnly = String(overlay.live_source_status || '').toUpperCase() === 'RESEARCH_ONLY';
      item.live_source_status = researchOnly
        ? 'RESEARCH_ONLY' : (overlay.live_source_status || 'FRESH');
      item.panel_input_state = researchOnly
        ? 'RESEARCH_LAST_SAVED' : 'LIVE_OVERLAY';
    }
    return merged;
  }

  function selectedSources(snapshot, sourceKeys) {
    const sources = snapshot && snapshot.sources || {};
    if (!Array.isArray(sourceKeys) || !sourceKeys.length) return Object.values(sources);
    return sourceKeys.map(key => sources[key]).filter(Boolean);
  }

  function latestSourceTimestamp(snapshot, sourceKeys) {
    const timestamps = selectedSources(snapshot, sourceKeys)
      .flatMap(source => [source && source.dataAsOf, source && source.fetchedAt])
      .filter(Boolean)
      .map(value => ({ value, time: Date.parse(value) }))
      .filter(item => Number.isFinite(item.time))
      .sort((a, b) => b.time - a.time);
    return timestamps.length ? timestamps[0].value : null;
  }

  function normalizeDataDate(value) {
    const text = String(value || '').trim();
    const iso = text.match(/\d{4}-\d{2}-\d{2}/);
    if (iso) return iso[0];
    const parsed = Date.parse(text);
    return Number.isFinite(parsed) ? new Date(parsed).toISOString().slice(0, 10) : null;
  }

  function latestSourceDataDate(snapshot, sourceKeys) {
    const dates = selectedSources(snapshot, sourceKeys)
      .map(source => normalizeDataDate(source && source.tradingDate))
      .filter(Boolean).sort().reverse();
    return dates[0] || null;
  }

  function latestInventoryDataDate(inventory, sourceKeys) {
    const wanted = new Set(Array.isArray(sourceKeys) ? sourceKeys : []);
    const dates = [];
    for (const item of Array.isArray(inventory) ? inventory : []) {
      if (wanted.size && !keysOf(item).some(key => wanted.has(key))) continue;
      const rows = Array.isArray(item.records_sample) ? item.records_sample : [];
      const candidates = [item.data_date];
      for (const row of rows.slice(0, 25)) {
        candidates.push(
          row && row.tradeDate,
          row && row.dataDate,
          row && row.previousDay,
          row && row.as_on_date,
          row && row.date
        );
      }
      for (const value of candidates) {
        const normalized = normalizeDataDate(value);
        if (normalized) dates.push(normalized);
      }
    }
    dates.sort().reverse();
    return dates[0] || null;
  }

  function formatIstTimestamp(value) {
    if (!value || !Number.isFinite(Date.parse(value))) return 'time unavailable';
    return new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
      hour12: false
    }).format(new Date(value)).replace(',', '') + ' IST';
  }

  function panelStatusModel(snapshot, inventories) {
    const tradingDate = snapshot && snapshot.market && snapshot.market.tradingDate || 'unknown';
    const snapshotId = snapshot && snapshot.snapshotId || 'none';
    const generatedAt = snapshot && snapshot.generatedAt || null;
    const refreshState = snapshot && snapshot.refresh && snapshot.refresh.state || 'OFFLINE';
    const result = {};
    for (const name of ['sector', 'consensus', 'screener']) {
      const panel = snapshot && snapshot.panels && snapshot.panels[name] || {};
      const freshSources = panel.freshSources || [];
      const researchSources = panel.researchSources || [];
      const candidateSources = panel.researchSourceCandidates || panel.requiredSources || [];
      const activitySources = freshSources.length
        ? [...freshSources, ...researchSources]
        : (researchSources.length ? researchSources : candidateSources);
      const sourceTimestamp = latestSourceTimestamp(snapshot, activitySources);
      const dataDate = latestSourceDataDate(snapshot, activitySources) ||
        latestInventoryDataDate(inventories && inventories[name], candidateSources);
      const ages = freshSources.map(key => snapshot.sources && snapshot.sources[key] && snapshot.sources[key].ageSec)
        .filter(Number.isFinite);
      result[name] = {
        state: panel.state || 'OFFLINE',
        snapshotId,
        tradingDate,
        dataDate,
        dataFreshness: dataDate && tradingDate !== 'unknown' && dataDate < tradingDate
          ? 'STALE_DATA' : 'CURRENT_DAY',
        generatedAt,
        activityAt: sourceTimestamp || generatedAt,
        activityLabel: sourceTimestamp ? 'Fetched' : 'Panel job',
        refreshState,
        ageSec: ages.length ? Math.max(...ages) : null,
        reason: panel.missingOrStaleSources && panel.missingOrStaleSources.length
          ? `Missing/stale: ${panel.missingOrStaleSources.join(', ')}` : ''
      };
    }
    return result;
  }

  function statusHtml(name, model) {
    const state = String(model.state || 'OFFLINE').toUpperCase();
    const stateLabel = state.replace(/_/g, ' ');
    const age = Number.isFinite(model.ageSec) ? ` · ${model.ageSec}s old` : '';
    const dataFreshness = model.dataFreshness === 'STALE_DATA' ? ' · STALE DATA' : '';
    const dateLabel = model.dataDate
      ? `Data ${model.dataDate}`
      : model.tradingDate === 'unknown'
        ? 'data date unavailable'
        : `Trading day ${model.tradingDate}`;
    const activityLabel = `${model.activityLabel || 'Panel job'} ${formatIstTimestamp(model.activityAt)}`;
    const title = [
      `Snapshot ${model.snapshotId}`,
      `Trading date ${model.tradingDate}`,
      dateLabel,
      activityLabel,
      model.reason,
      state === 'MARKET_CLOSED'
        ? 'Saved records are shown for research only; they are not live.'
        : 'LIVE covers required P0 sources; slower B/C evidence remains informational.'
    ].filter(Boolean).join(' · ');
    return `<div class="live-panel-status live-state-${state.toLowerCase().replace(/_/g, '-') }" ` +
      `data-live-panel="${name}" data-snapshot-id="${model.snapshotId}" title="${escapeHtml(title)}">` +
      `<strong>${stateLabel}</strong><span>· ${dateLabel}${age}${dataFreshness}</span>` +
      `<time datetime="${escapeHtml(model.activityAt || '')}">${escapeHtml(activityLabel)}</time></div>`;
  }

  function escapeHtml(value) {
    return String(value || '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function prependStatus(hostId, name, model) {
    const host = root.document && root.document.getElementById(hostId);
    if (!host) return;
    host.insertAdjacentHTML('afterbegin', statusHtml(name, model));
  }

  function render(snapshot) {
    const sectorInventory = buildPanelInventory(catalogInventory, snapshot, 'sector');
    const consensusInventory = buildPanelInventory(catalogInventory, snapshot, 'consensus');
    const screenerInventory = buildPanelInventory(catalogInventory, snapshot, 'screener');
    const status = panelStatusModel(snapshot, {
      sector: sectorInventory,
      consensus: consensusInventory,
      screener: screenerInventory
    });

    if (typeof root.renderSectorScreenerPanel === 'function') {
      root.renderSectorScreenerPanel(sectorInventory);
      prependStatus('sector-screener-panel', 'sector', status.sector);
    }
    if (typeof root.renderConsensusStrip === 'function') {
      root.renderConsensusStrip(consensusInventory);
      prependStatus('consensus-strip', 'consensus', status.consensus);
    }
    if (typeof root.renderScreenerPanel === 'function') {
      root.renderScreenerPanel(screenerInventory);
      prependStatus('screener-panel', 'screener', status.screener);
    }
    root.panelInventory = {
      sector: sectorInventory,
      consensus: consensusInventory,
      screener: screenerInventory
    };
    root.livePanelsSnapshot = snapshot || null;
    return root.panelInventory;
  }

  async function refresh(options) {
    const requestGeneration = ++generation;
    if (activeController) activeController.abort();
    activeController = new AbortController();
    const allowRefresh = !options || options.refresh !== false;
    const force = Boolean(options && options.force);
    const url = `${API_URL()}?maxAgeSec=300&refresh=${allowRefresh ? 'true' : 'false'}&force=${force ? 'true' : 'false'}`;
    try {
      const response = await root.fetch(url, {
        method: 'GET',
        cache: 'no-store',
        signal: activeController.signal
      });
      if (!response.ok) throw new Error(`live panels API returned HTTP ${response.status}`);
      const snapshot = validateSnapshot(await response.json());
      if (requestGeneration !== generation) return null;
      lastRefreshAt = Date.now();
      render(snapshot);
      return snapshot;
    } catch (error) {
      if (error && error.name === 'AbortError') return null;
      if (requestGeneration !== generation) return null;
      console.warn('[LivePanels] fail-closed:', error);
      render(null);
      return null;
    }
  }

  function start(baseInventory) {
    catalogInventory = Array.isArray(baseInventory) ? baseInventory : [];
    render(null);
    refresh({ refresh: true });
    bindManualRefreshControl();
    if (timer) root.clearInterval(timer);
    timer = root.setInterval(() => {
      if (!root.document || root.document.visibilityState === 'visible') {
        refresh({ refresh: true });
      }
    }, POLL_MS);
    if (root.document) {
      root.document.addEventListener('visibilitychange', () => {
        if (root.document.visibilityState === 'visible' && Date.now() - lastRefreshAt >= POLL_MS) {
          refresh({ refresh: true });
        }
      });
    }
  }

  function stop() {
    generation += 1;
    if (activeController) activeController.abort();
    if (timer) root.clearInterval(timer);
    timer = null;
  }

  const api = Object.freeze({
    CONTRACT, LIVE_OWNED_KEYS, CLOSED_RESEARCH_OVERLAY_KEYS,
    OVERLAY_OWNED_KEYS, NO_STATIC_CALCULATION_KEYS,
    validateSnapshot, buildPanelInventory, panelStatusModel, statusHtml,
    latestSourceTimestamp, latestSourceDataDate, latestInventoryDataDate,
    formatIstTimestamp,
    formatCollectorSchedule, getManualRefreshStatus, pollManualRefresh,
    requestManualRefresh, renderCollectorControl, bindManualRefreshControl,
    refreshAfterManualCompletion, render, refresh, start, stop
  });
  root.LivePanelsController = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
