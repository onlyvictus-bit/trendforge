// screener.js — TrendForge Symbol Screener Engine (v1)
// ─────────────────────────────────────────────────────────────────────────────
// Separate from consensus.js (voting). This = feature table + filters + rank.
// Docs: SCREENER.md · INDEX.md · ARCHITECTURE.md
//
// Design goals:
//   strong   — only real sample fields; null → "—"; no greeks invent
//   robust   — try/catch per extractor; records_sample only; preopen flat-safe
//   speed    — one inventory index pass; build once; filter/sort in memory
//   efficient— dedupe by source_key (skip PROVENANCE copies); ≤42×250 visits
//   future   — registerScreenerExtractor / registerScreenerColumn / engines[]
//
// Load order: schemas.js → consensus.js → plugins → screener.js → app.js
// ─────────────────────────────────────────────────────────────────────────────
'use strict';

const ScreenerEngine = (() => {
  // ═══════════════════════════════════════════════════════════════════════════
  // CONFIG
  // ═══════════════════════════════════════════════════════════════════════════
  const CONFIG = {
    version: '1.3',
    scorePolicy: {
      id: 'trendforge.screener.a-only.v1',
      scoredFamilies: ['A'],
      informationalFamilies: ['B', 'C'],
      scoredFields: ['price.pctChange', 'price.gapPercent', 'volume.spikeX']
    },
    defaultUniverse: 'n500',   // n50 | n100 | n500 | all
    maxSampleRows: 250,
    tableLimit: 200,           // max rows rendered (speed); full map kept in cache
    searchDebounceMs: 120,     // UI search debounce
    // LTP priority when multiple A feeds contribute (first match wins if empty)
    priceSourcePriority: [
      'nse_most_active_value',
      'nse_most_active_volume',
      'nse_variations_gainers',
      'nse_variations_loosers',
      'nse_volume_gainers',
      'nse_preopen_fo',
      'nse_sector_constituents',
      'nse_bhavcopy_eod',
      'bse_bhavcopy_eod'
    ],
    // Stable contract for future think engines (rename = version bump)
    featureContract: {
      id: 'trendforge.screener.featureTable.v1.3',
      fields: [
        'symbol', 'inN50', 'inN100', 'inN500',
        'price.ltp', 'price.pctChange', 'price.gapPercent',
        'volume.qty', 'volume.spikeX',
        'boards', 'deals', 'flags', 'risk', 'fo', 'market',
        'score', 'scoreParts', 'sources'
      ],
      metadataFields: ['scorePolicy']
    }
  };

  // Static Nifty 50 (large-cap core — same idea as consensus.js; local copy, no import)
  const NIFTY_50_STATIC = [
    'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK', 'BAJAJ-AUTO',
    'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BHARTIARTL', 'CIPLA', 'COALINDIA', 'DRREDDY',
    'EICHERMOT', 'ETERNAL', 'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE', 'HEROMOTOCO',
    'HINDALCO', 'HINDUNILVR', 'ICICIBANK', 'INDUSINDBK', 'INFY', 'ITC', 'JIOFIN',
    'JSWSTEEL', 'KOTAKBANK', 'LT', 'M&M', 'MARUTI', 'MAXHEALTH', 'NESTLEIND', 'NTPC',
    'ONGC', 'POWERGRID', 'RELIANCE', 'SBILIFE', 'SBIN', 'SUNPHARMA', 'TCS', 'TATACONSUM',
    'TATAMOTORS', 'TATASTEEL', 'TECHM', 'TITAN', 'TRENT', 'ULTRACEMCO', 'WIPRO'
  ];

  // Nifty Next 50 (approx for N100 = n50 ∪ next50). Label UI "N100 static approx".
  const NIFTY_NEXT50_STATIC = [
    'ABB', 'ACC', 'ADANIGREEN', 'ADANIPOWER', 'AMBUJACEM', 'AUROPHARMA', 'BANKBARODA',
    'BERGEPAINT', 'BOSCHLTD', 'BPCL', 'CANBK', 'CHOLAFIN', 'COLPAL', 'DABUR', 'DIVISLAB',
    'DLF', 'GAIL', 'GODREJCP', 'HAVELLS', 'HAL', 'ICICIGI', 'ICICIPRULI', 'INDIGO',
    'IOC', 'IRCTC', 'JINDALSTEL', 'JUBLFOOD', 'LICI', 'LODHA', 'LUPIN', 'MARICO',
    'MFSL', 'MOTHERSON', 'NAUKRI', 'NMDC', 'NYKAA', 'PAGEIND', 'PAYTM', 'PERSISTENT',
    'PETRONET', 'PIDILITIND', 'PNB', 'POLYCAB', 'SAIL', 'SIEMENS', 'SRF', 'TORNTPHARM',
    'TVSMOTOR', 'UNITDSPR', 'ZOMATO'
  ];

  const SYMBOL_ALIASES = [
    'symbol', 'Symbol', 'SYMBOL', 'sym', 'securitySymbol',
    'underlying', 'Underlying', 'underlyingSymbol', 'ScripSymbol', 'TradingSymbol',
    'TckrSymb'
  ];
  const NAME_ALIASES = [
    'scripname', 'scripName', 'ScripName', 'securityName',
    'companyName', 'Company Name', 'Company', 'name', 'Security'
  ];

  // ═══════════════════════════════════════════════════════════════════════════
  // UTILS (local — do not couple to consensus IIFE)
  // ═══════════════════════════════════════════════════════════════════════════
  function num(val) {
    if (val == null || val === '') return null;
    if (typeof val === 'number') return Number.isFinite(val) ? val : null;
    const s = String(val).replace(/,/g, '').replace(/%/g, '').trim();
    if (!s || s === '-' || s === '?' || s === 'NULL' || s === 'NA' || s === 'N/A') return null;
    const n = parseFloat(s);
    return Number.isFinite(n) ? n : null;
  }

  function esc(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function canonSymbol(raw) {
    if (raw == null || raw === '') return null;
    let s = String(raw).trim().toUpperCase();
    s = s.replace(/\s*-EQ$|\s+EQ$|^EQ:/i, '').replace(/\s+/g, '');
    if (!s || s === '-' || s === 'NA' || s === 'NULL' || s === 'UNDEFINED') return null;
    return s;
  }

  function pickSymbol(row) {
    if (!row || typeof row !== 'object') return null;
    for (const f of SYMBOL_ALIASES) {
      if (row[f] != null && row[f] !== '') {
        const s = canonSymbol(row[f]);
        if (s) return s;
      }
    }
    for (const f of NAME_ALIASES) {
      if (row[f] != null && row[f] !== '') {
        const s = canonSymbol(row[f]);
        if (s) return s;
      }
    }
    if (row.metadata && typeof row.metadata === 'object' && row.metadata.symbol) {
      return canonSymbol(row.metadata.symbol);
    }
    return null;
  }

  function firstField(row, fields) {
    for (const f of fields) {
      if (row[f] != null && row[f] !== '') return row[f];
    }
    return undefined;
  }

  function clamp(v, lo, hi) {
    if (v == null || !Number.isFinite(v)) return null;
    return Math.max(lo, Math.min(hi, v));
  }

  function isoDate(value) {
    const match = String(value || '').match(/\d{4}-\d{2}-\d{2}/);
    return match ? match[0] : null;
  }

  function itemSnapshotDate(item) {
    return isoDate(item && item.data_date);
  }

  function deterministicDaysBetween(fromDate, toDate) {
    const from = isoDate(fromDate);
    const to = isoDate(toDate);
    if (!from || !to) return null;
    const start = Date.parse(`${from}T00:00:00Z`);
    const end = Date.parse(`${to}T00:00:00Z`);
    if (!Number.isFinite(start) || !Number.isFinite(end)) return null;
    return Math.round((end - start) / 86400000);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // INVENTORY INDEX — one item per source_key (strongest status wins)
  // ═══════════════════════════════════════════════════════════════════════════
  function indexBySourceKey(inventory) {
    const map = new Map();
    const statusRank = {
      STRONG: 6, SUPPORTING: 5, THIRD_PARTY: 4,
      CONTEXT_NEWS: 3, COMPANION: 2, PROVENANCE: 1
    };
    for (const item of inventory || []) {
      const keys = String(item.active_source_keys || '').split('|').map(k => k.trim()).filter(Boolean);
      for (const sk of keys) {
        const prev = map.get(sk);
        if (!prev) {
          map.set(sk, item);
          continue;
        }
        const pr = statusRank[prev.status] || 0;
        const nr = statusRank[item.status] || 0;
        const pn = (prev.records_sample || []).length;
        const nn = (item.records_sample || []).length;
        if (nr > pr || (nr === pr && nn > pn)) map.set(sk, item);
      }
    }
    return map;
  }

  function getRecords(item) {
    if (!item) return [];
    const rs = item.records_sample;
    if (Array.isArray(rs) && rs.length) return rs;
    return []; // never sample_row for extract (AMFI wrapper gotcha)
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // UNIVERSE
  // ═══════════════════════════════════════════════════════════════════════════
  function buildUniverseSets(inventory) {
    const n50 = new Set(NIFTY_50_STATIC);
    const next50 = new Set(NIFTY_NEXT50_STATIC);
    const n100 = new Set([...n50, ...next50]);
    let n500 = new Set(n100);
    const officialN500 = new Set();
    let completeOfficial500 = false;
    let n500FromInv = 0;

    for (const item of inventory || []) {
      const keys = String(item.active_source_keys || '');
      if (!/nifty500_constituents|nifty_500|ind_nifty500/i.test(keys)) continue;
      for (const r of getRecords(item)) {
        const s = pickSymbol(r) || canonSymbol(r.Symbol || r.symbol);
        if (s) officialN500.add(s);
      }
      for (const e of (item.entity_list || [])) {
        const s = canonSymbol(e);
        if (s) officialN500.add(s);
      }
      const sourceRows = Number(item.source_row_count || item.source_rows || 0);
      const normalizedRows = Number(item.normalized_row_count || 0);
      if (officialN500.size >= 500 && sourceRows >= 500 && normalizedRows >= 500) {
        completeOfficial500 = true;
      }
    }

    if (completeOfficial500) {
      n500 = new Set(officialN500);
      n500FromInv = n500.size;
    } else {
      for (const s of officialN500) {
        if (!n500.has(s)) n500FromInv++;
        n500.add(s);
      }
    }

    return {
      n50,
      n100,
      n500,
      all: null, // filled after table build
      meta: {
        n50: n50.size,
        n100: n100.size,
        n500: n500.size,
        n500FromInv,
        n500Partial: !completeOfficial500,
        completeOfficial500,
        label500: !completeOfficial500
          ? `Nifty 500 partial (~${n500.size})`
          : `Nifty 500 official (${n500.size})`
      }
    };
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // EMPTY RECORD FACTORY
  // ═══════════════════════════════════════════════════════════════════════════
  function emptyRecord(symbol) {
    return {
      symbol,
      inN50: false,
      inN100: false,
      inN500: false,
      price: {
        ltp: null, pctChange: null, gapPercent: null,
        open: null, high: null, low: null, prevClose: null,
        _src: null, _srcPriority: 999
      },
      volume: { qty: null, valueCr: null, spikeX: null, _src: null },
      boards: {},
      deals: {
        bulkBuy: 0, bulkSell: 0, blockBuy: 0, blockSell: 0,
        buyValueCr: null, sellValueCr: null, netDealCr: null,
        largeDealCr: null, valueComplete: null, netSide: null, _src: []
      },
      flags: {
        pit: false, sast: false, reg29: false, reg31: false,
        buyback: false, results: false, corpAction: false, slb: false,
        pitDir: null, pitType: null, pitValueCr: null,
        pitValueComplete: null,
        boardMeeting: false, boardMeetingDate: null, boardMeetingPurpose: null,
        daysToMeeting: null, resultsEvent: false, boardMeetingAttachment: null,
        ipo: false, ipoStatus: null, ipoStartDate: null, ipoEndDate: null,
        wk52Event: null, corpActionDate: null, corpActionPurpose: null,
        corpActionDetails: [], _src: []
      },
      risk: {
        asm: false, asmStage: null, asmStageNum: null, asmFramework: null,
        gsm: false, gsmStage: null, gsmStageNum: null, gsmIndicator: null,
        pledgePct: null,
        t2t: false, t2tSeries: null, intradayEligible: null, _src: []
      },
      fo: {
        oiSpurt: false, oiPctChg: null, oiDirection: null,
        futOiPctChg: null, optOiPctChg: null, futOI: null, optOI: null,
        contracts: 0, nearExpiry: false,
        nearestLotSize: null, nearestLotExpiry: null, lotSchedules: [],
        mostActiveFutures: false, mostActiveOptions: false,
        tradedContractActivity: {
          futuresRows: 0, optionsRows: 0,
          futuresContractsTraded: 0, optionsContractsTraded: 0,
          futuresTurnover: 0, optionsTurnover: 0
        }, _src: []
      },
      market: { marketCapCr: null, _src: [] },
      sources: [],
      score: null,
      scoreParts: []
    };
  }

  function touchSource(rec, key, rowNo) {
    if (!rec.sources.some(s => s.key === key && s.row_no === rowNo)) {
      rec.sources.push({ key, row_no: rowNo });
    }
  }

  function ensureRec(table, symbol) {
    let rec = table.get(symbol);
    if (!rec) {
      rec = emptyRecord(symbol);
      table.set(symbol, rec);
    }
    return rec;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // EXTRACTOR REGISTRY — future-proof: registerScreenerExtractor(key, fn)
  // fn(ctx) where ctx = { item, records, table, key, row_no, helpers }
  // ═══════════════════════════════════════════════════════════════════════════
  /** @type {Map<string, { family: string, extract: Function, enabled: boolean }>} */
  const EXTRACTORS = new Map();

  function registerScreenerExtractor(sourceKey, def) {
    if (!sourceKey || !def || typeof def.extract !== 'function') {
      throw new Error('[Screener] registerScreenerExtractor needs sourceKey + extract fn');
    }
    EXTRACTORS.set(sourceKey, {
      family: def.family || 'custom',
      extract: def.extract,
      enabled: def.enabled !== false,
      label: def.label || sourceKey
    });
  }

  // ── A-family helpers ───────────────────────────────────────────────────────
  function writePrice(rec, key, rowNo, fields, priorityIndex) {
    const p = rec.price;
    const pri = priorityIndex == null ? 50 : priorityIndex;
    const ltp = num(fields.ltp);
    const pct = num(fields.pctChange);
    const gap = num(fields.gapPercent);
    const open = num(fields.open);
    const high = num(fields.high);
    const low = num(fields.low);
    const prev = num(fields.prevClose);

    // Prefer higher-priority sources for LTP (lower index = better)
    if (ltp != null && (p.ltp == null || pri < p._srcPriority)) {
      p.ltp = ltp;
      p._src = key;
      p._srcPriority = pri;
    }
    if (pct != null && (p.pctChange == null || pri <= p._srcPriority + 1)) {
      p.pctChange = pct;
    }
    if (gap != null) p.gapPercent = gap;
    if (open != null && p.open == null) p.open = open;
    if (high != null && p.high == null) p.high = high;
    if (low != null && p.low == null) p.low = low;
    if (prev != null && p.prevClose == null) p.prevClose = prev;
    touchSource(rec, key, rowNo);
  }

  function writeVolume(rec, key, rowNo, fields) {
    const v = rec.volume;
    const qty = num(fields.qty);
    const val = num(fields.valueCr);
    const spike = num(fields.spikeX);
    if (qty != null && (v.qty == null || qty > v.qty)) {
      v.qty = qty;
      v._src = key;
    }
    if (val != null && v.valueCr == null) v.valueCr = val;
    if (spike != null && (v.spikeX == null || spike > v.spikeX)) {
      v.spikeX = spike;
      v._src = key;
    }
    touchSource(rec, key, rowNo);
  }

  function setBoardRank(rec, boardName, rank, key, rowNo) {
    if (rank == null) return;
    const prev = rec.boards[boardName];
    if (prev == null || rank < prev) rec.boards[boardName] = rank;
    touchSource(rec, key, rowNo);
  }

  function pctFromRow(r) {
    const ltp = num(firstField(r, ['ltp', 'lastPrice', 'Last ₹', 'close', 'Close ₹', 'last']));
    const prev = num(firstField(r, ['prev_price', 'previousClose', 'prevClose', 'Prev Close ₹', 'prev']));
    if (ltp != null && prev != null && prev > 0) return ((ltp - prev) / prev) * 100;
    return num(firstField(r, ['pChange', 'net_price', 'percentChange', 'perChange', '%Chg']));
  }

  function ltpFromRow(r) {
    return num(firstField(r, [
      'ltp', 'lastPrice', 'Last ₹', 'close', 'Close ₹', 'ClsPric', 'last', 'LTP', 'price', 'PRICE'
    ]));
  }

  // Rank within a sorted board list (1 = best)
  function applyRankedBoard(table, records, key, rowNo, boardName, sortFn, desc, pri) {
    const scored = [];
    for (const r of records) {
      const sym = pickSymbol(r);
      if (!sym) continue;
      const m = sortFn(r);
      if (m == null) continue;
      scored.push({ sym, m, r });
    }
    scored.sort((a, b) => desc ? b.m - a.m : a.m - b.m);
    const seen = new Set();
    let rank = 0;
    for (const { sym, r } of scored) {
      if (seen.has(sym)) continue;
      seen.add(sym);
      rank++;
      if (rank > 50) break;
      const rec = ensureRec(table, sym);
      setBoardRank(rec, boardName, rank, key, rowNo);
      writePrice(rec, key, rowNo, {
        ltp: ltpFromRow(r),
        pctChange: pctFromRow(r),
        open: num(firstField(r, ['open', 'open_price', 'Open ₹', 'OpnPric'])),
        high: num(firstField(r, ['high', 'high_price', 'High ₹', 'HghPric'])),
        low: num(firstField(r, ['low', 'low_price', 'Low ₹', 'LwPric'])),
        prevClose: num(firstField(r, ['prev_price', 'previousClose', 'prevClose', 'Prev Close ₹', 'PrvsClsgPric']))
      }, pri);
      const vol = num(firstField(r, ['volume', 'trade_quantity', 'qty', 'Quantity', 'TtlTradgVol', 'finalQuantity']));
      const spike = num(firstField(r, ['week1volChange', 'volChange', 'volumeChange']));
      const turnover = num(firstField(r, ['turnover', 'tradedValue', 'totalTurnover', 'TtlTrfVal']));
      writeVolume(rec, key, rowNo, {
        qty: vol,
        spikeX: spike,
        valueCr: turnover != null && turnover > 1e5 ? turnover / 1e7 : turnover
      });
    }
  }

  // ── Register A extractors ──────────────────────────────────────────────────
  function registerAExtractors() {
    const pri = (key) => {
      const i = CONFIG.priceSourcePriority.indexOf(key);
      return i < 0 ? 50 : i;
    };

    registerScreenerExtractor('nse_variations_gainers', {
      family: 'momentum', label: 'Day Gainers',
      extract({ records, table, key, row_no }) {
        applyRankedBoard(table, records, key, row_no, 'gainers', pctFromRow, true, pri(key));
      }
    });
    registerScreenerExtractor('nse_variations_loosers', {
      family: 'momentum', label: 'Day Losers',
      extract({ records, table, key, row_no }) {
        applyRankedBoard(table, records, key, row_no, 'loosers', pctFromRow, false, pri(key));
      }
    });
    registerScreenerExtractor('nse_volume_gainers', {
      family: 'volume', label: 'Volume Gainers',
      extract({ records, table, key, row_no }) {
        applyRankedBoard(table, records, key, row_no, 'volGainers',
          r => num(r.week1volChange) ?? num(r.volume), true, pri(key));
      }
    });
    registerScreenerExtractor('nse_most_active_value', {
      family: 'momentum', label: 'Most Active Value',
      extract({ records, table, key, row_no }) {
        applyRankedBoard(table, records, key, row_no, 'mostActiveVal',
          r => num(firstField(r, ['totalTradedValue', 'turnover', 'tradedValue', 'value'])) ?? ltpFromRow(r),
          true, pri(key));
      }
    });
    registerScreenerExtractor('nse_most_active_volume', {
      family: 'momentum', label: 'Most Active Volume',
      extract({ records, table, key, row_no }) {
        applyRankedBoard(table, records, key, row_no, 'mostActiveVol',
          r => num(firstField(r, ['totalTradedVolume', 'volume', 'qty'])) ?? 0, true, pri(key));
      }
    });
    registerScreenerExtractor('nse_most_active_underlying', {
      family: 'fo', label: 'Most Active Underlying',
      extract({ records, table, key, row_no }) {
        applyRankedBoard(table, records, key, row_no, 'mostActiveUnd',
          r => num(firstField(r, ['volume', 'totalTradedVolume', 'qty'])) ?? 0, true, 40);
      }
    });
    registerScreenerExtractor('nse_preopen_fo', {
      family: 'momentum', label: 'Pre-Open Gap',
      extract({ records, table, key, row_no }) {
        // Flat-safe: our inventory may already be {symbol, gapPercent, ...}
        for (const r of records) {
          let row = r;
          if (r.metadata && typeof r.metadata === 'object') {
            const meta = r.metadata;
            const detail = r.detail || {};
            const pre = detail.preOpenMarket || detail.preopen || {};
            const iep = num(pre.IEP ?? meta.iep ?? pre.iep);
            const prev = num(meta.previousClose ?? pre.previousClose);
            let gap = null;
            if (iep != null && prev != null && prev > 0) gap = ((iep - prev) / prev) * 100;
            row = {
              symbol: meta.symbol,
              ltp: meta.lastPrice ?? iep,
              pChange: meta.pChange,
              previousClose: prev,
              gapPercent: gap,
              finalQuantity: meta.finalQuantity,
              totalTurnover: meta.totalTurnover
            };
          }
          const sym = pickSymbol(row);
          if (!sym) continue;
          const rec = ensureRec(table, sym);
          const gap = num(row.gapPercent);
          writePrice(rec, key, row_no, {
            ltp: ltpFromRow(row) ?? num(row.iep),
            pctChange: pctFromRow(row),
            gapPercent: gap,
            prevClose: num(row.previousClose ?? row.prevClose)
          }, pri(key));
          writeVolume(rec, key, row_no, {
            qty: num(row.finalQuantity),
            valueCr: num(row.totalTurnover) != null ? num(row.totalTurnover) / 1e7 : null
          });
          if (gap != null) {
            // rank later in second pass optional; store gap as board signal
            if (gap > 0) setBoardRank(rec, 'gapUp', Math.max(1, 11 - Math.min(10, Math.round(gap))), key, row_no);
            if (gap < 0) setBoardRank(rec, 'gapDn', Math.max(1, 11 - Math.min(10, Math.round(-gap))), key, row_no);
          }
        }
      }
    });

    function bhavExtract({ records, table, key, row_no }) {
      for (const r of records) {
        const sym = pickSymbol(r);
        if (!sym) continue;
        const rec = ensureRec(table, sym);
        writePrice(rec, key, row_no, {
          ltp: ltpFromRow(r),
          pctChange: pctFromRow(r),
          open: num(firstField(r, ['open', 'Open ₹', 'OpnPric', 'open_price'])),
          high: num(firstField(r, ['high', 'High ₹', 'HghPric', 'high_price'])),
          low: num(firstField(r, ['low', 'Low ₹', 'LwPric', 'low_price'])),
          prevClose: num(firstField(r, [
            'previousClose', 'prevClose', 'Prev Close ₹', 'PrvsClsgPric', 'prev_price'
          ]))
        }, pri(key));
        writeVolume(rec, key, row_no, {
          qty: num(firstField(r, ['volume', 'Volume', 'TtlTradgVol', 'trade_quantity'])),
          valueCr: num(firstField(r, ['tradedValue', 'TtlTrfVal', 'turnover']))
        });
      }
    }
    registerScreenerExtractor('nse_bhavcopy_eod', { family: 'price', label: 'NSE Bhavcopy', extract: bhavExtract });
    registerScreenerExtractor('bse_bhavcopy_eod', { family: 'price', label: 'BSE Bhavcopy', extract: bhavExtract });

    registerScreenerExtractor('nse_sector_constituents', {
      family: 'universe', label: 'Sector Constituents',
      extract({ records, table, key, row_no }) {
        // May be index rows (NIFTY AUTO) not stocks — only write if pickSymbol looks like equity
        for (const r of records) {
          const sym = pickSymbol(r);
          if (!sym || sym.startsWith('NIFTY')) continue;
          const rec = ensureRec(table, sym);
          writePrice(rec, key, row_no, {
            ltp: ltpFromRow(r),
            pctChange: pctFromRow(r),
            open: num(r.open), high: num(r.dayHigh ?? r.high), low: num(r.dayLow ?? r.low)
          }, pri(key));
        }
      }
    });
    registerScreenerExtractor('nse_nifty500_constituents', {
      family: 'universe', label: 'Nifty 500',
      extract({ records, table, key, row_no }) {
        for (const r of records) {
          const sym = pickSymbol(r);
          if (!sym) continue;
          const rec = ensureRec(table, sym);
          touchSource(rec, key, row_no);
          // membership only; no LTP in this feed
        }
      }
    });
    registerScreenerExtractor('nse_equity_universe', {
      family: 'universe', label: 'Equity Universe',
      extract({ records, table, key, row_no }) {
        for (const r of records) {
          const sym = pickSymbol(r);
          if (!sym) continue;
          ensureRec(table, sym);
          touchSource(ensureRec(table, sym), key, row_no);
        }
      }
    });
    registerScreenerExtractor('nse_all_indices', {
      family: 'universe', label: 'All Indices',
      extract({ records, table, key, row_no }) {
        // Index-level — skip stock table (identifiers are index names)
        void records; void table; void key; void row_no;
      }
    });
  }

  // ── B/C-family helpers ────────────────────────────────────────────────────
  function addSourceKey(bucket, key) {
    if (!bucket.includes(key)) bucket.push(key);
  }

  function hiddenValue(target, name, factory) {
    if (!Object.prototype.hasOwnProperty.call(target, name)) {
      Object.defineProperty(target, name, {
        value: factory(),
        enumerable: false,
        configurable: false,
        writable: false
      });
    }
    return target[name];
  }

  function normalizedSide(raw) {
    const side = String(raw == null ? '' : raw).trim().toUpperCase();
    if (['BUY', 'B', 'P', 'PURCHASE', 'ACQUIRE', 'ACQUISITION'].includes(side)) return 'BUY';
    if (['SELL', 'S', 'SALE', 'DISPOSE', 'DISPOSAL'].includes(side)) return 'SELL';
    return null;
  }

  function mergeMaxAbs(current, candidate) {
    const n = num(candidate);
    if (n == null) return current;
    if (current == null || Math.abs(n) > Math.abs(current)) return n;
    return current;
  }

  const ROMAN_STAGE_TO_NUMBER = Object.freeze({ 0: 0, I: 1, II: 2, III: 3, IV: 4, V: 5, VI: 6 });
  const NUMBER_TO_ROMAN_STAGE = Object.freeze(['0', 'I', 'II', 'III', 'IV', 'V', 'VI']);

  function stageNumber(raw, maxStage) {
    const token = String(raw == null ? '' : raw).trim().toUpperCase();
    const parsed = ROMAN_STAGE_TO_NUMBER[token];
    return parsed != null && parsed <= maxStage ? parsed : null;
  }

  function describedStage(row, family, maxStage) {
    const text = [row.Description, row.description, row['Surv. Code'], row.survCode]
      .filter(v => v != null && v !== '').join(' | ').toUpperCase();
    const familyPattern = family === 'GSM'
      ? /(?:GSM|GRADED\s+SURVEILLANCE\s+MEASURE)[^|]{0,50}?(?:STAGE\s*)?(0|VI|IV|III|II|I|V)\b/
      : /(?:LTASM|STASM|ASM|ADDITIONAL\s+SURVEILLANCE\s+MEASURE)[^|]{0,50}?STAGE\s*(IV|III|II|I)\b/;
    const match = text.match(familyPattern);
    if (!match) return null;
    return stageNumber(match[1], maxStage);
  }

  function parseAsmContext(row) {
    const raw = firstField(row, ['asmSurvIndicator', 'stage', 'ASM Stage']);
    const rawMatch = String(raw == null ? '' : raw).match(/(?:STAGE\s*)?(IV|III|II|I)\b/i);
    const stage = describedStage(row, 'ASM', 4) ?? stageNumber(rawMatch && rawMatch[1], 4);
    const context = [row.Description, row.description, row['Surv. Code'], row.survCode]
      .filter(Boolean).join(' ').toUpperCase();
    let framework = null;
    if (/\b(?:LTASM|LONG[ -]?TERM)\b/.test(context)) framework = 'LONG_TERM';
    else if (/\b(?:STASM|SHORT[ -]?TERM)\b/.test(context)) framework = 'SHORT_TERM';
    else if (raw != null || /\bASM\b/.test(context)) framework = 'ASM';
    return {
      raw: raw == null ? null : String(raw),
      stage,
      label: stage == null ? null : NUMBER_TO_ROMAN_STAGE[stage],
      framework
    };
  }

  function parseGsmContext(row) {
    const raw = firstField(row, ['GSM Stage', 'stage']);
    const fromDescription = describedStage(row, 'GSM', 6);
    const fromExactIndicator = stageNumber(raw, 6);
    const stage = fromDescription ?? fromExactIndicator;
    return {
      indicator: raw == null ? null : String(raw),
      stage,
      label: stage == null ? null : NUMBER_TO_ROMAN_STAGE[stage]
    };
  }

  const INDEX_UNDERLYINGS = new Set(['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTYNXT50']);

  function parseDateMs(raw) {
    if (raw == null || raw === '') return null;
    const text = String(raw).trim();
    const direct = Date.parse(text);
    if (Number.isFinite(direct)) return direct;
    const match = text.match(/(\d{4}-\d{2}-\d{2})/);
    if (!match) return null;
    const iso = Date.parse(`${match[1]}T00:00:00Z`);
    return Number.isFinite(iso) ? iso : null;
  }

  function isNearExpiry(expiryRaw, referenceRaw) {
    const expiry = parseDateMs(expiryRaw);
    if (expiry == null) return false;
    const reference = parseDateMs(referenceRaw) ?? Date.now();
    const days = (expiry - reference) / 86400000;
    return days >= 0 && days <= 7;
  }

  function itemReferenceDate(item, row) {
    const rowDate = firstField(row, ['Trade Date', 'Biz Date', 'tradeDate', 'date', 'Date']);
    if (rowDate != null) return rowDate;
    const match = String(item && item.data_date || '').match(/\d{4}-\d{2}-\d{2}/);
    return match ? match[0] : null;
  }

  function applyDealRows({ records, table, key, row_no }, kind) {
    const exchange = key.startsWith('bse_') ? 'BSE' : key.startsWith('nse_') ? 'NSE' : key;
    for (const r of records) {
      const symbol = pickSymbol(r);
      const side = normalizedSide(firstField(r, ['Buy/Sell', 'buySell', 'side', 'TRANSACTION_TYPE']));
      if (!symbol || !side) continue;

      const rec = ensureRec(table, symbol);
      const qty = num(firstField(r, ['Quantity Traded', 'qty', 'quantity', 'QUANTITY']));
      const price = num(firstField(r, ['Trade Price / Wght. Avg. Price', 'watp', 'price', 'PRICE']));
      const date = firstField(r, ['Date', 'date', 'DEAL_DATE']) || '';
      const client = firstField(r, ['Client Name', 'clientName', 'CLIENT_NAME']) || '';
      const signature = [exchange, kind, symbol, side, date, client, qty, price].join('|');
      const seen = hiddenValue(rec.deals, '_seen', () => new Set());

      touchSource(rec, key, row_no);
      addSourceKey(rec.deals._src, key);
      if (seen.has(signature)) continue;
      seen.add(signature);

      const field = `${kind}${side === 'BUY' ? 'Buy' : 'Sell'}`;
      rec.deals[field] += 1;

      const valueCr = qty != null && price != null ? (qty * price) / 1e7 : null;
      const totals = hiddenValue(rec.deals, '_valueCr', () => ({ BUY: 0, SELL: 0, known: 0, total: 0 }));
      totals.total += 1;
      if (valueCr != null) {
        totals[side] += valueCr;
        totals.known += 1;
        rec.deals.buyValueCr = +totals.BUY.toFixed(4);
        rec.deals.sellValueCr = +totals.SELL.toFixed(4);
        rec.deals.largeDealCr = +(totals.BUY + totals.SELL).toFixed(4);
      }
      rec.deals.valueComplete = totals.known === totals.total;
      rec.deals.netDealCr = rec.deals.valueComplete
        ? +(totals.BUY - totals.SELL).toFixed(4)
        : null;
      if (rec.deals.valueComplete && totals.BUY !== totals.SELL) {
        rec.deals.netSide = totals.BUY > totals.SELL ? 'BUY' : 'SELL';
      } else {
        const buys = rec.deals.bulkBuy + rec.deals.blockBuy;
        const sells = rec.deals.bulkSell + rec.deals.blockSell;
        rec.deals.netSide = buys === sells ? null : (buys > sells ? 'BUY' : 'SELL');
      }
    }
  }

  function foState(rec) {
    return hiddenValue(rec.fo, '_state', () => ({
      contracts: new Map(),
      futContractOI: 0,
      optContractOI: 0,
      futSummaryOI: null,
      optSummaryOI: null
    }));
  }

  function refreshFoOI(rec) {
    const state = foState(rec);
    const fut = [state.futContractOI || null, state.futSummaryOI].filter(v => v != null);
    const opt = [state.optContractOI || null, state.optSummaryOI].filter(v => v != null);
    rec.fo.futOI = fut.length ? Math.max(...fut) : null;
    rec.fo.optOI = opt.length ? Math.max(...opt) : null;
  }

  function normalizedExpiry(raw) {
    if (raw == null || raw === '') return '';
    const text = String(raw).trim();
    const iso = text.match(/\b(\d{4})-(\d{2})-(\d{2})\b/);
    if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
    const named = text.match(/\b(\d{1,2})[-\s]([A-Za-z]{3})[-\s](\d{4})\b/);
    if (named) {
      const months = { JAN: 1, FEB: 2, MAR: 3, APR: 4, MAY: 5, JUN: 6, JUL: 7, AUG: 8, SEP: 9, OCT: 10, NOV: 11, DEC: 12 };
      const month = months[named[2].toUpperCase()];
      if (month) return `${named[3]}-${String(month).padStart(2, '0')}-${String(Number(named[1])).padStart(2, '0')}`;
    }
    const ms = parseDateMs(text);
    if (ms == null) return '';
    const date = new Date(ms);
    return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-');
  }

  function normalizedOptionType(raw) {
    const token = String(raw == null ? '' : raw).trim().toUpperCase();
    if (['CE', 'CALL', 'C'].includes(token)) return 'CE';
    if (['PE', 'PUT', 'P'].includes(token)) return 'PE';
    return '';
  }

  function contractSignature(symbol, kind, row) {
    const expiry = normalizedExpiry(firstField(row, ['expiryDate', 'XpryDt', 'FininstrmActlXpryDt']));
    const strike = num(firstField(row, ['strikePrice', 'StrkPric']));
    const optionType = normalizedOptionType(firstField(row, ['optionType', 'OptnTp']));
    const identifier = String(firstField(row, ['identifier', 'FinInstrmNm']) || '').trim().toUpperCase();
    const hasCanonicalDetail = kind === 'fut' || strike != null || optionType !== '';
    if (expiry && hasCanonicalDetail) {
      return [symbol, kind, expiry, strike == null ? '' : strike, optionType].join('|');
    }
    return [symbol, kind, identifier || [expiry, strike, optionType].join('|')].join('|');
  }

  function oiPctFromRow(row) {
    const direct = num(firstField(row, ['pChangeInOI', 'avgInOI']));
    if (direct != null) return direct;
    const change = num(firstField(row, ['changeInOI', 'ChngInOpnIntrst']));
    let previous = num(firstField(row, ['prevOI', 'previousOI', 'PrvsOpnIntrst']));
    if (previous == null) {
      const latest = num(firstField(row, ['latestOI', 'openInterest', 'OpnIntrst']));
      if (latest != null && change != null) previous = latest - change;
    }
    if (change == null || previous == null || previous === 0) return null;
    return (change / previous) * 100;
  }

  function updateOiChange(rec, kind, candidate) {
    const pct = num(candidate);
    if (pct == null) return;
    if (kind === 'opt') rec.fo.optOiPctChg = mergeMaxAbs(rec.fo.optOiPctChg, pct);
    else rec.fo.futOiPctChg = mergeMaxAbs(rec.fo.futOiPctChg, pct);
    rec.fo.oiPctChg = mergeMaxAbs(rec.fo.oiPctChg, pct);
    rec.fo.oiDirection = rec.fo.oiPctChg > 0 ? 'UP' : rec.fo.oiPctChg < 0 ? 'DOWN' : 'FLAT';
    // The source calls these rows "spurts", but this flag is descriptive only.
    // Non-positive OI can never be represented as a bullish spurt.
    rec.fo.oiSpurt = rec.fo.oiPctChg > 0;
  }

  function applyFoContract(rec, key, rowNo, row, item, kind) {
    const state = foState(rec);
    const signature = contractSignature(rec.symbol, kind, row);

    touchSource(rec, key, rowNo);
    addSourceKey(rec.fo._src, key);
    const oi = num(firstField(row, ['latestOI', 'openInterest', 'OpnIntrst']));
    const existing = state.contracts.get(signature);
    if (!existing) {
      state.contracts.set(signature, { kind, oi: oi || 0 });
      if (oi != null) {
        if (kind === 'opt') state.optContractOI += oi;
        else state.futContractOI += oi;
      }
    } else if (oi != null && oi > existing.oi) {
      const delta = oi - existing.oi;
      existing.oi = oi;
      if (kind === 'opt') state.optContractOI += delta;
      else state.futContractOI += delta;
    }
    rec.fo.contracts = state.contracts.size;

    updateOiChange(rec, kind, oiPctFromRow(row));

    const expiry = firstField(row, ['expiryDate', 'XpryDt', 'FininstrmActlXpryDt']);
    if (isNearExpiry(expiry, itemReferenceDate(item, row))) rec.fo.nearExpiry = true;
    refreshFoOI(rec);
  }

  function registerBCExtractors() {
    for (const key of ['bse_bulk_deals', 'nse_large_deals']) {
      registerScreenerExtractor(key, {
        family: 'deals', label: key === 'bse_bulk_deals' ? 'BSE Bulk Deals' : 'NSE Large Deals',
        extract(ctx) { applyDealRows(ctx, 'bulk'); }
      });
    }
    for (const key of ['bse_block_deals', 'nse_large_deals_snapshot', 'nse_block_deal']) {
      registerScreenerExtractor(key, {
        family: 'deals', label: 'Block Deals',
        extract(ctx) { applyDealRows(ctx, 'block'); }
      });
    }

    registerScreenerExtractor('nse_asm', {
      family: 'risk', label: 'NSE ASM',
      extract({ records, table, key, row_no }) {
        for (const r of records) {
          const symbol = pickSymbol(r);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          const parsed = parseAsmContext(r);
          rec.risk.asm = true;
          rec.risk.asmStage = parsed.label;
          rec.risk.asmStageNum = parsed.stage;
          rec.risk.asmFramework = parsed.framework;
          addSourceKey(rec.risk._src, key);
          touchSource(rec, key, row_no);
        }
      }
    });

    registerScreenerExtractor('nse_gsm', {
      family: 'risk', label: 'NSE GSM',
      extract({ records, table, key, row_no }) {
        for (const r of records) {
          const symbol = pickSymbol(r);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          const parsed = parseGsmContext(r);
          rec.risk.gsm = true;
          rec.risk.gsmIndicator = parsed.indicator;
          rec.risk.gsmStage = parsed.label;
          rec.risk.gsmStageNum = parsed.stage;
          addSourceKey(rec.risk._src, key);
          touchSource(rec, key, row_no);
        }
      }
    });

    registerScreenerExtractor('nse_pit_symbol', {
      family: 'risk', label: 'NSE PIT',
      extract({ records, table, key, row_no }) {
        for (const r of records) {
          const symbol = pickSymbol(r);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          rec.flags.pit = true;
          const pitState = hiddenValue(rec.flags, '_pitState', () => ({
            buy: 0, sell: 0, unknown: 0, valueCr: 0,
            knownValues: 0, total: 0, types: new Set()
          }));
          pitState.total += 1;
          const rawType = firstField(r, [
            'transactionType', 'transactionMode', 'modeOfTransaction', 'Mode of Transaction'
          ]);
          const explicitDirection = firstField(r, [
            'acquisitionDisposal', 'acqDisposal', 'acquiredDisposed',
            'transactionDirection', 'buySell', 'Buy/Sell', 'side'
          ]);
          // transactionType may carry direction in some PIT schemas, but cached
          // "Off Market" is a transaction mode and therefore remains neutral.
          const direction = normalizedSide(explicitDirection) || normalizedSide(rawType);
          if (direction === 'BUY') pitState.buy += 1;
          else if (direction === 'SELL') pitState.sell += 1;
          else pitState.unknown += 1;
          if (rawType != null) pitState.types.add(String(rawType));
          const rawValue = num(firstField(r, [
            'value', 'transactionValue', 'valueOfTransaction', 'Value of Transaction'
          ]));
          if (rawValue != null) {
            pitState.valueCr += rawValue / 1e7;
            pitState.knownValues += 1;
          }
          rec.flags.pitDir = pitState.unknown === 0 && pitState.buy > 0 && pitState.sell === 0
            ? 'BUY'
            : pitState.unknown === 0 && pitState.sell > 0 && pitState.buy === 0
              ? 'SELL'
              : pitState.unknown === 0 && pitState.buy > 0 && pitState.sell > 0
                ? 'MIXED'
                : null;
          rec.flags.pitType = pitState.types.size === 1
            ? Array.from(pitState.types)[0]
            : pitState.types.size > 1 ? 'Mixed' : null;
          rec.flags.pitValueCr = pitState.knownValues ? +pitState.valueCr.toFixed(4) : null;
          rec.flags.pitValueComplete = pitState.knownValues === pitState.total;
          addSourceKey(rec.flags._src, key);
          touchSource(rec, key, row_no);
        }
      }
    });

    registerScreenerExtractor('nse_oi_spurts', {
      family: 'fo', label: 'NSE OI Spurts',
      extract({ records, table, key, row_no }) {
        for (const r of records) {
          const symbol = pickSymbol(r);
          if (!symbol || INDEX_UNDERLYINGS.has(symbol)) continue;
          const rec = ensureRec(table, symbol);
          const state = foState(rec);
          const latestOI = num(r.latestOI);
          if (latestOI != null && (state.futSummaryOI == null || latestOI > state.futSummaryOI)) {
            state.futSummaryOI = latestOI;
          }
          updateOiChange(rec, 'fut', oiPctFromRow(r));
          addSourceKey(rec.fo._src, key);
          touchSource(rec, key, row_no);
          writePrice(rec, key, row_no, { ltp: num(r.underlyingValue) }, 60);
          refreshFoOI(rec);
        }
      }
    });

    registerScreenerExtractor('nse_oi_spurts_contracts', {
      family: 'fo', label: 'NSE OI Spurt Contracts',
      extract({ item, records, table, key, row_no }) {
        for (const r of records) {
          const symbol = pickSymbol(r);
          const instrument = String(firstField(r, ['instrumentType', 'instrument']) || '').toUpperCase();
          if (!symbol || INDEX_UNDERLYINGS.has(symbol) || instrument.includes('IDX')) continue;
          const rec = ensureRec(table, symbol);
          applyFoContract(rec, key, row_no, r, item, instrument.includes('OPT') ? 'opt' : 'fut');
          writePrice(rec, key, row_no, { ltp: num(r.underlyingValue) }, 60);
        }
      }
    });

    registerScreenerExtractor('nse_slb', {
      family: 'risk', label: 'NSE SLB',
      extract({ records, table, key, row_no }) {
        for (const r of records) {
          const symbol = pickSymbol(r);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          rec.flags.slb = true;
          touchSource(rec, key, row_no);
        }
      }
    });

    registerScreenerExtractor('nse_fo_bhavcopy', {
      family: 'fo', label: 'NSE F&O Bhavcopy',
      extract({ item, records, table, key, row_no }) {
        for (const r of records) {
          const symbol = pickSymbol(r);
          const instrument = String(firstField(r, ['Inst Type', 'instrumentType']) || '').toUpperCase();
          if (!symbol || INDEX_UNDERLYINGS.has(symbol) || instrument.includes('ID')) continue;
          const rec = ensureRec(table, symbol);
          applyFoContract(rec, key, row_no, r, item, instrument.includes('O') ? 'opt' : 'fut');
          writePrice(rec, key, row_no, { ltp: num(r.UndrlygPric) }, 60);
        }
      }
    });

    function stockOptionExtract({ item, records, table, key, row_no }) {
      for (const r of records) {
        const symbol = pickSymbol(r);
        if (!symbol || INDEX_UNDERLYINGS.has(symbol)) continue;
        const rec = ensureRec(table, symbol);
        applyFoContract(rec, key, row_no, r, item, 'opt');
        writePrice(rec, key, row_no, { ltp: num(r.underlyingValue) }, 60);
      }
    }

    registerScreenerExtractor('nse_live_equity_derivatives_stock_opt', {
      family: 'fo', label: 'NSE Stock Options Live', extract: stockOptionExtract
    });
    registerScreenerExtractor('nse_option_chain_equity', {
      family: 'fo', label: 'NSE Equity Option Chain', extract: stockOptionExtract
    });
  }

  // Phase-1 from 30-link pack: ban / delivery / short / cash pre-open (B/C informational)
  function registerPhase1ThirtyPackExtractors() {
    registerScreenerExtractor('nse_fno_ban', {
      family: 'risk', label: 'NSE F&O Ban',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          const symbol = pickSymbol(row) || canonSymbol(row.symbol || row.Symbol);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          rec.risk.fnoBan = true;
          rec.risk.fnoBanReason = row.reason || row.banStatus || 'BANNED';
          addSourceKey(rec.risk._src, key);
          touchSource(rec, key, row_no);
        }
      }
    });

    registerScreenerExtractor('nse_mto_delivery', {
      family: 'volume', label: 'NSE MTO Delivery %',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          if (row.series && String(row.series).toUpperCase() !== 'EQ') continue;
          const symbol = pickSymbol(row) || canonSymbol(row.symbol);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          const pct = num(row.delivery_pct ?? row.deliveryPct ?? row.pct);
          if (pct != null) {
            rec.volume.deliveryPct = pct;
            rec.volume.deliverableQty = num(row.deliverable_qty ?? row.deliverableQty);
            rec.volume.qtyTraded = num(row.qty_traded ?? row.qtyTraded);
          }
          if (!Array.isArray(rec.volume._src)) rec.volume._src = [];
          addSourceKey(rec.volume._src, key);
          touchSource(rec, key, row_no);
        }
      }
    });

    registerScreenerExtractor('nse_short_selling', {
      family: 'risk', label: 'NSE Short Selling',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          const symbol = pickSymbol(row) || canonSymbol(row.symbol);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          const qty = num(row.short_qty ?? row.shortQty);
          if (qty != null) {
            rec.risk.shortQty = (rec.risk.shortQty || 0) + qty;
            rec.risk.shortSelling = true;
          }
          addSourceKey(rec.risk._src, key);
          touchSource(rec, key, row_no);
        }
      }
    });

    registerScreenerExtractor('nse_preopen_cash', {
      family: 'price', label: 'NSE Cash Pre-Open IEP',
      extract({ records, table, key, row_no, helpers }) {
        const { writePrice } = helpers || {};
        for (const row of records) {
          const symbol = pickSymbol(row) || canonSymbol(row.symbol);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          const iep = num(row.iep ?? row.IEP ?? row.ltp);
          const pct = num(row.pct_change ?? row.pChange ?? row.perChange);
          const prev = num(row.prev_close ?? row.prevClose);
          if (writePrice) {
            writePrice(rec, key, row_no, {
              ltp: iep,
              pctChange: pct,
              prevClose: prev,
              gapPercent: (iep != null && prev != null && prev > 0)
                ? ((iep - prev) / prev) * 100
                : null
            }, 40);
          } else {
            if (iep != null) rec.price.ltp = rec.price.ltp ?? iep;
            if (pct != null) rec.price.pctChange = rec.price.pctChange ?? pct;
          }
          rec.price.iep = iep;
          touchSource(rec, key, row_no);
        }
      }
    });

    registerScreenerExtractor('bse_fo_bhavcopy', {
      family: 'fo', label: 'BSE FO Bhavcopy',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          const symbol = pickSymbol(row) || canonSymbol(row.TckrSymb || row.symbol);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          rec.fo.bseFoSeen = true;
          const oi = num(row.OpnIntrst ?? row.openInterest);
          if (oi != null) rec.fo.optOI = rec.fo.optOI == null ? oi : Math.max(rec.fo.optOI, oi);
          if (!Array.isArray(rec.fo._src)) rec.fo._src = [];
          addSourceKey(rec.fo._src, key);
          touchSource(rec, key, row_no);
        }
      }
    });

    // Phase-2 30-pack (mostly informational / macro; insider flags stocks)
    registerScreenerExtractor('bse_insider_trading', {
      family: 'risk', label: 'BSE Insider Trading',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          const symbol = pickSymbol(row) || canonSymbol(row.symbol || row.Fld_ScripCode || row.scripcode);
          if (!symbol || /^\d+$/.test(symbol)) continue; // skip pure scrip codes without symbol
          const rec = ensureRec(table, symbol);
          rec.flags.insider = true;
          rec.flags.insiderBse = true;
          if (!Array.isArray(rec.flags._src)) rec.flags._src = [];
          addSourceKey(rec.flags._src, key);
          touchSource(rec, key, row_no);
        }
      }
    });

    registerScreenerExtractor('nse_option_chain_nifty', {
      family: 'fo', label: 'Nifty Option Chain',
      extract({ records, table, key, row_no }) {
        // Index-level context only — attach to synthetic NIFTY row if present
        const rec = ensureRec(table, 'NIFTY');
        rec.fo.indexOptionChain = true;
        rec.fo.indexOptionStrikes = (records || []).length;
        if (!Array.isArray(rec.fo._src)) rec.fo._src = [];
        addSourceKey(rec.fo._src, key);
        touchSource(rec, key, row_no);
      }
    });

    registerScreenerExtractor('nse_option_chain_banknifty', {
      family: 'fo', label: 'BankNifty Option Chain',
      extract({ records, table, key, row_no }) {
        const rec = ensureRec(table, 'BANKNIFTY');
        rec.fo.indexOptionChain = true;
        rec.fo.indexOptionStrikes = (records || []).length;
        if (!Array.isArray(rec.fo._src)) rec.fo._src = [];
        addSourceKey(rec.fo._src, key);
        touchSource(rec, key, row_no);
      }
    });

    // Macro keys intentionally have no equity-universe extractors (no fake stock LTP).
    registerScreenerExtractor('lbma_gold_silver_fix', {
      family: 'custom', label: 'LBMA Fix (macro)',
      extract() { /* macro context only — no stock merge */ }
    });
    registerScreenerExtractor('eia_natgas_storage', {
      family: 'custom', label: 'EIA NatGas (macro)',
      extract() { /* macro context only */ }
    });
    registerScreenerExtractor('usda_wasde_cornell', {
      family: 'custom', label: 'WASDE Index (macro)',
      extract() { /* macro context only */ }
    });
    registerScreenerExtractor('nse_fii_derivatives_stats', {
      family: 'fo', label: 'FII Derivatives Stats',
      extract() { /* market-level flow; no per-stock LTP */ }
    });
    registerScreenerExtractor('nse_index_option_chain_v3', {
      family: 'fo', label: 'Nifty OC v3',
      extract({ records, table, key, row_no }) {
        const rec = ensureRec(table, 'NIFTY');
        rec.fo.indexOptionChainV3 = true;
        rec.fo.indexOptionStrikes = (records || []).length;
        if (!Array.isArray(rec.fo._src)) rec.fo._src = [];
        addSourceKey(rec.fo._src, key);
        touchSource(rec, key, row_no);
      }
    });
    registerScreenerExtractor('rbi_fbil_usdinr', {
      family: 'custom', label: 'USDINR (macro)',
      extract() { /* FX macro only */ }
    });
    registerScreenerExtractor('cdsl_fpi_fortnightly', {
      family: 'custom', label: 'CDSL FPI (macro)',
      extract() { /* FPI sector context only */ }
    });
    registerScreenerExtractor('dgcis_trade_data', {
      family: 'custom', label: 'DGCIS Imports (macro)',
      extract() { /* trade-flow context only */ }
    });
    registerScreenerExtractor('yahoo_cme_proxy', {
      family: 'custom', label: 'Yahoo CME Proxy',
      extract() { /* futures proxy context */ }
    });
    registerScreenerExtractor('yahoo_lme_proxy', {
      family: 'custom', label: 'Yahoo LME Proxy',
      extract() { /* futures proxy context */ }
    });
    registerScreenerExtractor('mcx_market_watch', {
      family: 'custom', label: 'MCX Market Watch',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          const symbol = pickSymbol(row) || canonSymbol(row.symbol || row.Symbol || row.Commodity);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          rec.fo.mcxWatch = true;
          const ltp = num(row.LTP || row.LastPrice || row.close || row.Close);
          if (ltp != null && rec.price.ltp == null) rec.price.ltp = ltp;
          touchSource(rec, key, row_no);
        }
      }
    });
    registerScreenerExtractor('mcx_option_chain', {
      family: 'fo', label: 'MCX Option Chain',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          const symbol = pickSymbol(row) || canonSymbol(row.symbol || row.Commodity || 'GOLD');
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          rec.fo.mcxOptionChain = true;
          touchSource(rec, key, row_no);
        }
      }
    });
    registerScreenerExtractor('mcx_top_participants', {
      family: 'custom', label: 'MCX Top Participants',
      extract() { /* commodity positioning context */ }
    });
    registerScreenerExtractor('mcx_warehouse_stocks', {
      family: 'custom', label: 'MCX Warehouse',
      extract() { /* warehouse context */ }
    });
    registerScreenerExtractor('mcx_delivery_reports', {
      family: 'custom', label: 'MCX Delivery',
      extract() { /* delivery context */ }
    });
    registerScreenerExtractor('ncdex_bhavcopy', {
      family: 'custom', label: 'NCDEX',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          const symbol = pickSymbol(row) || canonSymbol(row.symbol || row.name || row.c0);
          if (!symbol) continue;
          ensureRec(table, symbol);
          touchSource(ensureRec(table, symbol), key, row_no);
        }
      }
    });
    registerScreenerExtractor('amfi_portfolio_disclosure', {
      family: 'custom', label: 'AMFI Portfolio Dir',
      extract() { /* AMC link directory */ }
    });
    registerScreenerExtractor('nse_bulk_deals_today_csv', {
      family: 'deals', label: 'NSE Bulk Deals CSV',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          const symbol = pickSymbol(row) || canonSymbol(row.Symbol || row.symbol);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          rec.deals.bulkSeen = true;
          touchSource(rec, key, row_no);
        }
      }
    });
    registerScreenerExtractor('nse_bulk_deal_symbol', {
      family: 'deals', label: 'NSE Bulk Deal Symbol',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          const symbol = pickSymbol(row) || canonSymbol(row.symbol);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          rec.deals.bulkSeen = true;
          touchSource(rec, key, row_no);
        }
      }
    });
    registerScreenerExtractor('nse_quote_equity_trade_info', {
      family: 'volume', label: 'NSE Trade Info Delivery',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          const symbol = pickSymbol(row) || canonSymbol(row.symbol);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          const pct = num(row.deliveryToTradedQuantity || row.dp_deliveryToTradedQuantity || row.delivery_pct);
          if (pct != null) rec.volume.deliveryPct = pct;
          touchSource(rec, key, row_no);
        }
      }
    });
  }

  function registerGapFeedExtractors() {
    registerScreenerExtractor('nse_trade_to_trade', {
      family: 'risk', label: 'NSE Trade-for-Trade',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          const symbol = pickSymbol(row);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          rec.risk.t2t = true;
          rec.risk.t2tSeries = String(row.series || '').toUpperCase() || null;
          rec.risk.intradayEligible = false;
          addSourceKey(rec.risk._src, key);
          touchSource(rec, key, row_no);
        }
      }
    });

    registerScreenerExtractor('kite_derivatives_contract_master', {
      family: 'fo', label: 'Derivative Lot-Size Reference',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          // The equity screener consumes NFO underlyings only. BFO/MCX remain
          // visible in the inventory drawer and never widen the stock universe.
          if (String(row.exchange || '').toUpperCase() !== 'NFO') continue;
          const symbol = pickSymbol(row);
          if (!symbol || INDEX_UNDERLYINGS.has(symbol)) continue;
          const lot = num(row.nearestLotSize);
          if (lot == null || lot <= 0) continue;
          const rec = ensureRec(table, symbol);
          rec.fo.nearestLotSize = lot;
          rec.fo.nearestLotExpiry = isoDate(row.nearestExpiry);
          rec.fo.lotSchedules = Array.isArray(row.lotSchedules)
            ? row.lotSchedules.filter(item => num(item && item.lotSize) > 0).map(item => ({
                expiry: isoDate(item.expiry),
                instrumentType: item.instrumentType || null,
                lotSize: num(item.lotSize)
              }))
            : [];
          addSourceKey(rec.fo._src, key);
          touchSource(rec, key, row_no);
        }
      }
    });

    registerScreenerExtractor('nse_board_meetings', {
      family: 'events', label: 'NSE Board Meetings',
      extract({ item, records, table, key, row_no }) {
        const snapshotDate = itemSnapshotDate(item);
        for (const row of records) {
          const symbol = pickSymbol(row);
          const meetingDate = isoDate(row.meetingDate);
          if (!symbol || !meetingDate) continue;
          const rec = ensureRec(table, symbol);
          const days = deterministicDaysBetween(snapshotDate, meetingDate);
          const rank = days == null ? Number.MAX_SAFE_INTEGER : days >= 0 ? days : 100000 + Math.abs(days);
          const currentDays = rec.flags.daysToMeeting;
          const currentRank = currentDays == null
            ? Number.MAX_SAFE_INTEGER
            : currentDays >= 0 ? currentDays : 100000 + Math.abs(currentDays);
          if (!rec.flags.boardMeeting || rank < currentRank) {
            rec.flags.boardMeeting = true;
            rec.flags.boardMeetingDate = meetingDate;
            rec.flags.boardMeetingPurpose = row.purpose || null;
            rec.flags.daysToMeeting = days;
            rec.flags.resultsEvent = !!row.resultsEvent;
            rec.flags.boardMeetingAttachment = row.attachment || null;
          }
          addSourceKey(rec.flags._src, key);
          touchSource(rec, key, row_no);
        }
      }
    });

    const mostActiveExtract = (kind) => ({ records, table, key, row_no }) => {
      for (const row of records) {
        const symbol = pickSymbol(row);
        if (!symbol || INDEX_UNDERLYINGS.has(symbol)) continue;
        const rec = ensureRec(table, symbol);
        const activity = rec.fo.tradedContractActivity;
        const traded = Math.max(0, num(row.contractsTraded) || 0);
        const turnover = Math.max(0, num(row.turnover) || 0);
        if (kind === 'futures') {
          rec.fo.mostActiveFutures = true;
          activity.futuresRows += 1;
          activity.futuresContractsTraded += traded;
          activity.futuresTurnover += turnover;
        } else {
          rec.fo.mostActiveOptions = true;
          activity.optionsRows += 1;
          activity.optionsContractsTraded += traded;
          activity.optionsTurnover += turnover;
        }
        // In particular, option premium movement is never written to price.*.
        addSourceKey(rec.fo._src, key);
        touchSource(rec, key, row_no);
      }
    };
    registerScreenerExtractor('nse_most_active_futures', {
      family: 'fo', label: 'Most-Active Futures', extract: mostActiveExtract('futures')
    });
    registerScreenerExtractor('nse_most_active_options', {
      family: 'fo', label: 'Most-Active Options', extract: mostActiveExtract('options')
    });

    registerScreenerExtractor('nse_ipo_issue_calendar', {
      family: 'events', label: 'NSE IPO Calendar',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          const symbol = pickSymbol(row);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          rec.flags.ipo = true;
          rec.flags.ipoStatus = row.status || null;
          rec.flags.ipoStartDate = isoDate(row.issueStartDate);
          rec.flags.ipoEndDate = isoDate(row.issueEndDate);
          addSourceKey(rec.flags._src, key);
          touchSource(rec, key, row_no);
        }
      }
    });

    registerScreenerExtractor('nse_pr_market_snapshot', {
      family: 'market_context', label: 'NSE PR Market Snapshot',
      extract({ records, table, key, row_no }) {
        for (const row of records) {
          const section = String(row.section || '').toLowerCase();
          // Top gainers/losers are derived from the same bhavcopy and must not
          // duplicate A-family price or score terms.
          if (section === 'top_gainers' || section === 'top_losers') continue;
          const symbol = pickSymbol(row);
          if (!symbol) continue;
          const rec = ensureRec(table, symbol);
          if (section === 'mcap') {
            const marketCapCr = num(row.marketCapCr);
            if (marketCapCr != null && marketCapCr > 0) rec.market.marketCapCr = marketCapCr;
            addSourceKey(rec.market._src, key);
          } else if (section === 'wk52') {
            rec.flags.wk52Event = row.event || null;
            addSourceKey(rec.flags._src, key);
          } else if (section === 'corp_actions') {
            rec.flags.corpAction = true;
            rec.flags.corpActionDate = isoDate(row.exDate || row.recordDate);
            rec.flags.corpActionPurpose = row.purpose || null;
            if (rec.flags.corpActionDetails.length < 10) {
              rec.flags.corpActionDetails.push({
                exDate: isoDate(row.exDate),
                recordDate: isoDate(row.recordDate),
                purpose: row.purpose || null
              });
            }
            addSourceKey(rec.flags._src, key);
          } else {
            continue;
          }
          touchSource(rec, key, row_no);
        }
      }
    });
  }

  registerAExtractors();
  registerBCExtractors();
  registerPhase1ThirtyPackExtractors();
  registerGapFeedExtractors();

  // ═══════════════════════════════════════════════════════════════════════════
  // SCORE v1.3: A-family price/volume evidence only.
  // B/C deals, disclosure, surveillance and derivatives fields are deliberately
  // informational until direction and weighting are validated by backtesting.
  // ═══════════════════════════════════════════════════════════════════════════
  function computeScreenerScore(rec) {
    const parts = [];
    let s = 0;
    if (rec.price.pctChange != null) {
      const v = clamp(rec.price.pctChange, -5, 5);
      s += v;
      parts.push({ label: '%chg', value: v });
    }
    if (rec.price.gapPercent != null) {
      const v = clamp(rec.price.gapPercent, -3, 3) * 0.5;
      s += v;
      parts.push({ label: 'gap', value: v });
    }
    if (rec.volume.spikeX != null && rec.volume.spikeX > 1) {
      const v = Math.min(Math.log2(rec.volume.spikeX), 3);
      s += v;
      parts.push({ label: 'vol×', value: v });
    }
    return { score: parts.length ? +s.toFixed(2) : null, parts };
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // BUILD TABLE
  // ═══════════════════════════════════════════════════════════════════════════
  let _cache = null; // { table: Map, universe, builtAt, inventoryRef }

  function buildSymbolTable(inventory, opts = {}) {
    const force = !!opts.force;
    if (_cache && _cache.inventoryRef === inventory && !force) return _cache;

    const t0 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    const byKey = indexBySourceKey(inventory);
    const table = new Map();
    const diagnostics = [];

    for (const [key, def] of EXTRACTORS) {
      if (!def.enabled) continue;
      const item = byKey.get(key);
      if (!item) {
        diagnostics.push({ key, status: 'absent' });
        continue;
      }
      const records = getRecords(item);
      if (!records.length) {
        diagnostics.push({ key, status: 'empty_sample' });
        continue;
      }
      try {
        def.extract({
          item,
          records,
          table,
          key,
          row_no: item.row_no,
          helpers: { num, pickSymbol, canonSymbol, firstField, ensureRec, touchSource, writePrice, writeVolume }
        });
        diagnostics.push({ key, status: 'ok', rows: records.length, family: def.family });
      } catch (err) {
        console.warn('[Screener] extractor failed', key, err);
        diagnostics.push({ key, status: 'error', error: String(err && err.message || err) });
      }
    }

    const universe = buildUniverseSets(inventory);
    for (const [sym, rec] of table) {
      rec.inN50 = universe.n50.has(sym);
      rec.inN100 = universe.n100.has(sym);
      rec.inN500 = universe.n500.has(sym);
      const sc = computeScreenerScore(rec);
      rec.score = sc.score;
      rec.scoreParts = sc.parts;
    }
    universe.all = new Set(table.keys());

    const t1 = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    _cache = {
      table,
      universe,
      diagnostics,
      builtAt: Date.now(),
      ms: Math.round(t1 - t0),
      inventoryRef: inventory,
      version: CONFIG.version,
      scorePolicy: CONFIG.scorePolicy
    };
    console.info(
      `[Screener] v${CONFIG.version} symbols=${table.size} universe n50=${universe.meta.n50} n500=${universe.meta.n500} build=${_cache.ms}ms extractors=${diagnostics.filter(d => d.status === 'ok').length}`
    );
    return _cache;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // FILTER + SORT (in-memory, fast)
  // ═══════════════════════════════════════════════════════════════════════════
  function filterTable(cache, state) {
    if (!cache) return [];
    const uni = state.universe || CONFIG.defaultUniverse;
    const q = (state.search || '').trim().toUpperCase();
    const minScore = state.minScore != null ? Number(state.minScore) : null;
    const preset = state.preset || 'all';

    let setFilter = null;
    if (uni === 'n50') setFilter = cache.universe.n50;
    else if (uni === 'n100') setFilter = cache.universe.n100;
    else if (uni === 'n500') setFilter = cache.universe.n500;

    const out = [];
    for (const [sym, rec] of cache.table) {
      if (setFilter && !setFilter.has(sym)) continue;
      // Prefer rows with some market signal for default view
      if (preset === 'momentum' && rec.price.pctChange == null && rec.price.gapPercent == null) continue;
      if (preset === 'has_price' && rec.price.ltp == null && rec.price.pctChange == null) continue;
      if (preset === 'risk_only' && !(
        rec.risk.t2t || rec.risk.asm || rec.risk.gsm || rec.risk.pledgePct != null
      )) continue;
      if (minScore != null && Number.isFinite(minScore) && (rec.score == null || rec.score < minScore)) continue;
      if (q && !sym.includes(q)) continue;
      out.push(rec);
    }

    const sortKey = state.sortKey || 'score';
    const sortDir = state.sortDir === 'asc' ? 1 : -1;
    out.sort((a, b) => {
      const av = sortValue(a, sortKey);
      const bv = sortValue(b, sortKey);
      if (av == null && bv == null) return a.symbol.localeCompare(b.symbol);
      if (av == null) return 1;
      if (bv == null) return -1;
      if (av < bv) return -1 * sortDir;
      if (av > bv) return 1 * sortDir;
      return a.symbol.localeCompare(b.symbol);
    });
    return out;
  }

  function sortValue(rec, key) {
    switch (key) {
      case 'symbol': return rec.symbol;
      case 'ltp': return rec.price.ltp;
      case 'pct': return rec.price.pctChange;
      case 'gap': return rec.price.gapPercent;
      case 'vol': return rec.volume.spikeX ?? rec.volume.qty;
      case 'score': return rec.score;
      case 'src': return rec.sources.length;
      default: return rec.score;
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // UI
  // ═══════════════════════════════════════════════════════════════════════════
  let _uiState = {
    universe: CONFIG.defaultUniverse,
    search: '',
    sortKey: 'score',
    sortDir: 'desc',
    minScore: null,
    preset: 'has_price'
  };

  function fmtNum(v, digits) {
    if (v == null || !Number.isFinite(v)) return '—';
    return Number(v).toFixed(digits != null ? digits : 2);
  }

  function fmtPct(v) {
    if (v == null || !Number.isFinite(v)) return '—';
    const sign = v > 0 ? '+' : '';
    const cls = v > 0 ? 'scr-pos' : v < 0 ? 'scr-neg' : '';
    return `<span class="${cls}">${sign}${v.toFixed(2)}%</span>`;
  }

  function fmtCr(v, signed) {
    if (v == null || !Number.isFinite(v)) return 'unknown';
    const sign = signed && v > 0 ? '+' : '';
    return `${sign}${v.toFixed(2)} Cr`;
  }

  function informationalEvidenceHtml(rec) {
    const chips = [];
    const buys = rec.deals.bulkBuy + rec.deals.blockBuy;
    const sells = rec.deals.bulkSell + rec.deals.blockSell;
    if (buys || sells) {
      const value = rec.deals.valueComplete
        ? `buy ${fmtCr(rec.deals.buyValueCr)} / sell ${fmtCr(rec.deals.sellValueCr)} / net ${fmtCr(rec.deals.netDealCr, true)}`
        : rec.deals.largeDealCr != null
          ? `known buy ${fmtCr(rec.deals.buyValueCr)} / known sell ${fmtCr(rec.deals.sellValueCr)} / net withheld`
          : 'value unknown';
      const completeness = rec.deals.valueComplete === false ? ' - partial values' : '';
      chips.push(`Deals B${buys}/S${sells} - ${value}${completeness}`);
    }
    if (rec.flags.pit) {
      const mode = rec.flags.pitType || 'mode unknown';
      const direction = rec.flags.pitDir || 'direction unknown';
      const partial = rec.flags.pitValueComplete === false ? ' (partial)' : '';
      const value = rec.flags.pitValueCr == null ? '' : ` - gross ${fmtCr(rec.flags.pitValueCr)}${partial}`;
      chips.push(`PIT ${mode} - ${direction}${value}`);
    }
    if (rec.risk.asm) {
      const stage = rec.risk.asmStage == null ? 'stage unknown' : `stage ${rec.risk.asmStage}`;
      const framework = rec.risk.asmFramework ? `${rec.risk.asmFramework} ` : '';
      chips.push(`ASM ${framework}${stage}`);
    }
    if (rec.risk.gsm) {
      const stage = rec.risk.gsmStage == null ? 'stage unknown' : `stage ${rec.risk.gsmStage}`;
      const indicator = rec.risk.gsmIndicator && rec.risk.gsmIndicator !== rec.risk.gsmStage
        ? ` - indicator ${rec.risk.gsmIndicator}` : '';
      chips.push(`GSM ${stage}${indicator}`);
    }
    if (rec.risk.t2t) {
      chips.push(`Delivery only • no intraday${rec.risk.t2tSeries ? ` • ${rec.risk.t2tSeries}` : ''}`);
    }
    if (rec.flags.boardMeeting) {
      const days = rec.flags.daysToMeeting == null ? '' : ` • ${rec.flags.daysToMeeting} day(s)`;
      const purpose = rec.flags.boardMeetingPurpose ? ` • ${rec.flags.boardMeetingPurpose}` : '';
      chips.push(`Board meeting ${rec.flags.boardMeetingDate || 'date unknown'}${days}${purpose}`);
    }
    if (rec.flags.ipo) {
      chips.push(`IPO ${rec.flags.ipoStatus || 'status unknown'} • ${rec.flags.ipoStartDate || 'start unknown'} to ${rec.flags.ipoEndDate || 'end unknown'}`);
    }
    if (rec.flags.wk52Event) chips.push(`52-week event ${rec.flags.wk52Event}`);
    if (rec.flags.corpAction) {
      chips.push(`Corporate action ${rec.flags.corpActionDate || 'date unknown'} • ${rec.flags.corpActionPurpose || 'purpose unknown'}`);
    }
    if (rec.fo.oiPctChg != null) {
      chips.push(`OI ${rec.fo.oiPctChg > 0 ? '+' : ''}${rec.fo.oiPctChg.toFixed(2)}% ${rec.fo.oiDirection || ''}`.trim());
    }
    if (rec.fo.contracts) chips.push(`F&O contracts ${rec.fo.contracts}`);
    if (rec.fo.nearestLotSize) chips.push(`Nearest lot ${rec.fo.nearestLotSize} • ${rec.fo.nearestLotExpiry || 'expiry unknown'}`);
    if (rec.fo.mostActiveFutures) {
      chips.push(`Most-active futures • ${rec.fo.tradedContractActivity.futuresContractsTraded} contracts traded`);
    }
    if (rec.fo.mostActiveOptions) {
      chips.push(`Most-active options • ${rec.fo.tradedContractActivity.optionsContractsTraded} contracts traded`);
    }
    if (rec.market.marketCapCr != null) chips.push(`Market cap ${fmtCr(rec.market.marketCapCr)}`);
    if (rec.flags.slb) chips.push('SLB present');
    return chips.length
      ? chips.map(value => `<span class="scr-chip">${esc(value)}</span>`).join(' ')
      : '<span class="scr-muted">No B/C evidence for this symbol</span>';
  }

  function showScreenerBreakdown(symbol) {
    const cache = _cache;
    if (!cache) return;
    const rec = cache.table.get(String(symbol || '').toUpperCase());
    if (!rec) return;

    const existing = document.getElementById('screener-modal');
    if (existing) existing.remove();

    const partsHtml = (rec.scoreParts || []).length
      ? rec.scoreParts.map(p =>
        `<span class="scr-chip">${esc(p.label)}: ${fmtNum(p.value, 2)}</span>`
      ).join(' ')
      : '<span class="scr-muted">No A-family score components</span>';
    const informationalHtml = informationalEvidenceHtml(rec);

    const inv = (cache.inventoryRef) ||
      (typeof window !== 'undefined' && window.inventory) || [];
    const srcRows = (rec.sources || []).map(s => {
      const item = inv.find(i => i.row_no === s.row_no);
      const title = item ? item.title : s.key;
      return `<tr>
        <td class="scr-mono">#${s.row_no}</td>
        <td>${esc(title)}<div class="scr-muted scr-mono">${esc(s.key)}</div></td>
        <td style="text-align:right">
          <button type="button" class="scr-btn" onclick="(function(){var m=document.getElementById('screener-modal');if(m)m.remove();if(typeof openDrawer==='function')openDrawer(${s.row_no});})()">Details</button>
        </td>
      </tr>`;
    }).join('') || '<tr><td colspan="3" class="scr-muted">No sources</td></tr>';

    const modal = document.createElement('div');
    modal.id = 'screener-modal';
    modal.className = 'scr-modal-backdrop';
    modal.innerHTML = `
      <div class="scr-modal" onclick="event.stopPropagation()">
        <div class="scr-modal-head">
          <div>
            <div class="scr-modal-sym">${esc(rec.symbol)}</div>
            <div class="scr-muted">A-only score ${fmtNum(rec.score, 2)} · ${rec.sources.length} source key(s)
              ${rec.inN50 ? ' · N50' : ''}${rec.inN100 ? ' · N100' : ''}${rec.inN500 ? ' · N500' : ''}
            </div>
          </div>
          <button type="button" class="scr-btn" onclick="document.getElementById('screener-modal').remove()">✕ Close</button>
        </div>
        <div class="scr-modal-body">
          <div class="scr-kv">
            <div><span class="scr-muted">LTP</span><br><strong>${fmtNum(rec.price.ltp, 2)}</strong></div>
            <div><span class="scr-muted">%Chg</span><br><strong>${fmtPct(rec.price.pctChange)}</strong></div>
            <div><span class="scr-muted">Gap%</span><br><strong>${fmtPct(rec.price.gapPercent)}</strong></div>
            <div><span class="scr-muted">Vol×</span><br><strong>${fmtNum(rec.volume.spikeX, 2)}</strong></div>
          </div>
          <div class="scr-section-title" style="margin-top:0.75rem">A-family score components</div>
          <div style="margin:0.5rem 0 0.75rem">${partsHtml}</div>
          <div class="scr-section-title">B/C informational evidence (not scored)</div>
          <div style="margin:0.5rem 0 0.75rem">${informationalHtml}</div>
          <div class="scr-section-title">Contributing inventory links</div>
          <table class="scr-table scr-table-compact"><thead><tr>
            <th>Row</th><th>Link</th><th></th>
          </tr></thead><tbody>${srcRows}</tbody></table>
          <p class="scr-foot">Cached samples only. No greeks. Not financial advice.</p>
        </div>
      </div>`;
    modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
    document.body.appendChild(modal);
  }

  function renderScreenerPanel(inventory) {
    const host = document.getElementById('screener-panel');
    if (!host) return null;

    // Use hooked build so onBuild / think-engine listeners see the cache
    const cache = (typeof buildSymbolTableWithHooks === 'function')
      ? buildSymbolTableWithHooks(inventory)
      : buildSymbolTable(inventory);
    const rows = filterTable(cache, _uiState);
    const show = rows.slice(0, CONFIG.tableLimit);
    const uniMeta = cache.universe.meta;

    const uniOpts = [
      ['n50', `Nifty 50 (${uniMeta.n50})`],
      ['n100', `Nifty 100 approx (${uniMeta.n100})`],
      ['n500', uniMeta.label500],
      ['all', `All extracted (${cache.table.size})`]
    ].map(([v, lab]) =>
      `<option value="${v}" ${_uiState.universe === v ? 'selected' : ''}>${esc(lab)}</option>`
    ).join('');

    const th = (key, label) => {
      const active = _uiState.sortKey === key;
      const arrow = active ? (_uiState.sortDir === 'asc' ? ' ▲' : ' ▼') : '';
      return `<th class="scr-th" data-sort="${key}" style="cursor:pointer">${esc(label)}${arrow}</th>`;
    };

    const body = show.map(rec => {
      const jsSym = JSON.stringify(rec.symbol);
      return `<tr class="scr-tr" onclick='showScreenerBreakdown(${jsSym})'>
        <td class="scr-mono scr-sym">${esc(rec.symbol)}</td>
        <td class="scr-num">${fmtNum(rec.price.ltp, 2)}</td>
        <td class="scr-num">${fmtPct(rec.price.pctChange)}</td>
        <td class="scr-num">${fmtPct(rec.price.gapPercent)}</td>
        <td class="scr-num">${fmtNum(rec.volume.spikeX, 2)}</td>
        <td class="scr-num">${fmtNum(rec.score, 2)}</td>
        <td class="scr-num scr-muted">${rec.sources.length}</td>
      </tr>`;
    }).join('') || `<tr><td colspan="7" class="scr-muted" style="text-align:center;padding:1rem">No rows for this universe/filter</td></tr>`;

    host.innerHTML = `
      <div class="scr-panel">
        <div class="scr-head">
          <div>
            <div class="scr-title">Screener <span class="scr-ver">v${CONFIG.version}</span></div>
            <div class="scr-sub">A-only score · B/C evidence informational · Nifty gate · freshness shown above · not consensus voting</div>
          </div>
          <div class="scr-meta">${cache.table.size} symbols · build ${cache.ms}ms · show ${show.length}${rows.length > show.length ? ` / ${rows.length}` : ''}</div>
        </div>
        <div class="scr-toolbar">
          <label class="scr-label">Universe
            <select id="scr-universe" class="scr-select">${uniOpts}</select>
          </label>
          <label class="scr-label">Preset
            <select id="scr-preset" class="scr-select">
              <option value="has_price" ${_uiState.preset === 'has_price' ? 'selected' : ''}>Has price signal</option>
              <option value="all" ${_uiState.preset === 'all' ? 'selected' : ''}>All extracted</option>
              <option value="momentum" ${_uiState.preset === 'momentum' ? 'selected' : ''}>Momentum (%/gap)</option>
              <option value="risk_only" ${_uiState.preset === 'risk_only' ? 'selected' : ''}>Risk flags (T2T / ASM / GSM / pledge)</option>
            </select>
          </label>
          <label class="scr-label">Search
            <input id="scr-search" class="scr-input" type="search" placeholder="Symbol…" value="${esc(_uiState.search)}" />
          </label>
        </div>
        <div class="scr-table-wrap">
          <table class="scr-table" id="scr-table">
            <thead><tr>
              ${th('symbol', 'Symbol')}
              ${th('ltp', 'LTP')}
              ${th('pct', '%Chg')}
              ${th('gap', 'Gap%')}
              ${th('vol', 'Vol×')}
              ${th('score', 'Score')}
              ${th('src', 'Src')}
            </tr></thead>
            <tbody>${body}</tbody>
          </table>
        </div>
        <div class="scr-foot">Cached samples only · no greeks · click row for evidence · B/C fields never change the v1.3 score</div>
      </div>`;

    // Bind controls once per render
    const uniEl = document.getElementById('scr-universe');
    const preEl = document.getElementById('scr-preset');
    const searchEl = document.getElementById('scr-search');
    if (uniEl) uniEl.onchange = () => { _uiState.universe = uniEl.value; renderScreenerPanel(inventory); };
    if (preEl) preEl.onchange = () => { _uiState.preset = preEl.value; renderScreenerPanel(inventory); };
    if (searchEl) {
      let _searchTimer = null;
      searchEl.oninput = () => {
        _uiState.search = searchEl.value || '';
        clearTimeout(_searchTimer);
        _searchTimer = setTimeout(() => renderScreenerPanel(inventory), CONFIG.searchDebounceMs);
      };
    }
    host.querySelectorAll('.scr-th').forEach(thEl => {
      thEl.onclick = () => {
        const k = thEl.getAttribute('data-sort');
        if (_uiState.sortKey === k) _uiState.sortDir = _uiState.sortDir === 'asc' ? 'desc' : 'asc';
        else { _uiState.sortKey = k; _uiState.sortDir = k === 'symbol' ? 'asc' : 'desc'; }
        renderScreenerPanel(inventory);
      };
    });

    return cache;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // FUTURE HOOKS — think engines, columns, multi-engine registry
  // ═══════════════════════════════════════════════════════════════════════════
  /** @type {Map<string, { build?: Function, render?: Function, describe?: string }>} */
  const ENGINES = new Map();
  ENGINES.set('featureTable', {
    build: buildSymbolTable,
    render: renderScreenerPanel,
    describe: 'A-only score with informational B/C evidence from cached feeds'
  });

  /** @type {Array<{ id: string, label: string, sortKey?: string, render?: Function }>} */
  const COLUMNS = [
    { id: 'symbol', label: 'Symbol', sortKey: 'symbol' },
    { id: 'ltp', label: 'LTP', sortKey: 'ltp' },
    { id: 'pct', label: '%Chg', sortKey: 'pct' },
    { id: 'gap', label: 'Gap%', sortKey: 'gap' },
    { id: 'vol', label: 'Vol×', sortKey: 'vol' },
    { id: 'score', label: 'Score', sortKey: 'score' },
    { id: 'src', label: 'Src', sortKey: 'src' }
  ];

  /** @type {Array<Function>} */
  const _onBuildHooks = [];

  function registerScreenerEngine(name, def) {
    if (!name || !def) throw new Error('[Screener] registerScreenerEngine needs name + def');
    ENGINES.set(name, {
      build: def.build || null,
      render: def.render || null,
      describe: def.describe || name
    });
    return name;
  }

  function registerScreenerColumn(col) {
    if (!col || !col.id || !col.label) throw new Error('[Screener] column needs id + label');
    const i = COLUMNS.findIndex(c => c.id === col.id);
    if (i >= 0) COLUMNS[i] = { ...COLUMNS[i], ...col };
    else COLUMNS.push(col);
    return col.id;
  }

  function onBuild(fn) {
    if (typeof fn === 'function') _onBuildHooks.push(fn);
    return () => {
      const i = _onBuildHooks.indexOf(fn);
      if (i >= 0) _onBuildHooks.splice(i, 1);
    };
  }

  /**
   * Stable snapshot for future think engines / LLM / export.
   * Always real fields only; nulls preserved (no invented greeks).
   */
  function getSnapshot(opts = {}) {
    const cache = _cache;
    if (!cache) return null;
    const state = { ..._uiState, ...(opts.state || {}) };
    const rows = filterTable(cache, state);
    const limit = opts.limit != null ? opts.limit : CONFIG.tableLimit;
    const slim = rows.slice(0, limit).map(rec => ({
      symbol: rec.symbol,
      inN50: rec.inN50,
      inN100: rec.inN100,
      inN500: rec.inN500,
      price: {
        ltp: rec.price.ltp,
        pctChange: rec.price.pctChange,
        gapPercent: rec.price.gapPercent,
        open: rec.price.open,
        high: rec.price.high,
        low: rec.price.low,
        prevClose: rec.price.prevClose
      },
      volume: {
        qty: rec.volume.qty,
        valueCr: rec.volume.valueCr,
        spikeX: rec.volume.spikeX
      },
      boards: { ...rec.boards },
      deals: { ...rec.deals },
      flags: { ...rec.flags },
      risk: { ...rec.risk },
      fo: { ...rec.fo },
      market: { ...rec.market },
      score: rec.score,
      scoreParts: (rec.scoreParts || []).slice(),
      sources: (rec.sources || []).map(s => ({ key: s.key, row_no: s.row_no }))
    }));
    return {
      contract: CONFIG.featureContract.id,
      version: CONFIG.version,
      scorePolicy: {
        id: CONFIG.scorePolicy.id,
        scoredFamilies: CONFIG.scorePolicy.scoredFamilies.slice(),
        informationalFamilies: CONFIG.scorePolicy.informationalFamilies.slice(),
        scoredFields: CONFIG.scorePolicy.scoredFields.slice()
      },
      builtAt: cache.builtAt,
      ms: cache.ms,
      universe: state.universe,
      totalSymbols: cache.table.size,
      filtered: rows.length,
      returned: slim.length,
      diagnostics: cache.diagnostics,
      rows: slim
    };
  }

  // Wrap build to fire hooks only when cache is newly built (not on filter re-render)
  const _buildSymbolTableCore = buildSymbolTable;
  function buildSymbolTableWithHooks(inventory, opts) {
    opts = opts || {};
    const prev = _cache;
    const cache = _buildSymbolTableCore(inventory, opts);
    // Fire only on fresh build (new object or forced), not cached return
    if (cache && !opts.silentHooks && cache !== prev) {
      for (const fn of _onBuildHooks) {
        try { fn(cache, getSnapshot({ limit: 50 })); }
        catch (e) { console.warn('[Screener] onBuild hook error', e); }
      }
    }
    return cache;
  }

  // Public API — future engines / think layer hook here
  return {
    CONFIG,
    NIFTY_50_STATIC,
    NIFTY_NEXT50_STATIC,
    registerScreenerExtractor,
    registerScreenerEngine,
    registerScreenerColumn,
    onBuild,
    getSnapshot,
    buildUniverseSets,
    buildSymbolTable: buildSymbolTableWithHooks,
    filterTable,
    computeScreenerScore,
    renderScreenerPanel,
    showScreenerBreakdown,
    getCache: () => _cache,
    clearCache: () => { _cache = null; },
    getUiState: () => ({ ..._uiState }),
    setUiState: (patch) => { Object.assign(_uiState, patch || {}); },
    listExtractors: () => Array.from(EXTRACTORS.entries()).map(([k, v]) => ({
      key: k, family: v.family, enabled: v.enabled, label: v.label
    })),
    listColumns: () => COLUMNS.slice(),
    listEngines: () => Array.from(ENGINES.entries()).map(([k, v]) => ({
      name: k, describe: v.describe, hasBuild: !!v.build, hasRender: !!v.render
    })),
    engines: ENGINES
  };
})();

window.ScreenerEngine = ScreenerEngine;
window.renderScreenerPanel = ScreenerEngine.renderScreenerPanel;
window.showScreenerBreakdown = ScreenerEngine.showScreenerBreakdown;
window.buildSymbolTable = ScreenerEngine.buildSymbolTable;
window.registerScreenerExtractor = ScreenerEngine.registerScreenerExtractor;
window.registerScreenerEngine = ScreenerEngine.registerScreenerEngine;
window.getScreenerSnapshot = ScreenerEngine.getSnapshot;
