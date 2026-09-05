// schemas.js — TrendForge inventory schema registry (count is data-driven)
// Covers every source_key found across the generated inventory rows
// Modes: RANKED | LATEST_5 | POSITIVE_AND_NEGATIVE | NEXT_5 | DIRECTORY | STATUS_ONLY | MIRROR_POINTER

'use strict';

// ASM stage rank: higher = more severe restriction
const ASM_STAGE_RANK = { 'Stage 1': 1, 'Stage 2': 2, 'Stage 3': 3, 'Stage 4': 4, 'Stage I': 1, 'Stage II': 2, 'Stage III': 3, 'Stage IV': 4 };
// GSM stage rank: higher = more severe
const GSM_STAGE_RANK = {
  'Stage I': 1, 'Stage II': 2, 'Stage III': 3,
  'Stage IV': 4, 'Stage V': 5, 'Stage VI': 6,
  'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6
};

// Roman / "Stage N" / bare digit → integer severity (GSM feeds use bare LXII etc.)
function _schemaStageRank(raw) {
  if (raw == null || raw === '') return 0;
  const s = String(raw).trim();
  if (ASM_STAGE_RANK[s] != null) return ASM_STAGE_RANK[s];
  if (GSM_STAGE_RANK[s] != null) return GSM_STAGE_RANK[s];
  const upper = s.toUpperCase();
  if (GSM_STAGE_RANK[upper] != null) return GSM_STAGE_RANK[upper];
  const m = upper.match(/STAGE\s*([IVXLCDM]+|\d+)/);
  const tok = m ? m[1] : upper;
  if (/^\d+$/.test(tok)) return parseInt(tok, 10) || 0;
  if (/^[IVXLCDM]+$/.test(tok)) {
    const R = { I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000 };
    let total = 0;
    for (let i = 0; i < tok.length; i++) {
      const cur = R[tok[i]] || 0, next = R[tok[i + 1]] || 0;
      total += cur < next ? -cur : cur;
    }
    return total > 0 ? total : 0;
  }
  const digits = parseInt(String(s).replace(/[^0-9]/g, ''), 10);
  return isNaN(digits) ? 0 : digits;
}

// OI spurts bucket rows contain sub-arrays keyed by a label like "Slide-in-OI-Slide"
// The real records are inside those arrays
function flattenOISpurts(records) {
  const flat = [];
  for (const row of records) {
    for (const [bucket, arr] of Object.entries(row)) {
      if (Array.isArray(arr)) {
        arr.forEach(r => flat.push({ _bucket: bucket, ...r }));
      }
    }
  }
  return flat;
}

// Pre-open records: each record has metadata + detail; extract top-level values
function flattenPreOpen(records) {
  const toN = v => {
    if (v == null || v === '') return null;
    if (typeof v === 'number') return isNaN(v) ? null : v;
    const n = parseFloat(String(v).replace(/,/g, '').replace(/%/g, '').trim());
    return isNaN(n) ? null : n;
  };
  return records.map(r => {
    const meta = r.metadata || {};
    const detail = r.detail || {};
    const preopen = detail.preOpenMarket || detail.preopen || {};
    const iep = toN(preopen.IEP ?? meta.iep ?? preopen.iep);
    const prevClose = toN(meta.previousClose ?? preopen.previousClose);
    const gap = iep != null && prevClose != null && prevClose > 0
      ? ((iep - prevClose) / prevClose) * 100
      : null;
    return {
      symbol: meta.symbol || '',
      series: meta.series || '',
      iep,
      prevClose,
      gapPercent: gap,
      lastPrice: meta.lastPrice || null,
      totalTradedVolume: preopen.totalTradedVolume || null
    };
  }).filter(r => r.symbol);
}

// Market Turnover: each record has name + today (nested) + yesterday (nested)
function flattenMarketTurnover(records) {
  return records.map(r => ({
    segment: r.name || '',
    todayVolume: (r.today || {}).volume || null,
    todayValue: (r.today || {}).value || null,
    todayOI: (r.today || {}).openInterest || null,
    yestVolume: (r.yesterday || {}).volume || null,
    yestValue: (r.yesterday || {}).value || null,
  })).filter(r => r.segment);
}

// ─────────────────────────────────────────────────────────────────────────────
// SCHEMA REGISTRY — keyed by active_source_keys string
// ─────────────────────────────────────────────────────────────────────────────
window.LINK_SCHEMAS = {

  // ══════════════════════════════════════════════════════
  // GROUP: News / Catalyst
  // ══════════════════════════════════════════════════════
  'bse_corporate_announcements': {
    group: 'News / Catalyst', mode: 'LATEST_5',
    identityField: 'Scrip Code',
    displayColumns: [
      { key: 'Scrip Code',  label: 'Scrip' },
      { key: 'Headline',    label: 'Headline / Subject', wide: true },
      { key: 'Date',        label: 'Filing Date/Time' },
      { key: 'Critical',    label: 'Critical' },
      { key: 'Category',    label: 'Category' }
    ],
    sort: { field: 'Date', dir: 'desc' },
    topN: 5,
    topLabel: 'Latest 5 Announcements'
  },

  'bse_order_win_announcements': {
    group: 'News / Catalyst', mode: 'LATEST_5',
    identityField: 'Scrip Code',
    displayColumns: [
      { key: 'Scrip Code', label: 'Scrip' },
      { key: 'Headline',   label: 'Order Win Headline', wide: true },
      { key: 'Date',       label: 'Filing Date/Time' },
      { key: 'Critical',   label: 'Critical' },
      { key: 'Category',   label: 'Category' }
    ],
    sort: { field: 'Date', dir: 'desc' },
    topN: 5,
    topLabel: 'Latest 5 Order Wins'
  },

  'nse_announcements': {
    group: 'News / Catalyst', mode: 'LATEST_5',
    identityField: 'Description',
    displayColumns: [
      { key: 'Date',        label: 'Filing Date/Time' },
      { key: 'Filing Text', label: 'Filing Subject', wide: true },
      { key: 'Description', label: 'Description', wide: true },
      { key: 'File Size',   label: 'File Size' },
      { key: 'PDF Link',    label: 'PDF', isLink: true }
    ],
    sort: { field: 'Date', dir: 'desc' },
    topN: 5,
    topLabel: 'Latest 5 NSE Filings'
  },

  // ══════════════════════════════════════════════════════
  // GROUP: Deals
  // ══════════════════════════════════════════════════════
  'bse_bulk_deals': {
    group: 'Deals', mode: 'RANKED',
    identityField: 'scripname',
    displayColumns: [
      { key: 'DEAL_DATE',         label: 'Deal Date' },
      { key: 'scripname',         label: 'Company' },
      { key: 'CLIENT_NAME',       label: 'Client' },
      { key: 'TRANSACTION_TYPE',  label: 'BUY / SELL' },
      { key: 'QUANTITY',          label: 'Quantity', numeric: true },
      { key: 'PRICE',             label: 'Price ₹', numeric: true },
      { key: '_dealValue',        label: 'Deal Value ₹ Cr', derived: true, numeric: true }
    ],
    sort: { field: '_dealValue', dir: 'desc' },
    derive: rec => ({
      _dealValue: (parseFloat(rec.QUANTITY || 0) * parseFloat(rec.PRICE || 0)) / 1e7
    }),
    topN: 5,
    topLabel: 'Top 5 by Deal Value ₹ Cr'
  },

  'bse_block_deals': {
    group: 'Deals', mode: 'RANKED',
    identityField: 'scripname',
    displayColumns: [
      { key: 'DEAL_DATE',         label: 'Deal Date' },
      { key: 'scripname',         label: 'Company' },
      { key: 'CLIENT_NAME',       label: 'Client' },
      { key: 'TRANSACTION_TYPE',  label: 'BUY / SELL' },
      { key: 'QUANTITY',          label: 'Quantity', numeric: true },
      { key: 'PRICE',             label: 'Price ₹', numeric: true },
      { key: '_dealValue',        label: 'Deal Value ₹ Cr', derived: true, numeric: true }
    ],
    sort: { field: '_dealValue', dir: 'desc' },
    derive: rec => ({
      _dealValue: (parseFloat(rec.QUANTITY || 0) * parseFloat(rec.PRICE || 0)) / 1e7
    }),
    topN: 5,
    topLabel: 'Top 5 by Deal Value ₹ Cr'
  },

  'nse_large_deals': {
    group: 'Deals', mode: 'RANKED',
    identityField: 'Symbol',
    displayColumns: [
      { key: 'Date',            label: 'Date' },
      { key: 'Symbol',          label: 'Symbol' },
      { key: 'Security Name',   label: 'Company' },
      { key: 'Client Name',     label: 'Client' },
      { key: 'Buy/Sell',        label: 'BUY / SELL' },
      { key: 'Quantity Traded', label: 'Quantity', numeric: true },
      // Real NSE key (not "Trade Price") — wrong key zeroed deal values in UI sort
      { key: 'Trade Price / Wght. Avg. Price', label: 'Price ₹', numeric: true },
      { key: '_dealValue',      label: 'Deal Value ₹ Cr', derived: true, numeric: true }
    ],
    sort: { field: '_dealValue', dir: 'desc' },
    derive: rec => {
      const qty = parseFloat(String(rec['Quantity Traded'] ?? '').replace(/,/g, '')) || 0;
      const px = parseFloat(String(
        rec['Trade Price / Wght. Avg. Price'] ?? rec['Trade Price'] ?? ''
      ).replace(/,/g, '')) || 0;
      return { _dealValue: (qty * px) / 1e7 };
    },
    topN: 5,
    topLabel: 'Top 5 by Deal Value ₹ Cr'
  },

  'nse_large_deals_snapshot': {
    group: 'Deals', mode: 'RANKED',
    identityField: 'symbol',
    displayColumns: [
      { key: 'date',       label: 'Date' },
      { key: 'symbol',     label: 'Symbol' },
      { key: 'dealType',   label: 'Deal Type' },
      { key: 'side',       label: 'BUY / SELL' },
      { key: 'clientName', label: 'Client' },
      { key: 'quantity',   label: 'Quantity', numeric: true },
      { key: 'price',      label: 'Price ₹', numeric: true },
      { key: '_dealValue', label: 'Deal Value ₹ Cr', derived: true, numeric: true }
    ],
    sort: { field: '_dealValue', dir: 'desc' },
    derive: rec => ({
      _dealValue: (parseFloat(rec.quantity || 0) * parseFloat(rec.price || 0)) / 1e7
    }),
    topN: 5,
    topLabel: 'Top 5 by Deal Value ₹ Cr'
  },

  // Live block deal — often VALID_EMPTY; show companion #87 snapshot
  'nse_block_deal': {
    group: 'Deals', mode: 'STATUS_ONLY',
    statusNote: 'NSE Live Block Deal endpoint is VALID_EMPTY during non-session hours.',
    companionKey: 'nse_large_deals_snapshot',
    companionNote: 'Showing NSE Large Deals Snapshot (Block deals filtered)'
  },
  'nse_block_deal_live': {
    group: 'Deals', mode: 'STATUS_ONLY',
    statusNote: 'NSE Live Block Deal endpoint is VALID_EMPTY during non-session hours.',
    companionKey: 'nse_large_deals_snapshot',
    companionNote: 'Showing NSE Large Deals Snapshot (Block deals filtered)'
  },

  // ══════════════════════════════════════════════════════
  // GROUP: Ownership & Insider Activity
  // ══════════════════════════════════════════════════════
  'bse_sast': {
    group: 'Ownership & Insider', mode: 'RANKED',
    identityField: 'Company_Name',
    displayColumns: [
      { key: 'Company_Name',          label: 'Company' },
      { key: 'Acq_Sale',              label: 'Acquisition / Sale' },
      { key: 'Acq_sale_qty',          label: 'Quantity Changed', numeric: true },
      { key: 'Acquisition_Pct_After', label: 'Holding After %', numeric: true },
      { key: 'flag',                  label: 'Regulation Flag' }
    ],
    sort: { field: 'Acq_sale_qty', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 by Quantity Changed (price field absent in feed)'
  },

  'bse_pledge_data': {
    group: 'Ownership & Insider', mode: 'RANKED',
    identityField: 'company',
    displayColumns: [
      { key: 'company',                           label: 'Company' },
      { key: 'promoterHoldingPercent',            label: 'Promoter Holding %', numeric: true },
      { key: 'pledgedShares',                     label: 'Pledged Shares', numeric: true },
      { key: 'promoterEncumberedPercentOfTotal',  label: 'Encumbered %', numeric: true }
    ],
    sort: { field: 'promoterEncumberedPercentOfTotal', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 by Encumbered % (Highest promoter pledge risk)'
  },

  'nse_pledge_data': {
    group: 'Ownership & Insider', mode: 'RANKED',
    identityField: 'comName',
    displayColumns: [
      { key: 'comName',              label: 'Company' },
      { key: 'broadcastDt',          label: 'Broadcast Date' },
      { key: 'totPromoterShares',    label: 'Promoter Shares', numeric: true },
      { key: 'numSharesPledged',     label: 'Shares Pledged', numeric: true },
      { key: 'percSharesPledged',    label: 'Pledged %', numeric: true },
      { key: 'percPromoterHolding',  label: 'Promoter Holding %', numeric: true }
    ],
    sort: { field: 'percSharesPledged', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 by Pledged % (Highest encumbrance)'
  },

  'nse_shareholding_pattern': {
    group: 'Ownership & Insider', mode: 'LATEST_5',
    identityField: 'name',
    displayColumns: [
      { key: 'name',           label: 'Company' },
      { key: 'symbol',         label: 'Symbol' },
      { key: 'broadcastDate',  label: 'Broadcast Date' },
      { key: 'pr_and_prgrp',  label: 'Promoter Group %', numeric: true },
      { key: 'public_val',     label: 'Public Holding %', numeric: true },
      { key: 'industry',       label: 'Industry' }
    ],
    sort: { field: 'broadcastDate', dir: 'desc' },
    topN: 5,
    topLabel: 'Latest 5 Shareholding Filings (not a buy/sell board)'
  },

  // Reg 29 — usually empty; companion = BSE SAST
  'nse_regulation_29': {
    group: 'Ownership & Insider', mode: 'STATUS_ONLY',
    statusNote: 'NSE Regulation 29 SAST endpoint is typically empty.',
    companionKey: 'bse_sast',
    companionNote: 'Showing BSE SAST companion data'
  },

  // Reg 31 — usually empty; companion = BSE Pledge
  'nse_regulation_31': {
    group: 'Ownership & Insider', mode: 'STATUS_ONLY',
    statusNote: 'NSE Regulation 31 Pledge endpoint is typically empty.',
    companionKey: 'bse_pledge_data',
    companionNote: 'Showing BSE Pledge companion data'
  },

  'nse_pit_symbol': {
    group: 'Ownership & Insider', mode: 'POSITIVE_AND_NEGATIVE',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol',          label: 'Symbol' },
      { key: 'entity',          label: 'Insider / Entity' },
      { key: 'transactionType', label: 'Transaction Type' },
      { key: 'quantity',        label: 'Quantity', numeric: true },
      { key: 'value',           label: 'Value ₹ Cr', numeric: true },
      { key: 'eventDate',       label: 'Event Date' }
    ],
    posFilter: r => String(r.transactionType || '').toUpperCase().includes('BUY'),
    negFilter: r => String(r.transactionType || '').toUpperCase().includes('SELL'),
    sort: { field: 'value', dir: 'desc' },
    topN: 5,
    posLabel: 'Top Insider BUY by Value',
    negLabel: 'Top Insider SELL by Value'
  },
  'nse_pit_current': {
    group: 'Ownership & Insider', mode: 'POSITIVE_AND_NEGATIVE',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol', label: 'Symbol' }, { key: 'entity', label: 'Insider / Entity' },
      { key: 'transactionType', label: 'Transaction Type' },
      { key: 'quantity', label: 'Quantity', numeric: true },
      { key: 'value', label: 'Value ₹ Cr', numeric: true },
      { key: 'eventDate', label: 'Event Date' }
    ],
    posFilter: r => String(r.transactionType || '').toUpperCase().includes('BUY'),
    negFilter: r => String(r.transactionType || '').toUpperCase().includes('SELL'),
    sort: { field: 'value', dir: 'desc' },
    topN: 5,
    posLabel: 'Top Insider BUY by Value',
    negLabel: 'Top Insider SELL by Value'
  },

  // ══════════════════════════════════════════════════════
  // GROUP: Commodity / Global
  // ══════════════════════════════════════════════════════
  'sge_benchmark_gold': {
    group: 'Commodity / Global', mode: 'LATEST_5',
    identityField: 'series',
    displayColumns: [
      { key: 'date',            label: 'Observation Date' },
      { key: 'benchmark_value', label: 'Gold Benchmark (RMB/g)', numeric: true },
      { key: 'currency',        label: 'Currency' },
      { key: 'series',          label: 'Series' },
      { key: 'source',          label: 'Source' }
    ],
    sort: { field: 'date', dir: 'desc' },
    topN: 5,
    topLabel: 'Latest 5 SGE Gold Fixings'
  },

  'wgc_gold_etf_holdings': {
    group: 'Commodity / Global', mode: 'LATEST_5',
    identityField: 'region',
    displayColumns: [
      { key: 'observationDate', label: 'Observation Date' },
      { key: 'region',          label: 'Region / Fund' },
      { key: 'value',           label: 'Holdings (Tonnes)', numeric: true },
      { key: 'dataset',         label: 'Dataset' },
      { key: 'period',          label: 'Period' }
    ],
    sort: { field: 'observationDate', dir: 'desc' },
    topN: 5,
    topLabel: 'Latest 5 WGC Gold ETF Holdings Readings'
  },

  'world_gold_council_oi': {
    group: 'Commodity / Global', mode: 'LATEST_5',
    identityField: 'venue',
    displayColumns: [
      { key: 'observationDate',    label: 'Observation Date' },
      { key: 'venue',              label: 'Exchange Venue' },
      { key: 'openInterestUsdBn',  label: 'Open Interest ($ Bn)', numeric: true },
      { key: 'units',              label: 'Units' },
      { key: 'frequency',          label: 'Frequency' }
    ],
    sort: { field: 'observationDate', dir: 'desc' },
    topN: 5,
    topLabel: 'Latest 5 WGC Gold Futures OI Readings'
  },

  'eia_weekly_petroleum_stocks': {
    group: 'Commodity / Global', mode: 'RANKED',
    identityField: 'Category',
    displayColumns: [
      { key: 'Category',        label: 'Product Category' },
      { key: 'Difference',      label: 'Weekly Change', numeric: true },
      { key: 'Percent Change',  label: 'Change %', numeric: true }
    ],
    sort: { field: '_absChange', dir: 'desc' },
    derive: rec => ({
      _absChange: Math.abs(parseFloat(String(rec['Percent Change'] || '0').replace('%', '')) || 0)
    }),
    topN: 5,
    topLabel: 'Top 5 by Absolute Weekly Inventory Change %'
  },

  'cftc_legacy_futures_only': {
    group: 'Commodity / Global', mode: 'RANKED',
    identityField: 'Contract',
    displayColumns: [
      { key: 'Market & Exchange',    label: 'Market & Exchange' },
      { key: 'Contract',             label: 'Contract' },
      { key: 'Report Date',          label: 'Report Date' },
      { key: 'Open Interest (All)',   label: 'Open Interest (All)', numeric: true }
    ],
    sort: { field: 'Open Interest (All)', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 by Total Open Interest (CFTC Legacy)'
  },

  'cftc_disagg_futures_only': {
    group: 'Commodity / Global', mode: 'RANKED',
    identityField: 'Contract',
    displayColumns: [
      { key: 'Market & Exchange',  label: 'Market & Exchange' },
      { key: 'Contract',           label: 'Contract' },
      { key: 'Report Date',        label: 'Report Date' },
      { key: 'Open Interest (All)', label: 'Open Interest (All)', numeric: true }
    ],
    sort: { field: 'Open Interest (All)', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 by Total Open Interest (CFTC Disaggregated)'
  },

  'cftc_tff_futures_only': {
    group: 'Commodity / Global', mode: 'RANKED',
    identityField: 'Contract',
    displayColumns: [
      { key: 'Market & Exchange',  label: 'Market & Exchange' },
      { key: 'Contract',           label: 'Contract' },
      { key: 'Report Date',        label: 'Report Date' },
      { key: 'Open Interest (All)', label: 'Open Interest (All)', numeric: true }
    ],
    sort: { field: 'Open Interest (All)', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 by Total Open Interest (CFTC TFF)'
  },

  // CFTC Annual — stored as binary ZIP; usually no parsed rows
  'cftc_cot': {
    group: 'Commodity / Global', mode: 'STATUS_ONLY',
    statusNote: 'CFTC Annual COT file is a binary ZIP archive. Rows shown if successfully parsed.'
  },

  // MCX — currently returning HTML error page from exchange
  'mcx_bhavcopy': {
    group: 'Commodity / Global', mode: 'STATUS_ONLY',
    statusNote: 'MCX Bhavcopy endpoint is returning an HTML error page (exchange-side block).'
  },

  // ══════════════════════════════════════════════════════
  // GROUP: Institutional & Macro
  // ══════════════════════════════════════════════════════
  'nsdl_fpi_daily': {
    group: 'Institutional Flow', mode: 'POSITIVE_AND_NEGATIVE',
    identityField: 'category',
    displayColumns: [
      { key: 'reportingDate',       label: 'Date' },
      { key: 'category',            label: 'Category' },
      { key: 'grossPurchasesCrore', label: 'Gross Buy ₹ Cr', numeric: true },
      { key: 'grossSalesCrore',     label: 'Gross Sell ₹ Cr', numeric: true },
      { key: 'netInvestmentCrore',  label: 'Net Flow ₹ Cr', numeric: true }
    ],
    posFilter: r => parseFloat(r.netInvestmentCrore || 0) > 0,
    negFilter: r => parseFloat(r.netInvestmentCrore || 0) < 0,
    sort: { field: 'netInvestmentCrore', dir: 'desc' },
    topN: 5,
    posLabel: 'Top Net Buying Days',
    negLabel: 'Top Net Selling Days'
  },

  'amfi_scheme_wise': {
    group: 'Institutional Flow', mode: 'STATUS_ONLY',
    statusNote: 'AMFI Scheme-Wise data is metadata-only in the current snapshot (no parsed scheme rows).'
  },

  'nsdl_fpi_fortnightly': {
    group: 'Institutional Flow', mode: 'STATUS_ONLY',
    statusNote: 'NSDL Fortnightly FPI AUC endpoint is WAF-blocked.',
    companionKey: 'nsdl_fpi_daily_reportdetail',
    companionNote: 'Showing NSDL FPI AUC Category breakdown as companion'
  },

  'nsdl_fpi_daily_reportdetail': {
    group: 'Institutional Flow', mode: 'RANKED',
    identityField: 'category',
    displayColumns: [
      { key: 'category',       label: 'FPI Category' },
      { key: 'subCategory',    label: 'Sub-Category' },
      { key: 'equityAucCrore', label: 'Equity AUC ₹ Cr', numeric: true },
      { key: 'debtAucCrore',   label: 'Debt AUC ₹ Cr', numeric: true },
      { key: 'totalAucCrore',  label: 'Total AUC ₹ Cr', numeric: true }
    ],
    sort: { field: 'totalAucCrore', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 FPI Categories by Total AUC'
  },

  'nse_fii_dii': {
    group: 'Institutional Flow', mode: 'POSITIVE_AND_NEGATIVE',
    identityField: 'Category',
    displayColumns: [
      { key: 'Date',      label: 'Date' },
      { key: 'Category',  label: 'Category (FII/DII)' },
      { key: 'Buy ₹ Cr',  label: 'Buy ₹ Cr', numeric: true },
      { key: 'Sell ₹ Cr', label: 'Sell ₹ Cr', numeric: true },
      { key: 'Net ₹ Cr',  label: 'Net ₹ Cr', numeric: true }
    ],
    posFilter: r => parseFloat(String(r['Net ₹ Cr'] || '0').replace(/,/g, '')) > 0,
    negFilter: r => parseFloat(String(r['Net ₹ Cr'] || '0').replace(/,/g, '')) < 0,
    sort: { field: 'Net ₹ Cr', dir: 'desc' },
    topN: 5,
    posLabel: 'FII / DII Net Buying',
    negLabel: 'FII / DII Net Selling',
    note: 'Feed typically has 2 rows per day (FII + DII). Multi-day history shown when available.'
  },

  'fred_real_yield_10y': {
    group: 'Macro', mode: 'LATEST_5',
    identityField: 'Real Yield 10Y (%)',
    displayColumns: [
      { key: 'Date',               label: 'Observation Date' },
      { key: 'Real Yield 10Y (%)', label: 'Real Yield 10Y (%)', numeric: true }
    ],
    sort: { field: 'Date', dir: 'desc' },
    topN: 5,
    topLabel: 'Latest 5 FRED 10Y Real Yield Observations (no stock table)'
  },

  'fred_broad_dollar_index': {
    group: 'Macro', mode: 'LATEST_5',
    identityField: 'USD Index',
    displayColumns: [
      { key: 'Date',      label: 'Observation Date' },
      { key: 'USD Index', label: 'USD Dollar Index Level', numeric: true }
    ],
    sort: { field: 'Date', dir: 'desc' },
    topN: 5,
    topLabel: 'Latest 5 FRED USD Dollar Index Observations (no stock table)'
  },

  // ══════════════════════════════════════════════════════
  // GROUP: Derivatives & Options
  // ══════════════════════════════════════════════════════
  'nse_slb': {
    group: 'Derivatives & Options', mode: 'RANKED',
    identityField: 'Symbol',
    displayColumns: [
      { key: 'Symbol',         label: 'Symbol' },
      { key: 'Series',         label: 'Series' },
      { key: 'Open Positions', label: 'Open Positions', numeric: true }
    ],
    sort: { field: 'Open Positions', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 by Open Positions (Highest Short/Borrow Interest)'
  },

  'nse_fo_bhavcopy': {
    group: 'Derivatives & Options', mode: 'RANKED',
    identityField: 'Symbol',
    displayColumns: [
      { key: 'Symbol',         label: 'Symbol' },
      { key: 'XpryDt',         label: 'Expiry Date' },
      { key: 'OptnTp',         label: 'CE / PE' },
      { key: 'StrkPric',       label: 'Strike ₹', numeric: true },
      { key: 'Close ₹',        label: 'Close ₹', numeric: true },
      { key: 'Volume',         label: 'Volume', numeric: true },
      { key: 'OpnIntrst',      label: 'Open Interest', numeric: true }
    ],
    rowFilter: r => parseFloat(r.Volume || 0) > 0,
    sort: { field: 'OpnIntrst', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 by Open Interest (non-zero volume contracts)'
  },
  'nse_participant_oi': {
    group: 'Derivatives & Options', mode: 'RANKED',
    identityField: 'Symbol',
    displayColumns: [
      { key: 'Symbol', label: 'Symbol' }, { key: 'XpryDt', label: 'Expiry Date' },
      { key: 'OptnTp', label: 'CE / PE' }, { key: 'StrkPric', label: 'Strike ₹', numeric: true },
      { key: 'Close ₹', label: 'Close ₹', numeric: true },
      { key: 'Volume', label: 'Volume', numeric: true }, { key: 'OpnIntrst', label: 'Open Interest', numeric: true }
    ],
    rowFilter: r => parseFloat(r.Volume || 0) > 0,
    sort: { field: 'OpnIntrst', dir: 'desc' },
    topN: 5, topLabel: 'Top 5 by Open Interest'
  },

  'nse_oi_spurts_contracts': {
    group: 'Derivatives & Options', mode: 'RANKED',
    identityField: 'symbol',
    preprocess: flattenOISpurts,
    displayColumns: [
      { key: '_bucket',         label: 'Signal' },
      { key: 'symbol',          label: 'Symbol' },
      { key: 'expiryDate',      label: 'Expiry Date' },
      { key: 'optionType',      label: 'CE / PE' },
      { key: 'strikePrice',     label: 'Strike ₹', numeric: true },
      { key: 'ltp',             label: 'LTP ₹', numeric: true },
      { key: 'changeInOI',      label: 'OI Change', numeric: true },
      { key: 'prevOI',          label: 'Prev OI', numeric: true },
      { key: 'latestOI',        label: 'Latest OI', numeric: true }
    ],
    sort: { field: 'changeInOI', dir: 'desc', abs: true },
    topN: 5,
    topLabel: 'Top 5 OI Spurt Contracts (by Absolute OI Change)'
  },

  'nse_oi_spurts': {
    group: 'Derivatives & Options', mode: 'RANKED',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol',      label: 'Symbol' },
      { key: 'latestOI',    label: 'Latest OI', numeric: true },
      { key: 'prevOI',      label: 'Prev OI', numeric: true },
      { key: 'changeInOI',  label: 'OI Change', numeric: true },
      { key: 'volume',      label: 'Volume', numeric: true }
    ],
    sort: { field: 'changeInOI', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 Underlying OI Spurts (Highest OI Change)'
  },

  // F&O Live Derivatives — shared field structure
  'nse_live_equity_derivatives_banknifty_fut': {
    group: 'Derivatives & Options', mode: 'RANKED',
    identityField: 'underlying',
    displayColumns: [
      { key: 'underlying',   label: 'Underlying' },
      { key: 'contract',     label: 'Contract' },
      { key: 'expiryDate',   label: 'Expiry' },
      { key: 'lastPrice',    label: 'LTP ₹', numeric: true },
      { key: 'change',       label: 'Change', numeric: true },
      { key: 'pChange',      label: '% Change', numeric: true },
      { key: 'volume',       label: 'Volume', numeric: true },
      { key: 'openInterest', label: 'Open Interest', numeric: true }
    ],
    sort: { field: 'openInterest', dir: 'desc' },
    topN: 3,
    topLabel: 'BankNifty Futures by Open Interest (few contracts expected)'
  },

  'nse_live_equity_derivatives_banknifty_opt': {
    group: 'Derivatives & Options', mode: 'RANKED',
    identityField: 'underlying',
    displayColumns: [
      { key: 'strikePrice',  label: 'Strike ₹', numeric: true },
      { key: 'optionType',   label: 'CE / PE' },
      { key: 'expiryDate',   label: 'Expiry' },
      { key: 'lastPrice',    label: 'LTP ₹', numeric: true },
      { key: 'volume',       label: 'Volume', numeric: true },
      { key: 'openInterest', label: 'Open Interest', numeric: true }
    ],
    sort: { field: 'openInterest', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 BankNifty Options by OI (Call & Put strike walls)'
  },

  'nse_live_equity_derivatives_index_fut': {
    group: 'Derivatives & Options', mode: 'RANKED',
    identityField: 'underlying',
    displayColumns: [
      { key: 'underlying',   label: 'Underlying' },
      { key: 'contract',     label: 'Contract' },
      { key: 'expiryDate',   label: 'Expiry' },
      { key: 'lastPrice',    label: 'LTP ₹', numeric: true },
      { key: 'pChange',      label: '% Change', numeric: true },
      { key: 'volume',       label: 'Volume', numeric: true },
      { key: 'openInterest', label: 'Open Interest', numeric: true }
    ],
    sort: { field: 'openInterest', dir: 'desc' },
    topN: 3,
    topLabel: 'Nifty50 Futures by Open Interest'
  },

  'nse_live_equity_derivatives_index_opt': {
    group: 'Derivatives & Options', mode: 'RANKED',
    identityField: 'underlying',
    displayColumns: [
      { key: 'strikePrice',  label: 'Strike ₹', numeric: true },
      { key: 'optionType',   label: 'CE / PE' },
      { key: 'expiryDate',   label: 'Expiry' },
      { key: 'lastPrice',    label: 'LTP ₹', numeric: true },
      { key: 'volume',       label: 'Volume', numeric: true },
      { key: 'openInterest', label: 'Open Interest', numeric: true }
    ],
    sort: { field: 'openInterest', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 Nifty50 Options by OI (Call & Put strike walls)'
  },

  'nse_live_equity_derivatives_stock_fut': {
    group: 'Derivatives & Options', mode: 'RANKED',
    identityField: 'underlying',
    displayColumns: [
      { key: 'underlying',   label: 'Symbol' },
      { key: 'expiryDate',   label: 'Expiry' },
      { key: 'lastPrice',    label: 'LTP ₹', numeric: true },
      { key: 'pChange',      label: '% Change', numeric: true },
      { key: 'volume',       label: 'Volume', numeric: true },
      { key: 'openInterest', label: 'Open Interest', numeric: true }
    ],
    sort: { field: 'openInterest', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 Stock Futures by Open Interest'
  },

  'nse_live_equity_derivatives_stock_opt': {
    group: 'Derivatives & Options', mode: 'RANKED',
    identityField: 'underlying',
    displayColumns: [
      { key: 'underlying',   label: 'Symbol' },
      { key: 'strikePrice',  label: 'Strike ₹', numeric: true },
      { key: 'optionType',   label: 'CE / PE' },
      { key: 'openInterest', label: 'Open Interest', numeric: true },
      { key: 'volume',       label: 'Volume', numeric: true }
    ],
    sort: { field: 'openInterest', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 Stock Options by Open Interest'
  },

  'nse_live_equity_derivatives': {
    group: 'Derivatives & Options', mode: 'RANKED',
    identityField: 'underlying',
    displayColumns: [
      { key: 'underlying',   label: 'Underlying' },
      { key: 'instrument',   label: 'Instrument' },
      { key: 'expiryDate',   label: 'Expiry' },
      { key: 'strikePrice',  label: 'Strike ₹', numeric: true },
      { key: 'optionType',   label: 'CE / PE' },
      { key: 'lastPrice',    label: 'LTP ₹', numeric: true },
      { key: 'openInterest', label: 'Open Interest', numeric: true }
    ],
    sort: { field: 'openInterest', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 by Open Interest'
  },

  // Pre-Open F&O — requires nested flattening
  'nse_preopen_fo': {
    group: 'Derivatives & Options', mode: 'POSITIVE_AND_NEGATIVE',
    identityField: 'symbol',
    preprocess: flattenPreOpen,
    displayColumns: [
      { key: 'symbol',              label: 'Symbol' },
      { key: 'series',              label: 'Series' },
      { key: 'iep',                 label: 'Pre-Open Price ₹ (IEP)', numeric: true },
      { key: 'prevClose',           label: 'Prev Close ₹', numeric: true },
      { key: 'gapPercent',          label: 'Gap %', numeric: true, derived: true },
      { key: 'totalTradedVolume',   label: 'Matched Qty', numeric: true }
    ],
    posFilter: r => r.gapPercent != null && r.gapPercent > 0,
    negFilter: r => r.gapPercent != null && r.gapPercent < 0,
    sort: { field: 'gapPercent', dir: 'desc' },
    topN: 5,
    posLabel: 'Top Gap-Up Stocks (Pre-Open F&O)',
    negLabel: 'Top Gap-Down Stocks (Pre-Open F&O)',
    note: 'Gap % = (IEP − Prev Close) / Prev Close × 100. Separate from Day Gainers #73.'
  },

  // Option Chain — soft empty; companion = stock options live
  'nse_option_chain_equity': {
    group: 'Derivatives & Options', mode: 'STATUS_ONLY',
    statusNote: 'NSE Option Chain endpoint is typically soft-empty ({}). No fake CE/PE matrix generated.',
    companionKey: 'nse_live_equity_derivatives_stock_opt',
    companionNote: 'Showing Stock Options Live data as companion'
  },
  'nse_option_chain': {
    group: 'Derivatives & Options', mode: 'STATUS_ONLY',
    statusNote: 'NSE Option Chain endpoint is typically soft-empty ({}). No fake CE/PE matrix generated.',
    companionKey: 'nse_live_equity_derivatives_stock_opt',
    companionNote: 'Showing Stock Options Live data as companion'
  },

  // ══════════════════════════════════════════════════════
  // GROUP: Price & Universe
  // ══════════════════════════════════════════════════════
  'nse_bhavcopy_eod': {
    group: 'Price & Universe', mode: 'RANKED',
    identityField: 'Symbol',
    displayColumns: [
      { key: 'Symbol',       label: 'Symbol' },
      { key: 'Series',       label: 'Series' },
      { key: 'Open ₹',       label: 'Open ₹', numeric: true },
      { key: 'High ₹',       label: 'High ₹', numeric: true },
      { key: 'Low ₹',        label: 'Low ₹', numeric: true },
      { key: 'Close ₹',      label: 'Close ₹', numeric: true },
      { key: 'Volume',       label: 'Volume', numeric: true },
      { key: 'Traded Value', label: 'Traded Value ₹', numeric: true }
    ],
    sort: { field: 'Traded Value', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 by Traded Value (Most Liquid)'
  },

  'bse_bhavcopy_eod': {
    group: 'Price & Universe', mode: 'RANKED',
    identityField: 'Symbol',
    displayColumns: [
      { key: 'Symbol',       label: 'Symbol' },
      { key: 'Series',       label: 'Series' },
      { key: 'Open ₹',       label: 'Open ₹', numeric: true },
      { key: 'High ₹',       label: 'High ₹', numeric: true },
      { key: 'Low ₹',        label: 'Low ₹', numeric: true },
      { key: 'Close ₹',      label: 'Close ₹', numeric: true },
      { key: 'Volume',       label: 'Volume', numeric: true },
      { key: 'Traded Value', label: 'Traded Value ₹', numeric: true }
    ],
    sort: { field: 'Traded Value', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 by Traded Value (Most Liquid)'
  },

  'nse_equity_universe': {
    group: 'Price & Universe', mode: 'DIRECTORY',
    identityField: 'Symbol',
    displayColumns: [
      { key: 'Symbol',            label: 'Symbol' },
      { key: 'Company',           label: 'Company Name' },
      { key: ' SERIES',           label: 'Series' },
      { key: ' DATE OF LISTING',  label: 'Listing Date' },
      { key: ' PAID UP VALUE',    label: 'Paid-Up Value ₹', numeric: true }
    ],
    sort: { field: ' DATE OF LISTING', dir: 'desc' },
    topN: 5,
    topLabel: 'Latest 5 Listed Companies (Directory view, not movers)'
  },

  // ══════════════════════════════════════════════════════
  // GROUP: Calendar, Indices & Movers
  // ══════════════════════════════════════════════════════
  'nse_all_indices': {
    group: 'Calendar / Regime', mode: 'POSITIVE_AND_NEGATIVE',
    identityField: 'index',
    displayColumns: [
      { key: 'index',          label: 'Index Name' },
      { key: 'indexSymbol',    label: 'Symbol' },
      { key: 'last',           label: 'Last Value', numeric: true },
      { key: 'percentChange',  label: '% Change', numeric: true },
      { key: 'open',           label: 'Open', numeric: true },
      { key: 'high',           label: 'High', numeric: true },
      { key: 'low',            label: 'Low', numeric: true }
    ],
    posFilter: r => parseFloat(r.percentChange || 0) > 0,
    negFilter: r => parseFloat(r.percentChange || 0) < 0,
    sort: { field: 'percentChange', dir: 'desc' },
    topN: 5,
    posLabel: 'Top Gaining Indices',
    negLabel: 'Top Declining Indices',
    note: 'Advances/Declines dropped — not present in index-level payload.'
  },

  'nse_nifty500_constituents': {
    group: 'Calendar / Regime', mode: 'DIRECTORY',
    identityField: 'Symbol',
    displayColumns: [
      { key: 'Company Name', label: 'Company Name' },
      { key: 'Symbol',       label: 'Symbol' },
      { key: 'Industry',     label: 'Industry' },
      { key: 'Series',       label: 'Series' }
    ],
    sort: { field: 'Industry', dir: 'asc' },
    topN: null,
    topLabel: 'Nifty500 Constituents — grouped by Industry (no artificial ranking)'
  },

  'nse_corporate_filings_actions': {
    group: 'Calendar / Regime', mode: 'NEXT_5',
    identityField: 'Symbol',
    displayColumns: [
      { key: 'Symbol',            label: 'Symbol' },
      { key: 'Company',           label: 'Company' },
      { key: 'subject',           label: 'Action Type' },
      { key: 'Ex-Date',           label: 'Ex-Date' },
      { key: 'Record Date',       label: 'Record Date' },
      { key: 'Book Closure Start',label: 'Book Closure Start' },
      { key: 'Face Value ₹',      label: 'Face Value ₹', numeric: true }
    ],
    sort: { field: 'Ex-Date', dir: 'asc' },
    topN: 5,
    topLabel: 'Next 5 Upcoming Ex-Dates'
  },

  // Buyback — usually empty; companion = BSE buyback if present
  'nse_daily_buyback': {
    group: 'Calendar / Regime', mode: 'STATUS_ONLY',
    statusNote: 'NSE Daily Buyback endpoint is typically empty. No execution columns invented.',
    displayColumns: [
      { key: 'Company',      label: 'Company' },
      { key: 'Status',       label: 'Buyback Status' },
      { key: 'Last Updated', label: 'Last Updated' }
    ],
    sort: { field: 'Last Updated', dir: 'desc' },
    topN: 5,
    topLabel: 'Latest Buyback Status Updates (if rows present)'
  },

  'nse_financial_results': {
    group: 'Calendar / Regime', mode: 'LATEST_5',
    identityField: 'Company',
    displayColumns: [
      { key: 'Company',        label: 'Company' },
      { key: 'Type',           label: 'Result Type' },
      { key: 'Audit',          label: 'Audit Status' },
      { key: 'Financial Year', label: 'Financial Year' },
      { key: 'Period',         label: 'Period' },
      { key: 'Broadcast Date', label: 'Filed On' }
    ],
    sort: { field: 'Broadcast Date', dir: 'desc' },
    topN: 5,
    topLabel: 'Latest 5 Quarterly Results Filed'
  },

  'nse_sector_constituents': {
    group: 'Calendar / Regime', mode: 'RANKED',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol',           label: 'Symbol' },
      { key: 'lastPrice',        label: 'LTP ₹', numeric: true },
      { key: 'previousClose',    label: 'Prev Close ₹', numeric: true },
      { key: 'pChange',          label: 'Day Change %', numeric: true },
      { key: 'perChange30d',     label: '30D Change %', numeric: true },
      { key: 'perChange365d',    label: '1Y Change %', numeric: true },
      { key: 'totalTradedValue', label: 'Traded Value', numeric: true }
    ],
    sort: { field: 'pChange', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 Sector Stocks by Day Change %'
  },

  'nse_trading_calendar': {
    group: 'Calendar / Regime', mode: 'NEXT_5',
    identityField: 'tradingDate',
    displayColumns: [
      { key: 'tradingDate',  label: 'Holiday Date' },
      { key: 'weekDay',      label: 'Weekday' },
      { key: 'segment',      label: 'Segment' },
      { key: 'description',  label: 'Holiday Description' }
    ],
    sort: { field: 'tradingDate', dir: 'asc' },
    topN: 5,
    topLabel: 'Next 5 Upcoming Market Holidays'
  },

  'nse_most_active_value': {
    group: 'Calendar / Regime', mode: 'RANKED',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol',            label: 'Symbol' },
      { key: 'lastPrice',         label: 'LTP ₹', numeric: true },
      { key: 'pChange',           label: '% Change', numeric: true },
      { key: 'quantityTraded',    label: 'Volume', numeric: true },
      { key: 'totalTradedValue',  label: 'Traded Value ₹', numeric: true }
    ],
    sort: { field: 'totalTradedValue', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 Most Active by Traded Value'
  },

  'nse_most_active_volume': {
    group: 'Calendar / Regime', mode: 'RANKED',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol',            label: 'Symbol' },
      { key: 'lastPrice',         label: 'LTP ₹', numeric: true },
      { key: 'pChange',           label: '% Change', numeric: true },
      { key: 'quantityTraded',    label: 'Volume', numeric: true },
      { key: 'totalTradedValue',  label: 'Traded Value ₹', numeric: true }
    ],
    sort: { field: 'quantityTraded', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 Most Active by Volume'
  },

  'nse_most_active_underlying': {
    group: 'Calendar / Regime', mode: 'RANKED',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol',       label: 'Underlying Symbol' },
      { key: 'futVolume',    label: 'Futures Volume', numeric: true },
      { key: 'optVolume',    label: 'Options Volume', numeric: true },
      { key: 'totVolume',    label: 'Total Volume', numeric: true },
      { key: 'futTurnover',  label: 'Futures Turnover', numeric: true },
      { key: 'totTurnover',  label: 'Total Turnover', numeric: true }
    ],
    sort: { field: 'totTurnover', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 Most Active F&O Underlyings by Total Turnover'
  },

  'nse_variations_gainers': {
    group: 'Calendar / Regime', mode: 'RANKED',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol',         label: 'Symbol' },
      { key: 'ltp',            label: 'LTP ₹', numeric: true },
      { key: 'prev_price',     label: 'Prev Close ₹', numeric: true },
      { key: 'net_price',      label: 'Net Change', numeric: true },
      { key: '_pChange',       label: 'Day Change %', derived: true, numeric: true },
      { key: 'trade_quantity', label: 'Volume', numeric: true }
    ],
    sort: { field: '_pChange', dir: 'desc' },
    derive: rec => ({
      _pChange: rec.prev_price > 0 ? ((rec.ltp - rec.prev_price) / rec.prev_price) * 100 : 0
    }),
    topN: 5,
    topLabel: 'Top 5 Day Gainers by % Change'
  },
  'nse_market_variations': {
    group: 'Calendar / Regime', mode: 'RANKED',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol', label: 'Symbol' }, { key: 'ltp', label: 'LTP ₹', numeric: true },
      { key: 'prev_price', label: 'Prev Close ₹', numeric: true },
      { key: 'net_price', label: 'Net Change', numeric: true },
      { key: '_pChange', label: 'Day Change %', derived: true, numeric: true },
      { key: 'trade_quantity', label: 'Volume', numeric: true }
    ],
    sort: { field: '_pChange', dir: 'desc' },
    derive: rec => ({ _pChange: rec.prev_price > 0 ? ((rec.ltp - rec.prev_price) / rec.prev_price) * 100 : 0 }),
    topN: 5, topLabel: 'Top 5 by Day % Change'
  },

  'nse_variations_loosers': {
    group: 'Calendar / Regime', mode: 'RANKED',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol',         label: 'Symbol' },
      { key: 'ltp',            label: 'LTP ₹', numeric: true },
      { key: 'prev_price',     label: 'Prev Close ₹', numeric: true },
      { key: 'net_price',      label: 'Net Change', numeric: true },
      { key: '_pChange',       label: 'Day Change %', derived: true, numeric: true },
      { key: 'trade_quantity', label: 'Volume', numeric: true }
    ],
    sort: { field: '_pChange', dir: 'asc' },
    derive: rec => ({
      _pChange: rec.prev_price > 0 ? ((rec.ltp - rec.prev_price) / rec.prev_price) * 100 : 0
    }),
    topN: 5,
    topLabel: 'Top 5 Day Losers by % Change (Worst First)'
  },

  'nse_volume_gainers': {
    group: 'Calendar / Regime', mode: 'RANKED',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol',          label: 'Symbol' },
      { key: 'companyName',     label: 'Company' },
      { key: 'ltp',             label: 'LTP ₹', numeric: true },
      { key: 'pChange',         label: '% Change', numeric: true },
      { key: 'volume',          label: 'Today Volume', numeric: true },
      { key: 'week1AvgVolume',  label: '1-Wk Avg Volume', numeric: true },
      { key: 'week1volChange',  label: 'Volume Spike Ratio', numeric: true }
    ],
    sort: { field: 'week1volChange', dir: 'desc' },
    topN: 5,
    topLabel: 'Top 5 Volume Gainers by Spike Ratio vs 1-Week Average'
  },

  'nse_market_turnover': {
    group: 'Calendar / Regime', mode: 'RANKED',
    identityField: 'segment',
    preprocess: flattenMarketTurnover,
    displayColumns: [
      { key: 'segment',     label: 'Market Segment' },
      { key: 'yestVolume',  label: 'Yesterday Volume', numeric: true },
      { key: 'yestValue',   label: 'Yesterday Value ₹', numeric: true },
      { key: 'todayVolume', label: 'Today Volume', numeric: true },
      { key: 'todayValue',  label: 'Today Value ₹', numeric: true },
      { key: 'todayOI',     label: 'Today OI', numeric: true }
    ],
    sort: { field: 'yestValue', dir: 'desc' },
    topN: null,
    topLabel: 'Market Segment Turnover (all segments; ranked by Yesterday Value when today is empty)'
  },

  // ══════════════════════════════════════════════════════
  // GROUP: Surveillance
  'nse_trade_to_trade': {
    group: 'Surveillance', mode: 'DIRECTORY', identityField: 'symbol',
    displayColumns: [
      { key: 'symbol', label: 'Symbol' }, { key: 'series', label: 'T2T Series' },
      { key: 'name', label: 'Security' }, { key: 'close', label: 'Close ₹', numeric: true },
      { key: 'tradeMode', label: 'Trade Mode' }, { key: 'intradayEligible', label: 'Intraday Eligible' }
    ],
    topN: null, topLabel: 'Delivery-only securities (no intraday)'
  },

  'kite_derivatives_contract_master': {
    group: 'Derivatives & Options', mode: 'DIRECTORY', identityField: 'symbol',
    displayColumns: [
      { key: 'symbol', label: 'Underlying' }, { key: 'exchange', label: 'Exchange' },
      { key: 'nearestExpiry', label: 'Nearest Expiry' },
      { key: 'nearestLotSize', label: 'Nearest Lot Size', numeric: true },
      { key: 'expiryCount', label: 'Expiries', numeric: true },
      { key: 'contractCount', label: 'Contracts', numeric: true },
      { key: 'contractTypes', label: 'Types' }, { key: 'sourceTrust', label: 'Source Trust' }
    ],
    topN: null, topLabel: 'Compact underlying-level lot schedules (third-party reference)'
  },

  'nse_board_meetings': {
    group: 'Calendar / Regime', mode: 'NEXT_5', identityField: 'symbol',
    displayColumns: [
      { key: 'symbol', label: 'Symbol' }, { key: 'meetingDate', label: 'Meeting Date' },
      { key: 'purpose', label: 'Purpose' }, { key: 'resultsEvent', label: 'Results Event' },
      { key: 'description', label: 'Description' }, { key: 'attachment', label: 'Attachment' }
    ],
    sort: { field: 'meetingDate', dir: 'asc' }, topN: 5,
    topLabel: 'Next 5 board meetings / results events'
  },

  'nse_most_active_futures': {
    group: 'Derivatives & Options', mode: 'RANKED', identityField: 'symbol',
    displayColumns: [
      { key: 'symbol', label: 'Underlying' }, { key: 'identifier', label: 'Contract' },
      { key: 'expiryDate', label: 'Expiry' },
      { key: 'contractsTraded', label: 'Contracts Traded', numeric: true },
      { key: 'turnover', label: 'Turnover', numeric: true },
      { key: 'openInterest', label: 'Open Interest', numeric: true }, { key: 'basis', label: 'Rank Basis' }
    ],
    sort: { field: 'contractsTraded', dir: 'desc' }, topN: 5,
    topLabel: 'Most-active futures by contracts traded'
  },

  'nse_most_active_options': {
    group: 'Derivatives & Options', mode: 'RANKED', identityField: 'symbol',
    displayColumns: [
      { key: 'symbol', label: 'Underlying' }, { key: 'identifier', label: 'Contract' },
      { key: 'expiryDate', label: 'Expiry' }, { key: 'optionType', label: 'Option Type' },
      { key: 'strikePrice', label: 'Strike ₹', numeric: true },
      { key: 'contractsTraded', label: 'Contracts Traded', numeric: true },
      { key: 'turnover', label: 'Turnover', numeric: true }, { key: 'basis', label: 'Rank Basis' }
    ],
    sort: { field: 'contractsTraded', dir: 'desc' }, topN: 5,
    topLabel: 'Most-active options by contracts traded (not underlying direction)'
  },

  'nse_ipo_issue_calendar': {
    group: 'Calendar / Regime', mode: 'DIRECTORY', identityField: 'symbol',
    displayColumns: [
      { key: 'symbol', label: 'Symbol' }, { key: 'companyName', label: 'Company' },
      { key: 'status', label: 'Actual Status' }, { key: 'feedSection', label: 'Feed Section' },
      { key: 'issueStartDate', label: 'Issue Start' }, { key: 'issueEndDate', label: 'Issue End' },
      { key: 'issuePrice', label: 'Issue Price' },
      { key: 'subscriptionTimes', label: 'Subscription ×', numeric: true }
    ],
    topN: null, topLabel: 'Active, Closed and Forthcoming IPO issues'
  },

  'nse_pr_market_snapshot': {
    group: 'Price & Universe', mode: 'DIRECTORY', identityField: 'symbol',
    displayColumns: [
      { key: 'section', label: 'Section' }, { key: 'symbol', label: 'Symbol' },
      { key: 'name', label: 'Security' }, { key: 'event', label: '52-Week Event' },
      { key: 'exDate', label: 'Ex-Date' }, { key: 'recordDate', label: 'Record Date' },
      { key: 'purpose', label: 'Corporate Action' },
      { key: 'marketCapCr', label: 'Market Cap ₹ Cr', numeric: true },
      { key: 'pctChange', label: '% Change', numeric: true }
    ],
    topN: null, topLabel: 'Symbol-safe PR market context (unscored)'
  },
  // ══════════════════════════════════════════════════════
  'nse_asm': {
    group: 'Surveillance', mode: 'RANKED',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol',        label: 'Symbol' },
      { key: 'company',       label: 'Company' },
      { key: 'stage',         label: 'ASM Stage' },
      { key: 'measure',       label: 'Measure' },
      { key: 'code',          label: 'Code' },
      { key: 'effectiveDate', label: 'Effective Date' }
    ],
    sort: { field: '_stageRank', dir: 'desc', abs: false },
    derive: rec => ({
      _stageRank: _schemaStageRank(rec.stage)
    }),
    topN: 5,
    topLabel: 'Top 5 by Highest ASM Stage Severity (Stage 4 = most restricted)'
  },

  'nse_gsm': {
    group: 'Surveillance', mode: 'RANKED',
    identityField: 'Symbol',
    displayColumns: [
      { key: 'Symbol',      label: 'Symbol' },
      { key: 'Company',     label: 'Company' },
      { key: 'GSM Stage',   label: 'GSM Stage' },
      { key: 'Surv. Code',  label: 'Surv. Code' },
      { key: 'Description', label: 'Description' },
      { key: 'Date',        label: 'Effective Date' }
    ],
    sort: { field: '_stageRank', dir: 'desc', abs: false },
    derive: rec => ({
      _stageRank: _schemaStageRank(rec['GSM Stage'])
    }),
    topN: 5,
    topLabel: 'Top 5 by Highest GSM Stage Severity (Stage VI = most restricted)'
  },

  'screener_in_fii_holding_change': {
    group: 'Institutional / FII (third-party)', mode: 'LATEST_5',
    identityField: 'name',
    displayColumns: [
      { key: 'name', label: 'Name', wide: true },
      { key: 'fiiHoldPct', label: 'FII Hold %' },
      { key: 'fiiChgPct', label: 'Chg %' }
    ],
    sort: { field: 'fiiChgPct', dir: 'desc' },
    topN: 10,
    topLabel: 'Screener.in FII hold change (names only, not daily FII tape)'
  },
  'tickertape_fii_holding_change_3m': {
    group: 'Institutional / FII (third-party)', mode: 'LATEST_5',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol', label: 'Symbol' },
      { key: 'name', label: 'Name', wide: true },
      { key: 'fiiHoldPct', label: 'FII Hold %' },
      { key: 'fiiChgPct', label: '3M Chg %' }
    ],
    sort: { field: 'fiiChgPct', dir: 'desc' },
    topN: 10,
    topLabel: 'Tickertape 3M FII hold change (not daily FII tape)'
  },
  'dhan_fii_holding_change': {
    group: 'Institutional / FII (third-party)', mode: 'LATEST_5',
    identityField: 'symbol',
    displayColumns: [
      { key: 'symbol', label: 'Symbol' },
      { key: 'name', label: 'Name', wide: true },
      { key: 'fiiChgPct', label: 'FII Chg %' }
    ],
    sort: { field: 'fiiChgPct', dir: 'desc' },
    topN: 10,
    topLabel: 'Dhan FII hold change (not daily FII tape)'
  },
  'equitymaster_fii_buys_reference': {
    group: 'Institutional / FII (third-party)', mode: 'LATEST_5',
    identityField: 'name',
    displayColumns: [
      { key: 'name', label: 'Name', wide: true }
    ],
    sort: { field: 'name', dir: 'asc' },
    topN: 10,
    topLabel: 'Equitymaster names (no ticker, not daily FII tape)'
  }
};

// ─────────────────────────────────────────────────────────────────────────────
// Lookup helper: resolve schema from a pipe-separated keys string
// e.g. "nse_variations_gainers|nse_market_variations" → first match wins
// ─────────────────────────────────────────────────────────────────────────────
window.getSchemaForItem = function(item) {
  if (!item || !item.active_source_keys) return null;
  const keys = item.active_source_keys.split('|');
  for (const k of keys) {
    const trimmed = k.trim();
    if (window.LINK_SCHEMAS[trimmed]) return window.LINK_SCHEMAS[trimmed];
  }
  return null;
};
