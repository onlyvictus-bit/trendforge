// sector_screener.js — compact NSE sector bull/bear context panel
// Derived from the existing nse_all_indices inventory snapshot. No fetching.
(function () {
  'use strict';

  const SECTOR_INDICES = Object.freeze([
    'NIFTY AUTO', 'NIFTY BANK', 'NIFTY FINANCIAL SERVICES',
    'NIFTY FMCG', 'NIFTY IT', 'NIFTY MEDIA', 'NIFTY METAL',
    'NIFTY PHARMA', 'NIFTY PSU BANK', 'NIFTY PRIVATE BANK',
    'NIFTY REALTY', 'NIFTY HEALTHCARE INDEX', 'NIFTY CONSUMER DURABLES',
    'NIFTY OIL & GAS', 'NIFTY CHEMICALS', 'NIFTY ENERGY',
    'NIFTY INFRASTRUCTURE', 'NIFTY INDIA CONSUMPTION',
    'NIFTY INDIA DIGITAL', 'NIFTY INDIA MANUFACTURING',
    'NIFTY INDIA DEFENCE', 'NIFTY INDIA TOURISM',
    'NIFTY CAPITAL MARKETS', 'NIFTY EV & NEW AGE AUTOMOTIVE',
    'NIFTY INDIA NEW AGE CONSUMPTION', 'NIFTY MOBILITY',
    'NIFTY CORE HOUSING', 'NIFTY HOUSING', 'NIFTY RURAL',
    'NIFTY TRANSPORTATION & LOGISTICS', 'NIFTY INDIA INTERNET',
    'NIFTY COMMODITIES', 'NIFTY CPSE', 'NIFTY PSE',
    'NIFTY SERVICES SECTOR', 'NIFTY MNC', 'NIFTY REITS & REALTY',
    'NIFTY CEMENT'
  ]);

  const ZONES = Object.freeze([
    'STRONG_BULL', 'BULL', 'NEUTRAL', 'BEAR', 'STRONG_BEAR'
  ]);

  const MONTHS = Object.freeze({
    JAN: 0, FEB: 1, MAR: 2, APR: 3, MAY: 4, JUN: 5,
    JUL: 6, AUG: 7, SEP: 8, OCT: 9, NOV: 10, DEC: 11
  });

  function finite(value) {
    if (value == null || String(value).trim() === '') return null;
    const number = Number(String(value).replace(/,/g, ''));
    return Number.isFinite(number) ? number : null;
  }

  function splitKeys(item) {
    return String(item && item.active_source_keys || '')
      .split('|').map(key => key.trim()).filter(Boolean);
  }

  function findAllIndicesSource(inventory) {
    return (Array.isArray(inventory) ? inventory : [])
      .find(item => splitKeys(item).includes('nse_all_indices')) || null;
  }

  function classifyZone(pctChange, benchmarkPct) {
    const pct = finite(pctChange);
    const benchmark = finite(benchmarkPct);
    if (pct == null || benchmark == null) return 'UNKNOWN';
    if (pct > benchmark + 1.5 && pct > 0) return 'STRONG_BULL';
    if (pct > benchmark + 0.5 && pct > 0) return 'BULL';
    if (pct < benchmark - 1.5 || pct < -2) return 'STRONG_BEAR';
    if (pct < benchmark - 0.5 || pct < -1) return 'BEAR';
    return 'NEUTRAL';
  }

  function trendScore(pctChange) {
    const pct = finite(pctChange);
    if (pct == null) return 0;
    return Math.min(10, Math.max(-10, Math.round(pct * 20) / 10));
  }

  function parseDate(value) {
    const text = String(value || '').trim();
    let match = text.match(/(20\d{2})-(\d{2})-(\d{2})/);
    if (match) return `${match[1]}-${match[2]}-${match[3]}`;
    match = text.match(/^(\d{1,2})-([A-Za-z]{3})-(20\d{2})$/);
    if (!match) return null;
    const month = MONTHS[match[2].toUpperCase()];
    if (month == null) return null;
    return `${match[3]}-${String(month + 1).padStart(2, '0')}-${String(match[1]).padStart(2, '0')}`;
  }

  function resolveDataDate(item, niftyRow) {
    const rows = item && item.records_sample || [];
    const direct = parseDate(item && item.data_date);
    if (direct) return direct;
    const rowDate = parseDate(niftyRow && (
      niftyRow.dataDate || niftyRow.date || niftyRow.timestamp || niftyRow.previousDay
    ));
    if (rowDate) return rowDate;
    for (const row of rows) {
      const candidate = parseDate(row.dataDate || row.date || row.timestamp || row.previousDay);
      if (candidate) return candidate;
    }
    return null;
  }

  function resolveFetchedDate(item) {
    return parseDate(item && (item.fetched_at || item.raw_path));
  }

  function ageDays(isoDate, now) {
    if (!isoDate) return null;
    const start = Date.parse(`${isoDate}T00:00:00Z`);
    const today = now instanceof Date ? now : new Date();
    const end = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
    if (!Number.isFinite(start) || !Number.isFinite(end)) return null;
    return Math.max(0, Math.floor((end - start) / 86400000));
  }

  function normalizeSector(row, benchmarkPct) {
    const pctChange = finite(row.percentChange != null ? row.percentChange : row.PCT_CHANGE);
    const close = finite(row.last != null ? row.last : row.CLOSE);
    const change = finite(row.variation != null ? row.variation : row.CHANGE);
    return {
      name: String(row.index || row.INDEX || '').trim(),
      symbol: String(row.indexSymbol || row.index || row.INDEX || '').trim(),
      close,
      change,
      pctChange,
      relativeStrength: pctChange == null ? null : Math.round((pctChange - benchmarkPct) * 100) / 100,
      zone: classifyZone(pctChange, benchmarkPct),
      trendScore: trendScore(pctChange),
      open: finite(row.open),
      high: finite(row.high),
      low: finite(row.low),
      previousClose: finite(row.previousClose),
      yearHigh: finite(row.yearHigh),
      yearLow: finite(row.yearLow),
      pe: finite(row.pe),
      pb: finite(row.pb),
      dividendYield: finite(row.dy != null ? row.dy : row.dividendYield),
      advances: finite(row.advances),
      declines: finite(row.declines),
      unchanged: finite(row.unchanged),
      change30d: finite(row.perChange30d),
      change365d: finite(row.perChange365d)
    };
  }

  function buildSectorSnapshot(inventory, options) {
    const source = findAllIndicesSource(inventory);
    if (!source) return { state: 'UNAVAILABLE', reason: 'nse_all_indices is missing.' };
    const records = Array.isArray(source.records_sample) ? source.records_sample : [];
    const nifty = records.find(row => String(row.index || row.INDEX || '').trim() === 'NIFTY 50');
    const benchmarkPct = nifty && finite(nifty.percentChange != null ? nifty.percentChange : nifty.PCT_CHANGE);
    if (!nifty || benchmarkPct == null) {
      return { state: 'UNAVAILABLE', reason: 'NIFTY 50 benchmark is missing.', source };
    }

    const allowed = new Set(SECTOR_INDICES);
    const sectors = records
      .filter(row => allowed.has(String(row.index || row.INDEX || '').trim()))
      .map(row => normalizeSector(row, benchmarkPct))
      .filter(row => row.name && row.pctChange != null);

    const bullish = sectors.slice().sort((a, b) => b.pctChange - a.pctChange || a.name.localeCompare(b.name));
    const bearish = sectors.slice().sort((a, b) => a.pctChange - b.pctChange || a.name.localeCompare(b.name));
    const zoneCounts = Object.fromEntries(ZONES.map(zone => [zone, 0]));
    sectors.forEach(row => {
      if (Object.prototype.hasOwnProperty.call(zoneCounts, row.zone)) zoneCounts[row.zone] += 1;
    });

    const percentRows = records.map(row => finite(row.percentChange != null ? row.percentChange : row.PCT_CHANGE))
      .filter(value => value != null);
    const dataDate = resolveDataDate(source, nifty);
    const fetchedDate = resolveFetchedDate(source);
    const age = ageDays(dataDate, options && options.now);
    const coverage = sectors.length;
    const state = coverage === SECTOR_INDICES.length ? (age != null && age > 3 ? 'STALE' : 'READY') : 'PARTIAL';

    return {
      state,
      reason: coverage ? null : 'No requested sector indices are present.',
      source,
      sourceRow: source.row_no,
      dataDate,
      fetchedDate,
      ageDays: age,
      coverage,
      requestedCount: SECTOR_INDICES.length,
      benchmark: normalizeSector(nifty, benchmarkPct),
      breadth: {
        up: percentRows.filter(value => value > 0).length,
        down: percentRows.filter(value => value < 0).length,
        unchanged: percentRows.filter(value => value === 0).length
      },
      zoneCounts,
      topBullish: bullish.slice(0, 5),
      topBearish: bearish.slice(0, 5),
      sectors
    };
  }

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  function fmtNumber(value, digits) {
    if (value == null) return '—';
    return Number(value).toLocaleString('en-IN', {
      minimumFractionDigits: digits == null ? 2 : digits,
      maximumFractionDigits: digits == null ? 2 : digits
    });
  }

  function fmtPct(value) {
    if (value == null) return '—';
    return `${value >= 0 ? '+' : ''}${fmtNumber(value, 2)}%`;
  }

  function fmtDate(isoDate) {
    if (!isoDate) return 'Date unavailable';
    const parts = isoDate.split('-');
    const date = new Date(Date.UTC(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2])));
    return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' });
  }

  function zoneLabel(zone) {
    return String(zone || 'UNKNOWN').replace(/_/g, ' ');
  }

  function detailMetric(label, value, className) {
    return `<div class="sector-detail-metric"><span>${esc(label)}</span><strong class="${className || ''}">${esc(value)}</strong></div>`;
  }

  function renderSectorRow(row, rank, side) {
    const directionClass = row.pctChange >= 0 ? 'positive' : 'negative';
    const rsClass = row.relativeStrength >= 0 ? 'positive' : 'negative';
    return `
      <details class="sector-rank-row sector-${side}">
        <summary>
          <span class="sector-rank">${rank}</span>
          <span class="sector-name" title="${esc(row.name)}">${esc(row.name.replace(/^NIFTY\s+/, ''))}</span>
          <span class="sector-rs ${rsClass}" title="Relative strength versus Nifty 50">RS ${fmtPct(row.relativeStrength)}</span>
          <span class="sector-move ${directionClass}">${fmtPct(row.pctChange)}</span>
          <span class="sector-zone zone-${esc(row.zone)}">${esc(zoneLabel(row.zone))}</span>
        </summary>
        <div class="sector-row-details">
          ${detailMetric('Close', fmtNumber(row.close))}
          ${detailMetric('Session change', `${row.change != null && row.change >= 0 ? '+' : ''}${fmtNumber(row.change)}`, directionClass)}
          ${detailMetric('Trend score', fmtNumber(row.trendScore, 1), directionClass)}
          ${detailMetric('Breadth', `${fmtNumber(row.advances, 0)} up / ${fmtNumber(row.declines, 0)} down`)}
          ${detailMetric('Open / High / Low', `${fmtNumber(row.open)} / ${fmtNumber(row.high)} / ${fmtNumber(row.low)}`)}
          ${detailMetric('P/E · P/B · Yield', `${fmtNumber(row.pe)} · ${fmtNumber(row.pb)} · ${fmtNumber(row.dividendYield)}%`)}
          ${detailMetric('30D / 1Y', `${fmtPct(row.change30d)} / ${fmtPct(row.change365d)}`)}
          ${detailMetric('52-week range', `${fmtNumber(row.yearLow)} – ${fmtNumber(row.yearHigh)}`)}
        </div>
      </details>`;
  }

  function renderUnavailable(host, snapshot) {
    host.innerHTML = `
      <section class="sector-pulse sector-pulse-unavailable" aria-label="NSE sector bull and bear screener">
        <div><span class="sector-eyebrow">NSE sector pulse</span><h2>Sector data unavailable</h2></div>
        <p>${esc(snapshot.reason || 'The cached index snapshot is incomplete.')}</p>
      </section>`;
  }

  function renderSectorScreenerPanel(inventory, options) {
    const host = typeof document !== 'undefined' && document.getElementById('sector-screener-panel');
    const snapshot = buildSectorSnapshot(inventory, options);
    if (!host) return snapshot;
    if (snapshot.state === 'UNAVAILABLE') {
      renderUnavailable(host, snapshot);
      return snapshot;
    }

    const benchmark = snapshot.benchmark;
    const stateLabel = snapshot.state === 'STALE'
      ? `STALE ${snapshot.ageDays}D`
      : snapshot.state === 'PARTIAL'
        ? `PARTIAL ${snapshot.coverage}/${snapshot.requestedCount}`
        : 'DAILY SNAPSHOT';
    const stateClass = snapshot.state.toLowerCase();
    const zonePills = ZONES.map(zone => `
      <span class="sector-zone-count zone-${zone}"><strong>${snapshot.zoneCounts[zone]}</strong>${zoneLabel(zone)}</span>`).join('');

    host.innerHTML = `
      <section class="sector-pulse" aria-label="NSE sector bull and bear screener">
        <header class="sector-pulse-header">
          <div>
            <span class="sector-eyebrow">NSE market rotation</span>
            <div class="sector-title-line">
              <h2>Sector Bull / Bear Pulse</h2>
              <span class="sector-state sector-state-${stateClass}">${esc(stateLabel)}</span>
            </div>
            <p>${esc(fmtDate(snapshot.dataDate))} · ${snapshot.coverage}/${snapshot.requestedCount} tracked sectors · cached official snapshot</p>
          </div>
          <button type="button" class="sector-source-button" data-sector-source-row="${esc(snapshot.sourceRow)}" title="Open the nse_all_indices source evidence">Source #${esc(snapshot.sourceRow)}</button>
        </header>

        <div class="sector-market-strip">
          <div class="sector-benchmark">
            <span>NIFTY 50</span>
            <strong>${fmtNumber(benchmark.close)}</strong>
            <em class="${benchmark.pctChange >= 0 ? 'positive' : 'negative'}">${benchmark.change >= 0 ? '+' : ''}${fmtNumber(benchmark.change)} · ${fmtPct(benchmark.pctChange)}</em>
          </div>
          <div class="sector-breadth" aria-label="Index breadth">
            <span><i class="breadth-up"></i>${snapshot.breadth.up} up</span>
            <span><i class="breadth-down"></i>${snapshot.breadth.down} down</span>
            <span>${snapshot.breadth.unchanged} flat</span>
          </div>
          <div class="sector-zone-distribution" aria-label="Sector zone distribution">${zonePills}</div>
        </div>

        <div class="sector-lists">
          <section class="sector-list sector-list-bull" aria-labelledby="sector-bull-title">
            <div class="sector-list-heading"><h3 id="sector-bull-title">Top 5 bullish</h3><span>Strongest first</span></div>
            ${snapshot.topBullish.map((row, index) => renderSectorRow(row, index + 1, 'bull')).join('')}
          </section>
          <section class="sector-list sector-list-bear" aria-labelledby="sector-bear-title">
            <div class="sector-list-heading"><h3 id="sector-bear-title">Top 5 bearish</h3><span>Weakest first</span></div>
            ${snapshot.topBearish.map((row, index) => renderSectorRow(row, index + 1, 'bear')).join('')}
          </section>
        </div>

        <footer class="sector-pulse-note">
          Context only · benchmark-relative daily zones · a positive sector can be BEAR when it underperforms Nifty 50 · freshness shown above
        </footer>
      </section>`;

    const sourceButton = host.querySelector('[data-sector-source-row]');
    if (sourceButton) sourceButton.addEventListener('click', () => {
      if (typeof window.openDrawer === 'function') window.openDrawer(Number(snapshot.sourceRow));
    });
    return snapshot;
  }

  const api = Object.freeze({
    SECTOR_INDICES, ZONES, classifyZone, trendScore, buildSectorSnapshot,
    renderSectorScreenerPanel, parseDate
  });
  if (typeof window !== 'undefined') {
    window.SectorScreenerEngine = api;
    window.renderSectorScreenerPanel = renderSectorScreenerPanel;
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
