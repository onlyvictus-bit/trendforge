// consensus.js — TrendForge Cross-Board Consensus Engine v4.1
// ─────────────────────────────────────────────────────────────────────────────
// Docs: ARCHITECTURE.md §5 · GRAPH.md §5 / §5b · INDEX.md (Consensus UI) · README.md
//
// Architecture (efficient · robust · future-proof):
//
//   1. RESOLVERS   — named field/metric strategies (symbol, side, deal value…)
//   2. PREPROCESS  — named source normalizers (preopen pass-through if already flat)
//   3. BOARD DEFS  — declarative configs only (no engine forks per feed)
//   4. REGISTRY    — registerConsensusBoard() for any future inventory link
//   5. ENGINE      — one pipeline: index → cache source once → score → aggregate
//   6. UI STRIPS   — Section 1 all-universe top5 · Section 2 Nifty∩ ranked top5
//
// Adding a NEW link later (zero engine edits):
//   registerConsensusBoard({ id, sourceKey, side, family, weight, label,
//     symbolFields, sideField?, metric, sortDir, rowFilter?, preprocess? });
//   // or use factories: ConsensusBoards.dealPair({...}), .momentum({...})
// ─────────────────────────────────────────────────────────────────────────────
'use strict';

const ConsensusEngine = (() => {
  // ═══════════════════════════════════════════════════════════════════════════
  // TUNABLES (single place — change policy without touching boards)
  // ═══════════════════════════════════════════════════════════════════════════
  const CONFIG = {
    version: 4.1,
    K: 10,
    uiTopN: 5,
    minConsensusBoards: 2,
    strongSingleMinPoints: 12,
    mixedNetEdge: 0.15,          // |net|/combined must be ≥ this when mixed
    familyDecay: [1.0, 0.45, 0.25, 0.15],
    sampleRowQuality: 0.35,      // sparse sample_row only
    minQuality: 0.25,
    riskMinStage: 1,
    blacklist: new Set(['UNDEFINED', '?', 'NONE', 'NULL', 'NA', 'N/A', '-']),

    // ── v4.1: context, safety, and display rails ────────────────────────────
    enableRegime: true,
    regimeMin: 0.85,
    regimeMax: 1.15,
    regimeDefault: 1.0,
    regimeFiiStep: 0.05,
    regimeBreadthStep: 0.03,

    enableBuyVeto: true,
    buyVetoFamilies: ['risk'],
    buyVetoSourceKeys: ['nse_asm', 'nse_gsm', 'nse_fno_ban'],

    enableNumericConfidence: true,
    minConfidenceForUi: null,

    showRankDelta: true,
    showInfoBadges: true,
    enableSectorTilt: false
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // PRIMITIVES
  // ═══════════════════════════════════════════════════════════════════════════
  function num(val) {
    if (val == null) return null;
    if (typeof val === 'number') return Number.isFinite(val) ? val : null;
    const cleaned = String(val).replace(/,/g, '').replace(/%/g, '').trim();
    if (!cleaned || cleaned === '-' || cleaned === '?' ||
        cleaned === 'NULL' || cleaned === 'NA' || cleaned === 'N/A') return null;
    const n = parseFloat(cleaned);
    return Number.isFinite(n) ? n : null;
  }

  function firstField(row, fields) {
    if (!row) return undefined;
    const list = Array.isArray(fields) ? fields : [fields];
    for (const f of list) {
      if (f == null) continue;
      if (Object.prototype.hasOwnProperty.call(row, f) && row[f] != null && row[f] !== '') {
        return row[f];
      }
    }
    // case-insensitive fallback (future schema drift)
    const keys = Object.keys(row);
    for (const f of list) {
      if (f == null) continue;
      const target = String(f).toLowerCase();
      for (const k of keys) {
        if (k.toLowerCase() === target && row[k] != null && row[k] !== '') return row[k];
      }
    }
    return undefined;
  }

  function pickNum(row, fields) {
    return num(firstField(row, fields));
  }

  function esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ── Side detection (NSE text + BSE P/S + insider verbs) ────────────────────
  function isBuySide(raw) {
    const t = String(raw || '').trim().toUpperCase();
    if (!t) return false;
    if (t === 'P' || t === 'B' || t === 'BUY' || t === 'PURCHASE') return true;
    return t.includes('BUY') || t.includes('ACQUI') || t.includes('PURCH');
  }
  function isSellSide(raw) {
    const t = String(raw || '').trim().toUpperCase();
    if (!t) return false;
    if (t === 'S' || t === 'SELL' || t === 'SALE') return true;
    return t.includes('SELL') || t.includes('DISPOS') || t.includes('SALE');
  }

  // ── Stage / Roman ─────────────────────────────────────────────────────────
  const ROMAN = { I: 1, V: 5, X: 10, L: 50, C: 100, D: 500, M: 1000 };
  function romanToInt(str) {
    const s = String(str || '').trim().toUpperCase();
    if (!s || !/^[IVXLCDM]+$/.test(s)) return null;
    let total = 0;
    for (let i = 0; i < s.length; i++) {
      const cur = ROMAN[s[i]] || 0;
      const next = ROMAN[s[i + 1]] || 0;
      total += cur < next ? -cur : cur;
    }
    return total > 0 ? total : null;
  }
  function stageRank(raw) {
    if (raw == null || raw === '') return 0;
    const upper = String(raw).trim().toUpperCase();
    const NAMED = {
      'STAGE 1': 1, 'STAGE 2': 2, 'STAGE 3': 3, 'STAGE 4': 4,
      'STAGE I': 1, 'STAGE II': 2, 'STAGE III': 3, 'STAGE IV': 4,
      'STAGE V': 5, 'STAGE VI': 6,
      '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6
    };
    if (NAMED[upper] != null) return NAMED[upper];
    const m = upper.match(/STAGE\s*([IVXLCDM]+|\d+)/);
    const tok = m ? m[1] : upper;
    const asNum = num(tok);
    if (asNum !== null && /^\d/.test(tok)) return asNum;
    const rom = romanToInt(tok);
    if (rom !== null) return rom;
    const digits = num(upper.replace(/[^0-9.]/g, ''));
    return digits !== null ? digits : 0;
  }

  /**
   * NSE GSM exports sometimes put a composite surveillance code (for example
   * LVIII) in `GSM Stage`, while Description/Surv. Code carries the real
   * `GSM Stage 0` token. Prefer that explicit token to avoid false hard vetoes.
   */
  function surveillanceStageRank(row, stageFields) {
    for (const field of ['Description', 'description', 'Surv. Code', 'survCode']) {
      const text = String(firstField(row, [field]) || '').trim();
      if (!/\bGSM\b/i.test(text)) continue;
      const match = text.match(/\bGSM(?:\s+STAGE)?\s*[-:]?\s*([0-9]+|[IVXLCDM]+)/i);
      if (match) return stageRank(match[1]);
    }
    return stageRank(firstField(row, stageFields || [
      'stage', 'GSM Stage', 'gsmStage', 'asmStage', 'asmSurvIndicator', 'Stage'
    ]));
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // METRIC RESOLVERS — register new metrics without touching the scorer
  // Each: (row, board) => number|null   (used as sort key + optional derive)
  // ═══════════════════════════════════════════════════════════════════════════
  const METRICS = {
    /** Day % change from ltp/prev or net_price/pChange */
    pctChange(row) {
      const ltp = pickNum(row, ['ltp', 'lastPrice', 'LTP', 'last', 'close', 'CLOSE_PRICE', 'ClsPric']);
      const prev = pickNum(row, ['prev_price', 'previousClose', 'prevClose', 'prev', 'PREV_CLOSE', 'previous_close']);
      if (ltp !== null && prev !== null && prev > 0) return ((ltp - prev) / prev) * 100;
      const net = pickNum(row, ['net_price', 'pChange', 'perChange', 'percentChange', 'pct_change']);
      return net;
    },

    /** Pre-open gap % (expects preprocess or gapPercent field) */
    gapPercent(row) {
      const g = pickNum(row, ['gapPercent', 'gap_percent', 'gap', 'pct_change', 'pChange']);
      if (g !== null) return g;
      const iep = pickNum(row, ['iep', 'IEP', 'open', 'OPEN_PRICE']);
      const prev = pickNum(row, ['prevClose', 'previousClose', 'prev_price', 'prev_close', 'PREV_CLOSE']);
      if (iep !== null && prev !== null && prev > 0) return ((iep - prev) / prev) * 100;
      return null;
    },

    /** Deal value ₹ Cr — resilient across NSE/BSE field names */
    dealValueCr(row) {
      const qty = pickNum(row, [
        'Quantity Traded', 'quantity', 'QUANTITY', 'qty', 'Qty', 'tradedQuantity'
      ]);
      const px = pickNum(row, [
        'Trade Price / Wght. Avg. Price', 'Trade Price', 'tradePrice',
        'price', 'PRICE', 'avgPrice', 'weightedAvgPrice'
      ]);
      if (qty === null || px === null) return null;
      return (qty * px) / 1e7;
    },

    volumeSpike(row) {
      return pickNum(row, ['week1volChange', 'volChange', 'volumeChange', 'pChangeVol']);
    },

    stageSeverity(row) {
      return surveillanceStageRank(row);
    },

    value(row) {
      return pickNum(row, [
        'value', 'Value', 'VALUE', '_v', 'notional', 'amount',
        'Fld_SecurityValue', 'SecurityValue', 'securityValue'
      ]);
    },

    /** Delivery % (MTO) — higher = more cash delivery interest */
    deliveryPct(row) {
      return pickNum(row, ['delivery_pct', 'deliveryPct', 'DELIV_PER', 'delivPer', 'deliverablePercent']);
    },

    /** Short-selling quantity */
    shortQty(row) {
      return pickNum(row, ['short_qty', 'shortQty', 'ShortQty', 'quantity']);
    },

    /** OI spurt intensity (% or absolute change) */
    oiSpurt(row) {
      const avg = pickNum(row, ['avgInOI', 'avgOiChange', 'oiChangePct']);
      if (avg !== null) return avg;
      return pickNum(row, ['changeInOI', 'changeInOi', 'oiChange', 'latestOI']);
    },

    tradedVolume(row) {
      return pickNum(row, [
        'totalTradedVolume', 'quantityTraded', 'volume', 'trade_quantity',
        'qty_traded', 'TTL_TRD_QNTY'
      ]);
    },

    tradedValue(row) {
      return pickNum(row, [
        'totalTradedValue', 'turnover', 'tradedValue', 'TURNOVER_LACS', 'totTurnover'
      ]);
    },

    /** Ban list membership severity (constant positive for banned rows) */
    banSeverity(row) {
      if (row.isBanned === true || String(row.banStatus || '').toUpperCase() === 'BANNED') return 1;
      return pickNum(row, ['mwplPercent', 'mwpl_percent']) || 1;
    },

    /** Generic: board.metricField / board.sortField */
    field(row, board) {
      const f = board.metricField || board.sortField;
      return f ? pickNum(row, Array.isArray(f) ? f : [f]) : null;
    }
  };

  function isIndexUnderlyingSymbol(sym) {
    const s = String(sym || '').trim().toUpperCase();
    return /^(NIFTY|BANKNIFTY|FINNIFTY|MIDCPNIFTY|NIFTYNXT50|INDIA VIX|SENSEX|BANKEX)$/i.test(s);
  }

  function resolveMetric(name) {
    if (typeof name === 'function') return name;
    if (name && METRICS[name]) return METRICS[name];
    return METRICS.field;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // PREPROCESSORS — normalize nested/raw feeds once per sourceKey (cached)
  // ═══════════════════════════════════════════════════════════════════════════
  const PREPROCESSORS = {
    identity(records) { return records; },

    preopen(records) {
      if (!Array.isArray(records) || !records.length) return [];

      // Already-flat samples (after inventory flatten): symbol + gap/iep, no metadata nest.
      // MUST NOT re-run schemas.flattenPreOpen — that reads only r.metadata and wipes symbols.
      const sample = records[0] || {};
      const alreadyFlat = !!(sample.symbol || sample.Symbol) && !sample.metadata;
      if (alreadyFlat) {
        return records.map(r => {
          const iep = num(r.iep);
          const prev = num(r.prevClose != null ? r.prevClose : r.previousClose);
          let gap = num(r.gapPercent);
          if (gap === null && iep !== null && prev !== null && prev > 0) {
            gap = ((iep - prev) / prev) * 100;
          }
          const symbol = String(r.symbol || r.Symbol || '').trim();
          return { ...r, symbol, iep, prevClose: prev, gapPercent: gap };
        }).filter(r => r.symbol);
      }

      const flatten = (typeof flattenPreOpen === 'function')
        ? flattenPreOpen
        : function fallbackFlatten(recs) {
            // Nested API shape: { metadata, detail.preOpenMarket }
            return recs.map(r => {
              const meta = r.metadata || {};
              const detail = r.detail || {};
              const preopen = detail.preOpenMarket || detail.preopen || {};
              const iep = num(preopen.IEP ?? meta.iep ?? preopen.iep);
              const prevClose = num(meta.previousClose ?? preopen.previousClose);
              const gap = (iep !== null && prevClose !== null && prevClose > 0)
                ? ((iep - prevClose) / prevClose) * 100 : null;
              return {
                symbol: meta.symbol || '',
                series: meta.series || '',
                iep, prevClose, gapPercent: gap
              };
            }).filter(r => r.symbol);
          };
      return flatten(records).map(r => {
        const iep = num(r.iep);
        const prev = num(r.prevClose);
        let gap = num(r.gapPercent);
        if (gap === null && iep !== null && prev !== null && prev > 0) {
          gap = ((iep - prev) / prev) * 100;
        }
        return { ...r, iep, prevClose: prev, gapPercent: gap };
      });
    }
  };

  function resolvePreprocess(name) {
    if (!name) return PREPROCESSORS.identity;
    if (typeof name === 'function') return name;
    return PREPROCESSORS[name] || PREPROCESSORS.identity;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // BOARD REGISTRY
  // ═══════════════════════════════════════════════════════════════════════════
  /** @type {Map<string, object>} */
  const boardRegistry = new Map();

  /**
   * Validate + normalize a board definition.
   * Future links only need to pass this shape.
   */
  function normalizeBoard(def) {
    if (!def || !def.id || !def.sourceKey) {
      throw new Error('[Consensus] board requires id + sourceKey');
    }
    const side = String(def.side || 'BUY').toUpperCase();
    if (side !== 'BUY' && side !== 'SELL') {
      throw new Error(`[Consensus] board ${def.id}: side must be BUY|SELL`);
    }
    const symbolFields = def.symbolFields || def.symbolField || ['symbol', 'Symbol', 'SYMBOL'];
    return {
      id: def.id,
      sourceKey: def.sourceKey,
      side,
      family: def.family || def.sourceKey,
      weight: Number(def.weight) > 0 ? Number(def.weight) : 1.0,
      label: def.label || def.id,
      symbolFields: Array.isArray(symbolFields) ? symbolFields : [symbolFields],
      sideField: def.sideField || null,       // e.g. 'Buy/Sell', 'TRANSACTION_TYPE'
      sideMode: def.sideMode || null,         // 'buy'|'sell' when filtering via sideField
      metric: def.metric || 'field',
      metricField: def.metricField || def.sortField || null,
      sortDir: (def.sortDir === 'asc') ? 'asc' : 'desc',
      preprocess: def.preprocess || null,     // name | fn
      rowFilter: typeof def.rowFilter === 'function' ? def.rowFilter : null,
      enabled: def.enabled !== false,
      // Optional: min metric value, etc.
      minMetric: def.minMetric != null ? def.minMetric : null,
      maxMetric: def.maxMetric != null ? def.maxMetric : null
    };
  }

  function registerConsensusBoard(def) {
    const board = normalizeBoard(def);
    boardRegistry.set(board.id, board);
    return board;
  }

  function registerConsensusBoards(defs) {
    return (defs || []).map(registerConsensusBoard);
  }

  function unregisterConsensusBoard(id) {
    return boardRegistry.delete(id);
  }

  function listConsensusBoards() {
    return Array.from(boardRegistry.values());
  }

  function clearConsensusBoards() {
    boardRegistry.clear();
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // BOARD FACTORIES — one-liners for common feed patterns (future links)
  // ═══════════════════════════════════════════════════════════════════════════
  const ConsensusBoards = {
    /**
     * Institutional deal feed → BUY + SELL pair (NSE/BSE bulk/block/large).
     * @example ConsensusBoards.dealPair({ sourceKey:'nse_block_deal', symbolFields:['symbol'], sideField:'side', weight:2 })
     */
    dealPair(cfg) {
      const base = {
        sourceKey: cfg.sourceKey,
        family: cfg.family || 'deals',
        weight: cfg.weight != null ? cfg.weight : 2.0,
        symbolFields: cfg.symbolFields || ['Symbol', 'symbol', 'scripname', 'SCRIP_CODE'],
        sideField: cfg.sideField || 'Buy/Sell',
        metric: 'dealValueCr',
        sortDir: 'desc',
        preprocess: cfg.preprocess || null
      };
      const buyId = cfg.buyId || `${cfg.sourceKey}__buy`;
      const sellId = cfg.sellId || `${cfg.sourceKey}__sell`;
      return [
        {
          ...base,
          id: buyId,
          side: 'BUY',
          label: cfg.buyLabel || `${cfg.label || cfg.sourceKey} – BUY`,
          sideMode: 'buy',
          rowFilter: cfg.buyFilter || (r => isBuySide(firstField(r, [base.sideField, 'side', 'TRANSACTION_TYPE', 'transactionType', 'Buy/Sell'])))
        },
        {
          ...base,
          id: sellId,
          side: 'SELL',
          label: cfg.sellLabel || `${cfg.label || cfg.sourceKey} – SELL`,
          sideMode: 'sell',
          rowFilter: cfg.sellFilter || (r => isSellSide(firstField(r, [base.sideField, 'side', 'TRANSACTION_TYPE', 'transactionType', 'Buy/Sell'])))
        }
      ];
    },

    /** Momentum list ranked by % change (gainers/losers style) */
    momentum(cfg) {
      return {
        id: cfg.id,
        sourceKey: cfg.sourceKey,
        side: cfg.side || 'BUY',
        family: cfg.family || 'momentum',
        weight: cfg.weight != null ? cfg.weight : 1.5,
        label: cfg.label || cfg.id,
        symbolFields: cfg.symbolFields || ['symbol', 'Symbol'],
        metric: 'pctChange',
        sortDir: cfg.sortDir || (cfg.side === 'SELL' ? 'asc' : 'desc'),
        rowFilter: cfg.rowFilter || null
      };
    },

    /** Volume spike split: pass side BUY|SELL; filters pChange sign */
    volumeSpike(cfg) {
      const side = (cfg.side || 'BUY').toUpperCase();
      return {
        id: cfg.id || `volume_${side.toLowerCase()}_${cfg.sourceKey}`,
        sourceKey: cfg.sourceKey,
        side,
        family: cfg.family || 'volume',
        weight: cfg.weight != null ? cfg.weight : 1.0,
        label: cfg.label || `Volume Spike – ${side === 'BUY' ? 'Up' : 'Down'}`,
        symbolFields: cfg.symbolFields || ['symbol', 'Symbol'],
        metric: 'volumeSpike',
        sortDir: 'desc',
        rowFilter: side === 'BUY'
          ? (r => { const p = METRICS.pctChange(r); return p !== null && p > 0; })
          : (r => { const p = METRICS.pctChange(r); return p !== null && p < 0; })
      };
    },

    /** Pre-open gap up/down */
    preopenGap(cfg) {
      const side = (cfg.side || 'BUY').toUpperCase();
      return {
        id: cfg.id,
        sourceKey: cfg.sourceKey || 'nse_preopen_fo',
        side,
        family: cfg.family || 'preopen',
        weight: cfg.weight != null ? cfg.weight : 1.5,
        label: cfg.label || (side === 'BUY' ? 'Pre-Open Gap Up' : 'Pre-Open Gap Down'),
        symbolFields: cfg.symbolFields || ['symbol'],
        metric: 'gapPercent',
        sortDir: side === 'BUY' ? 'desc' : 'asc',
        preprocess: 'preopen',
        rowFilter: side === 'BUY'
          ? (r => { const g = METRICS.gapPercent(r); return g !== null && g > 0; })
          : (r => { const g = METRICS.gapPercent(r); return g !== null && g < 0; })
      };
    },

    /** ASM/GSM surveillance → SELL/risk rail */
    surveillance(cfg) {
      const minStage = cfg.minStage != null ? cfg.minStage : CONFIG.riskMinStage;
      return {
        id: cfg.id,
        sourceKey: cfg.sourceKey,
        side: 'SELL',
        family: cfg.family || 'risk',
        weight: cfg.weight != null ? cfg.weight : 0.75,
        label: cfg.label || cfg.id,
        symbolFields: cfg.symbolFields || ['symbol', 'Symbol'],
        metric: 'stageSeverity',
        sortDir: 'desc',
        rowFilter: r => surveillanceStageRank(
          r, cfg.stageFields || ['stage', 'GSM Stage', 'gsmStage']
        ) >= minStage
      };
    },

    /** Insider PIT buy/sell pair */
    pitPair(cfg) {
      return ConsensusBoards.dealPair({
        ...cfg,
        family: cfg.family || 'insider',
        weight: cfg.weight != null ? cfg.weight : 2.0,
        sideField: cfg.sideField || 'transactionType',
        buyFilter: r => isBuySide(firstField(r, ['transactionType', 'Transaction Type', 'Fld_TransactionType'])),
        sellFilter: r => isSellSide(firstField(r, ['transactionType', 'Transaction Type', 'Fld_TransactionType'])),
        // override metric to notional value not dealValueCr
      }).map(b => ({
        ...b,
        metric: 'value',
        label: b.side === 'BUY'
          ? (cfg.buyLabel || 'NSE Insider PIT – BUY')
          : (cfg.sellLabel || 'NSE Insider PIT – SELL')
      }));
    },

    /** High cash delivery % (MTO) — constructive for BUY; low delivery for SELL */
    deliverySplit(cfg) {
      const key = cfg.sourceKey || 'nse_mto_delivery';
      const w = cfg.weight != null ? cfg.weight : 1.0;
      const minHigh = cfg.minHighPct != null ? cfg.minHighPct : 55;
      const maxLow = cfg.maxLowPct != null ? cfg.maxLowPct : 25;
      const base = {
        sourceKey: key,
        family: cfg.family || 'delivery',
        weight: w,
        symbolFields: cfg.symbolFields || ['symbol', 'Symbol'],
        metric: 'deliveryPct',
        sortDir: 'desc'
      };
      return [
        {
          ...base,
          id: cfg.buyId || `${key}__high_deliv`,
          side: 'BUY',
          label: cfg.buyLabel || 'High Delivery % (MTO)',
          sortDir: 'desc',
          rowFilter: r => {
            const p = METRICS.deliveryPct(r);
            return p !== null && p >= minHigh && !isIndexUnderlyingSymbol(firstField(r, base.symbolFields));
          }
        },
        {
          ...base,
          id: cfg.sellId || `${key}__low_deliv`,
          side: 'SELL',
          label: cfg.sellLabel || 'Low Delivery % (MTO)',
          sortDir: 'asc',
          rowFilter: r => {
            const p = METRICS.deliveryPct(r);
            return p !== null && p <= maxLow && p >= 0 && !isIndexUnderlyingSymbol(firstField(r, base.symbolFields));
          }
        }
      ];
    },

    /** Short-selling disclosure → SELL pressure rail */
    shortInterest(cfg) {
      return {
        id: cfg.id || `${cfg.sourceKey || 'nse_short_selling'}__short`,
        sourceKey: cfg.sourceKey || 'nse_short_selling',
        side: 'SELL',
        family: cfg.family || 'short',
        weight: cfg.weight != null ? cfg.weight : 1.25,
        label: cfg.label || 'NSE Short Selling',
        symbolFields: cfg.symbolFields || ['symbol', 'Symbol', 'security'],
        metric: 'shortQty',
        sortDir: 'desc',
        rowFilter: r => {
          const q = METRICS.shortQty(r);
          return q !== null && q > 0 && !isIndexUnderlyingSymbol(firstField(r, ['symbol', 'Symbol']));
        }
      };
    },

    /** OI spurts on stock underlyings (indexes excluded) */
    oiSpurt(cfg) {
      const side = (cfg.side || 'BUY').toUpperCase();
      return {
        id: cfg.id || `oi_spurt_${side.toLowerCase()}_${cfg.sourceKey || 'nse_oi_spurts'}`,
        sourceKey: cfg.sourceKey || 'nse_oi_spurts',
        side,
        family: cfg.family || 'derivatives_oi',
        weight: cfg.weight != null ? cfg.weight : 1.0,
        label: cfg.label || (side === 'BUY' ? 'OI Spurts – Rising' : 'OI Spurts – Falling'),
        symbolFields: cfg.symbolFields || ['symbol', 'Symbol', 'underlying'],
        metric: 'oiSpurt',
        sortDir: side === 'BUY' ? 'desc' : 'asc',
        rowFilter: r => {
          const sym = firstField(r, ['symbol', 'Symbol', 'underlying']);
          if (isIndexUnderlyingSymbol(sym)) return false;
          const m = METRICS.oiSpurt(r);
          if (m === null) return false;
          return side === 'BUY' ? m > 0 : m < 0;
        }
      };
    },

    /** F&O ban list → SELL / risk (hard veto evidence) */
    fnoBan(cfg) {
      return {
        id: cfg.id || 'nse_fno_ban_risk',
        sourceKey: cfg.sourceKey || 'nse_fno_ban',
        side: 'SELL',
        family: cfg.family || 'risk',
        weight: cfg.weight != null ? cfg.weight : 1.5,
        label: cfg.label || 'NSE F&O Ban List',
        symbolFields: cfg.symbolFields || ['symbol', 'Symbol'],
        metric: 'banSeverity',
        sortDir: 'desc',
        rowFilter: r => r.isBanned === true || String(r.banStatus || '').toUpperCase() === 'BANNED'
      };
    },

    /**
     * Generic ranked board for a brand-new link.
     * Prefer this when the feed doesn't fit a factory.
     */
    custom(cfg) {
      return normalizeBoard(cfg);
    }
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // DEFAULT BOARDS (current inventory) — add future links via register* only
  // ═══════════════════════════════════════════════════════════════════════════
  function loadDefaultBoards() {
    clearConsensusBoards();
    const defs = [
      ConsensusBoards.momentum({
        id: 'nse_gainers', sourceKey: 'nse_variations_gainers',
        side: 'BUY', label: 'NSE Day Gainers', weight: 1.5
      }),
      ConsensusBoards.preopenGap({
        id: 'nse_preopen_gapup', sourceKey: 'nse_preopen_fo', side: 'BUY',
        label: 'Pre-Open Gap Up (F&O)'
      }),
      ConsensusBoards.volumeSpike({
        id: 'nse_volume_spike_buy', sourceKey: 'nse_volume_gainers', side: 'BUY',
        label: 'NSE Volume Spike – Up'
      }),

      ConsensusBoards.momentum({
        id: 'nse_losers', sourceKey: 'nse_variations_loosers',
        side: 'SELL', label: 'NSE Day Losers', weight: 1.5, sortDir: 'asc'
      }),
      ConsensusBoards.preopenGap({
        id: 'nse_preopen_gapdown', sourceKey: 'nse_preopen_fo', side: 'SELL',
        label: 'Pre-Open Gap Down (F&O)'
      }),
      ConsensusBoards.volumeSpike({
        id: 'nse_volume_spike_sell', sourceKey: 'nse_volume_gainers', side: 'SELL',
        label: 'NSE Volume Spike – Down'
      }),

      ConsensusBoards.surveillance({
        id: 'nse_asm', sourceKey: 'nse_asm', label: 'NSE ASM Surveillance',
        symbolFields: ['symbol', 'Symbol'], stageFields: ['stage', 'asmSurvIndicator', 'asmStage']
      }),
      ConsensusBoards.surveillance({
        id: 'nse_gsm', sourceKey: 'nse_gsm', label: 'NSE GSM Surveillance',
        symbolFields: ['Symbol', 'symbol'], stageFields: ['GSM Stage', 'stage']
      }),

      ...ConsensusBoards.dealPair({
        sourceKey: 'nse_large_deals', label: 'NSE Large Deals',
        buyId: 'nse_large_deals_buy', sellId: 'nse_large_deals_sell',
        symbolFields: ['Symbol', 'symbol'],
        sideField: 'Buy/Sell'
      }),
      ...ConsensusBoards.dealPair({
        sourceKey: 'nse_large_deals_snapshot', label: 'NSE Block Snapshot',
        buyId: 'nse_snapshot_buy', sellId: 'nse_snapshot_sell',
        symbolFields: ['symbol'],
        sideField: 'side'
      }),
      // Future-ready: NSE block deal keys already in inventory catalog
      ...ConsensusBoards.dealPair({
        sourceKey: 'nse_block_deal', label: 'NSE Block Deal',
        buyId: 'nse_block_deal_buy', sellId: 'nse_block_deal_sell',
        symbolFields: ['symbol', 'Symbol'],
        sideField: 'Buy/Sell'
      }),
      ...ConsensusBoards.dealPair({
        sourceKey: 'nse_block_deal_live', label: 'NSE Block Deal Live',
        buyId: 'nse_block_deal_live_buy', sellId: 'nse_block_deal_live_sell',
        symbolFields: ['symbol', 'Symbol'],
        sideField: 'Buy/Sell'
      }),

      ...ConsensusBoards.pitPair({
        sourceKey: 'nse_pit_symbol',
        buyId: 'nse_pit_buy', sellId: 'nse_pit_sell',
        symbolFields: ['symbol']
      }),

      ...ConsensusBoards.dealPair({
        sourceKey: 'bse_bulk_deals', label: 'BSE Bulk Deals',
        buyId: 'bse_bulk_buy', sellId: 'bse_bulk_sell',
        symbolFields: ['scripname', 'SCRIP_CODE', 'symbol'],
        sideField: 'TRANSACTION_TYPE'
      }),
      ...ConsensusBoards.dealPair({
        sourceKey: 'bse_block_deals', label: 'BSE Block Deals',
        buyId: 'bse_block_buy', sellId: 'bse_block_sell',
        symbolFields: ['scripname', 'SCRIP_CODE', 'symbol'],
        sideField: 'TRANSACTION_TYPE'
      }),

      // ── Expanded stock-level voters (2026-08-06) — real symbols only ─────
      // Market-wide FII/DII / AMFI NAV totals are NOT stock voters (no symbol).
      ...ConsensusBoards.dealPair({
        sourceKey: 'nse_bulk_deals_today_csv', label: 'NSE Bulk Deals (Daily CSV)',
        buyId: 'nse_bulk_csv_buy', sellId: 'nse_bulk_csv_sell',
        symbolFields: ['Symbol', 'symbol'],
        sideField: 'Buy/Sell',
        weight: 2.0,
        family: 'deals'
      }),
      // BSE insider samples often store scrip *codes* in `symbol` (not NSE tickers).
      // Keep NSE PIT as the primary insider voter until a scrip→symbol map exists.
      // Optional experimental enable: map Companyname → ticker offline, then pitPair.
      ConsensusBoards.preopenGap({
        id: 'nse_preopen_cash_gapup', sourceKey: 'nse_preopen_cash', side: 'BUY',
        label: 'Cash Pre-Open Gap Up', weight: 1.5, family: 'preopen'
      }),
      ConsensusBoards.preopenGap({
        id: 'nse_preopen_cash_gapdown', sourceKey: 'nse_preopen_cash', side: 'SELL',
        label: 'Cash Pre-Open Gap Down', weight: 1.5, family: 'preopen'
      }),
      ConsensusBoards.volumeSpike({
        id: 'nse_most_active_vol_buy', sourceKey: 'nse_most_active_volume', side: 'BUY',
        label: 'Most Active Volume – Up', weight: 1.0, family: 'volume',
        // volumeSpike metric falls back via custom metricField on board — override below
      }),
      ConsensusBoards.volumeSpike({
        id: 'nse_most_active_vol_sell', sourceKey: 'nse_most_active_volume', side: 'SELL',
        label: 'Most Active Volume – Down', weight: 1.0, family: 'volume'
      }),
      {
        id: 'nse_most_active_value_buy',
        sourceKey: 'nse_most_active_value',
        side: 'BUY',
        family: 'volume',
        weight: 1.0,
        label: 'Most Active Value – Up',
        symbolFields: ['symbol', 'Symbol'],
        metric: 'tradedValue',
        sortDir: 'desc',
        rowFilter: r => {
          const p = METRICS.pctChange(r);
          return p !== null && p > 0;
        }
      },
      {
        id: 'nse_most_active_value_sell',
        sourceKey: 'nse_most_active_value',
        side: 'SELL',
        family: 'volume',
        weight: 1.0,
        label: 'Most Active Value – Down',
        symbolFields: ['symbol', 'Symbol'],
        metric: 'tradedValue',
        sortDir: 'desc',
        rowFilter: r => {
          const p = METRICS.pctChange(r);
          return p !== null && p < 0;
        }
      },
      ...ConsensusBoards.deliverySplit({
        sourceKey: 'nse_mto_delivery', weight: 1.0
      }),
      ConsensusBoards.shortInterest({
        sourceKey: 'nse_short_selling', weight: 1.25
      }),
      ConsensusBoards.oiSpurt({
        sourceKey: 'nse_oi_spurts', side: 'BUY', weight: 1.0
      }),
      ConsensusBoards.oiSpurt({
        sourceKey: 'nse_oi_spurts', side: 'SELL', weight: 1.0
      }),
      ConsensusBoards.fnoBan({
        sourceKey: 'nse_fno_ban', weight: 1.5
      }),
      // EOD cash gap / momentum from full equity bhavcopy (EQ series preferred)
      ConsensusBoards.momentum({
        id: 'nse_bhav_eod_gainers',
        sourceKey: 'nse_bhavcopy_eod',
        side: 'BUY',
        label: 'EOD Bhavcopy – Gainers',
        weight: 1.25,
        family: 'momentum_eod',
        symbolFields: ['symbol', 'Symbol'],
        rowFilter: r => {
          const series = String(r.series || r.Series || 'EQ').toUpperCase();
          if (series && series !== 'EQ' && series !== 'BE' && series !== 'BZ') return false;
          const p = METRICS.pctChange(r);
          return p !== null && p > 0;
        }
      }),
      ConsensusBoards.momentum({
        id: 'nse_bhav_eod_losers',
        sourceKey: 'nse_bhavcopy_eod',
        side: 'SELL',
        label: 'EOD Bhavcopy – Losers',
        weight: 1.25,
        family: 'momentum_eod',
        symbolFields: ['symbol', 'Symbol'],
        sortDir: 'asc',
        rowFilter: r => {
          const series = String(r.series || r.Series || 'EQ').toUpperCase();
          if (series && series !== 'EQ' && series !== 'BE' && series !== 'BZ') return false;
          const p = METRICS.pctChange(r);
          return p !== null && p < 0;
        }
      })
    ];
    // Fix most-active volume boards to rank by traded volume (not week1volChange)
    for (const d of defs) {
      if (d && d.sourceKey === 'nse_most_active_volume') {
        d.metric = 'tradedVolume';
      }
    }
    registerConsensusBoards(defs);
  }

  loadDefaultBoards();

  // ═══════════════════════════════════════════════════════════════════════════
  // ENGINE — efficient single pass with source cache
  // ═══════════════════════════════════════════════════════════════════════════

  /** Build sourceKey → inventory item index (O(n) once per compute) */
  function indexInventory(inventory) {
    const map = new Map();
    if (!Array.isArray(inventory)) return map;
    for (const item of inventory) {
      const keys = String(item.active_source_keys || '').split('|');
      for (const raw of keys) {
        const k = raw.trim();
        if (!k) continue;
        // first writer wins (mirrors old find() behaviour)
        if (!map.has(k)) map.set(k, item);
      }
    }
    return map;
  }

  function extractRecords(item) {
    if (!item) return { records: [], universeSize: 0, fromSampleRow: false };
    const rs = item.records_sample || [];
    if (rs.length > 0) return { records: rs, universeSize: rs.length, fromSampleRow: false };
    const sr = item.sample_row;
    if (sr && typeof sr === 'object' && !Array.isArray(sr) && Object.keys(sr).length > 0) {
      return { records: [sr], universeSize: 1, fromSampleRow: true };
    }
    return { records: [], universeSize: 0, fromSampleRow: false };
  }

  /**
   * Market context changes display/ranking magnitude only. It never creates a
   * symbol or a vote, and eligibility continues to use unscaled core scores.
   */
  function computeRegimeMultiplier(inventory) {
    const index = indexInventory(inventory);
    const reasons = [];
    let multiplier = CONFIG.regimeDefault;
    let fiiNet = null;
    let advances = null;
    let declines = null;

    const fiiRows = extractRecords(index.get('nse_fii_dii')).records;
    const labelledFiiRow = fiiRows.find(row => {
      const category = String(firstField(row, ['Category', 'category', 'investorType', 'clientType']) || '')
        .trim().toUpperCase();
      return category.includes('FII') || category.includes('FPI') || category.includes('FOREIGN');
    });
    // A single unlabelled row may be an already-normalized FII record. When a
    // multi-row market table is labelled, never mistake the DII row for FII.
    const fiiRow = labelledFiiRow || (fiiRows.length === 1 ? fiiRows[0] : null);
    if (fiiRow) {
      fiiNet = pickNum(fiiRow, [
        'net_value', 'netValue', 'fii_net', 'net', 'NetValue', 'fiiNet',
        'Net ₹ Cr', 'Net Rs Cr', 'netValueCr'
      ]);
      if (fiiNet === null) {
        const buy = pickNum(fiiRow, [
          'buy_value', 'buyValue', 'fii_buy', 'fiiBuy', 'BuyValue',
          'Buy ₹ Cr', 'Buy Rs Cr', 'buyValueCr'
        ]);
        const sell = pickNum(fiiRow, [
          'sell_value', 'sellValue', 'fii_sell', 'fiiSell', 'SellValue',
          'Sell ₹ Cr', 'Sell Rs Cr', 'sellValueCr'
        ]);
        if (buy !== null && sell !== null) fiiNet = buy - sell;
      }
    }

    const breadthAliases = {
      advances: ['advances', 'advance', 'advancesCount', 'advanceCount', 'Advances', 'ADVANCES'],
      declines: ['declines', 'decline', 'declinesCount', 'declineCount', 'Declines', 'DECLINES']
    };
    let breadthRows = extractRecords(index.get('nse_all_indices')).records;
    if (!breadthRows.length && Array.isArray(inventory)) {
      breadthRows = inventory.flatMap(item => extractRecords(item).records);
    }
    for (const row of breadthRows) {
      const adv = pickNum(row, breadthAliases.advances);
      const dec = pickNum(row, breadthAliases.declines);
      if (adv === null || dec === null) continue;
      advances = adv;
      declines = dec;
      break;
    }

    if (fiiNet !== null) {
      if (fiiNet > 0) {
        multiplier += CONFIG.regimeFiiStep;
        reasons.push('FII net +');
      } else if (fiiNet < 0) {
        multiplier -= CONFIG.regimeFiiStep;
        reasons.push('FII net -');
      }
    }
    if (advances !== null && declines !== null) {
      if (advances > declines) {
        multiplier += CONFIG.regimeBreadthStep;
        reasons.push('breadth +');
      } else if (advances < declines) {
        multiplier -= CONFIG.regimeBreadthStep;
        reasons.push('breadth -');
      }
    }

    multiplier = Math.max(CONFIG.regimeMin, Math.min(CONFIG.regimeMax, multiplier));
    if (!CONFIG.enableRegime) multiplier = CONFIG.regimeDefault;
    return {
      multiplier: Math.round(multiplier * 1000) / 1000,
      reasons: CONFIG.enableRegime ? reasons : [],
      inputs: { fiiNet, advances, declines }
    };
  }

  function isBuyVetoHit(hit) {
    if (!hit) return false;
    const family = String(hit.family || '').trim();
    if (CONFIG.buyVetoFamilies.includes(family)) return true;
    const sourceKey = String(hit.sourceKey || '').trim();
    const boardId = String(hit.boardId || '').trim();
    return CONFIG.buyVetoSourceKeys.some(key =>
      sourceKey === key || boardId === key || boardId.startsWith(`${key}_`)
    );
  }

  /** Accepts the raw symbol map or a flat test-friendly hit array. */
  function collectBuyVetoSet(rawOrScoreHits) {
    const veto = new Set();
    if (Array.isArray(rawOrScoreHits)) {
      for (const hit of rawOrScoreHits) {
        const symbol = String(hit && hit.symbol || '').trim().toUpperCase();
        if (symbol && isBuyVetoHit(hit)) veto.add(symbol);
      }
      return veto;
    }
    if (!rawOrScoreHits || typeof rawOrScoreHits !== 'object') return veto;
    for (const [symbol, sides] of Object.entries(rawOrScoreHits)) {
      const hits = Array.isArray(sides)
        ? sides
        : [].concat((sides && sides.BUY) || [], (sides && sides.SELL) || []);
      if (hits.some(isBuyVetoHit)) veto.add(String(symbol).trim().toUpperCase());
    }
    return veto;
  }

  /**
   * Risk boards still score only their top K for SELL evidence, but BUY safety
   * applies to every validated row in the underlying ASM/GSM/ban source.
   */
  function extendBuyVetoSetFromSources(veto, boards, loadSource) {
    for (const board of boards) {
      if (!isBuyVetoHit(board)) continue;
      const source = loadSource(board.sourceKey, board.preprocess);
      let rows = source.records || [];
      if (board.rowFilter) {
        try {
          rows = rows.filter(board.rowFilter);
        } catch (error) {
          console.warn(`[Consensus] veto filter failed on ${board.id}:`, error);
          continue;
        }
      }
      for (const row of rows) {
        const symbol = String(firstField(row, board.symbolFields) || '').trim().toUpperCase();
        if (symbol && !CONFIG.blacklist.has(symbol)) veto.add(symbol);
      }
    }
    return veto;
  }

  function numericConfidence({ multiBoard, sideFamilies, isMixed, buyScore, sellScore }) {
    const familyPart = 0.35 * Math.min((sideFamilies || 0) / 4, 1);
    const boardPart = 0.35 * (multiBoard ? 1 : 0.4);
    const high = Math.max(buyScore || 0, sellScore || 0, Number.EPSILON);
    const conflictRatio = isMixed ? Math.min(buyScore || 0, sellScore || 0) / high : 0;
    const conflictPart = 0.30 * (1 - conflictRatio);
    return Math.max(0, Math.min(1, Math.round((familyPart + boardPart + conflictPart) * 1000) / 1000));
  }

  function infoBadgesForBoards(boards) {
    if (!CONFIG.showInfoBadges) return [];
    return boards.some(hit => hit.family === 'deals' && hit.points > 0) ? ['LARGE_DEAL'] : [];
  }

  function sampleQuality(universeSize, validCount, fromSampleRow) {
    if (fromSampleRow || universeSize <= 1) return CONFIG.sampleRowQuality;
    const depth = Math.min(validCount, CONFIG.K);
    return Math.max(CONFIG.minQuality, Math.min(1, depth / CONFIG.K));
  }

  /**
   * Load + preprocess each sourceKey at most once per computeConsensus call.
   * Key efficiency win when many boards share a source (buy/sell splits, gap up/down).
   */
  function getSourceCache(index) {
    const cache = new Map(); // sourceKey + preprocessName → payload
    return function loadSource(sourceKey, preprocessName) {
      const cacheKey = sourceKey + '::' + (preprocessName || 'identity');
      if (cache.has(cacheKey)) return cache.get(cacheKey);

      const item = index.get(sourceKey);
      const extracted = extractRecords(item);
      if (!extracted.records.length) {
        const empty = { records: [], universeSize: 0, fromSampleRow: false };
        cache.set(cacheKey, empty);
        return empty;
      }
      const pp = resolvePreprocess(preprocessName);
      let records;
      try {
        records = pp(extracted.records) || [];
      } catch (err) {
        console.warn(`[Consensus] preprocess failed for ${sourceKey}:`, err);
        records = [];
      }
      const payload = {
        records,
        universeSize: extracted.universeSize,
        fromSampleRow: extracted.fromSampleRow
      };
      cache.set(cacheKey, payload);
      return payload;
    };
  }

  function scoreBoardTopK(board, loadSource) {
    const src = loadSource(board.sourceKey, board.preprocess);
    if (!src.records.length) return { scores: {}, meta: { active: false, reason: 'empty_source' } };

    const metricFn = resolveMetric(board.metric);
    let rows = src.records;

    if (board.rowFilter) {
      try {
        rows = rows.filter(board.rowFilter);
      } catch (err) {
        console.warn(`[Consensus] rowFilter failed on ${board.id}:`, err);
        return { scores: {}, meta: { active: false, reason: 'filter_error' } };
      }
    }

    // Attach metric once
    const scored = [];
    for (const r of rows) {
      let m;
      try {
        m = metricFn(r, board);
      } catch (_) {
        m = null;
      }
      m = num(m);
      if (m === null) continue;
      if (board.minMetric != null && m < board.minMetric) continue;
      if (board.maxMetric != null && m > board.maxMetric) continue;
      const sym = String(firstField(r, board.symbolFields) || '').trim().toUpperCase();
      if (!sym || CONFIG.blacklist.has(sym)) continue;
      scored.push({ sym, metric: m, row: r });
    }

    if (!scored.length) return { scores: {}, meta: { active: false, reason: 'no_valid_rows' } };

    scored.sort((a, b) => board.sortDir === 'asc' ? a.metric - b.metric : b.metric - a.metric);

    const quality = sampleQuality(src.universeSize, scored.length, src.fromSampleRow);
    const seen = new Set();
    const result = {};
    let rank = 0;
    for (const item of scored) {
      if (seen.has(item.sym)) continue;
      seen.add(item.sym);
      rank++;
      if (rank > CONFIG.K) break;
      const rawPoints = board.weight * (CONFIG.K + 1 - rank);
      result[item.sym] = {
        rank,
        points: rawPoints * quality,
        rawPoints,
        quality,
        metric: item.metric,
        boardId: board.id,
        boardLabel: board.label,
        family: board.family,
        weight: board.weight
      };
    }

    return {
      scores: result,
      meta: {
        active: rank > 0,
        quality,
        universeSize: src.universeSize,
        fromSampleRow: src.fromSampleRow,
        ranked: rank,
        validRows: scored.length
      }
    };
  }

  function applyFamilyDecay(hits) {
    const byFamily = new Map();
    for (const h of hits) {
      const f = h.family || h.boardId;
      if (!byFamily.has(f)) byFamily.set(f, []);
      byFamily.get(f).push(h);
    }
    let total = 0;
    const adjusted = [];
    for (const famHits of byFamily.values()) {
      famHits.sort((a, b) => b.points - a.points);
      famHits.forEach((h, i) => {
        const decay = CONFIG.familyDecay[Math.min(i, CONFIG.familyDecay.length - 1)];
        const pts = h.points * decay;
        total += pts;
        adjusted.push({
          boardId: h.boardId,
          boardLabel: h.boardLabel,
          sourceKey: h.sourceKey,
          side: h.side,
          rank: h.rank,
          points: Math.round(pts * 10) / 10,
          weight: h.weight,
          family: h.family,
          familyDecay: decay,
          quality: h.quality
        });
      });
    }
    return { total: Math.round(total * 10) / 10, boards: adjusted };
  }

  function computeConsensus(inventory) {
    const index = indexInventory(inventory);
    const loadSource = getSourceCache(index);
    const boards = listConsensusBoards().filter(b => b.enabled);
    const regimeInfo = computeRegimeMultiplier(inventory);

    /** @type {Record<string, {BUY: any[], SELL: any[]}>} */
    const raw = Object.create(null);
    let activeBoardCount = 0;
    const diagnostics = [];

    for (const board of boards) {
      const { scores, meta } = scoreBoardTopK(board, loadSource);
      if (!meta.active || !Object.keys(scores).length) {
        diagnostics.push({ id: board.id, sourceKey: board.sourceKey, active: false, ...meta });
        continue;
      }
      activeBoardCount++;
      diagnostics.push({
        id: board.id, sourceKey: board.sourceKey, active: true,
        symbols: Object.keys(scores).length, ...meta
      });

      for (const [sym, info] of Object.entries(scores)) {
        if (!raw[sym]) raw[sym] = { BUY: [], SELL: [] };
        raw[sym][board.side].push({
          boardId: info.boardId,
          boardLabel: info.boardLabel,
          sourceKey: board.sourceKey,
          side: board.side,
          rank: info.rank,
          points: info.points,
          rawPoints: info.rawPoints,
          quality: info.quality,
          weight: info.weight,
          family: info.family
        });
      }
    }

    const vetoSet = extendBuyVetoSetFromSources(collectBuyVetoSet(raw), boards, loadSource);

    const scoreMap = Object.create(null);
    const buyList = [];
    const sellList = [];

    for (const sym of Object.keys(raw)) {
      const sides = raw[sym];
      const buyAdj = applyFamilyDecay(sides.BUY);
      const sellAdj = applyFamilyDecay(sides.SELL);
      const buyScoreCore = buyAdj.total;
      const sellScoreCore = sellAdj.total;
      const buyBoards = buyAdj.boards.length;
      const sellBoards = sellAdj.boards.length;
      const buyFamilies = new Set(buyAdj.boards.map(b => b.family)).size;
      const sellFamilies = new Set(sellAdj.boards.map(b => b.family)).size;
      const isMixed = buyScoreCore > 0 && sellScoreCore > 0;

      let dominantSide = null;
      const net = buyScoreCore - sellScoreCore;
      if (net > 0) dominantSide = 'BUY';
      else if (net < 0) dominantSide = 'SELL';
      else if (buyBoards > sellBoards) dominantSide = 'BUY';
      else if (sellBoards > buyBoards) dominantSide = 'SELL';
      if (!dominantSide) continue;

      if (isMixed) {
        const combined = buyScoreCore + sellScoreCore;
        if (combined > 0 && Math.abs(net) / combined < CONFIG.mixedNetEdge) continue;
      }

      const sideScore = dominantSide === 'BUY' ? buyScoreCore : sellScoreCore;
      const sideBoards = dominantSide === 'BUY' ? buyBoards : sellBoards;
      const sideFamilies = dominantSide === 'BUY' ? buyFamilies : sellFamilies;
      const allBoards = buyAdj.boards.concat(sellAdj.boards);

      const multiBoard = sideBoards >= CONFIG.minConsensusBoards;
      const multiFamily = sideFamilies >= 2;
      const strongSingle = sideBoards === 1 && sideScore >= CONFIG.strongSingleMinPoints;
      if (!(multiBoard || multiFamily || strongSingle)) continue;

      // Surveillance and ban evidence is a hard BUY exclusion, even though the
      // risk board itself lives on the SELL rail.
      if (CONFIG.enableBuyVeto && dominantSide === 'BUY' && vetoSet.has(sym)) continue;

      // Existing eligibility gates above use core scores. Context scaling is
      // display/ranking-only and therefore cannot manufacture consensus.
      const buyScore = Math.round(buyScoreCore * regimeInfo.multiplier * 10) / 10;
      const sellScore = Math.round(sellScoreCore * regimeInfo.multiplier * 10) / 10;

      const confidence =
        multiBoard && multiFamily ? 'HIGH' :
        multiBoard || multiFamily ? 'MED' : 'LOW';
      const confidenceScore = CONFIG.enableNumericConfidence
        ? numericConfidence({
            multiBoard, sideFamilies, isMixed,
            buyScore: buyScoreCore, sellScore: sellScoreCore
          })
        : null;
      if (typeof CONFIG.minConfidenceForUi === 'number' &&
          (confidenceScore === null || confidenceScore < CONFIG.minConfidenceForUi)) continue;
      const infoBadges = infoBadgesForBoards(allBoards);

      const payload = {
        symbol: sym,
        buyScore, sellScore, isMixed,
        buyScoreCore, sellScoreCore,
        regime: regimeInfo.multiplier,
        tag: dominantSide,
        boards: allBoards,
        buyBoards, sellBoards,
        buyFamilies, sellFamilies,
        confidence, confidenceScore, infoBadges
      };

      scoreMap[sym] = {
        buyScore, sellScore, buyScoreCore, sellScoreCore,
        buyBoards, sellBoards, boards: allBoards,
        buyFamilies, sellFamilies, confidence, confidenceScore,
        infoBadges, regime: regimeInfo.multiplier
      };

      if (dominantSide === 'BUY') buyList.push(payload);
      else sellList.push(payload);
    }

    const confRank = { HIGH: 3, MED: 2, LOW: 1 };
    const rankKey = (a, b, side) => {
      const aScore = side === 'BUY' ? a.buyScore : a.sellScore;
      const bScore = side === 'BUY' ? b.buyScore : b.sellScore;
      const aB = side === 'BUY' ? a.buyBoards : a.sellBoards;
      const bB = side === 'BUY' ? b.buyBoards : b.sellBoards;
      const aF = side === 'BUY' ? a.buyFamilies : a.sellFamilies;
      const bF = side === 'BUY' ? b.buyFamilies : b.sellFamilies;
      return (
        (confRank[b.confidence] - confRank[a.confidence]) ||
        (bF - aF) ||
        ((b.confidenceScore || 0) - (a.confidenceScore || 0)) ||
        (bB - aB) || (bScore - aScore) ||
        a.symbol.localeCompare(b.symbol)
      );
    };

    buyList.sort((a, b) => rankKey(a, b, 'BUY'));
    sellList.sort((a, b) => rankKey(a, b, 'SELL'));

    // Known sources in inventory but not yet registered as boards (discovery aid)
    const registeredSources = new Set(boards.map(b => b.sourceKey));
    const unmappedSources = [];
    for (const k of index.keys()) {
      if (!registeredSources.has(k)) unmappedSources.push(k);
    }

    return {
      version: CONFIG.version,
      buy: buyList.slice(0, CONFIG.uiTopN),
      sell: sellList.slice(0, CONFIG.uiTopN),
      // Full ranked lists (for Nifty filter — top-5 alone may be all pennies)
      buyRanked: buyList,
      sellRanked: sellList,
      boardCount: activeBoardCount,
      totalConfiguredBoards: boards.length,
      symbolCount: Object.keys(raw).length,
      allScores: scoreMap,
      diagnostics,
      unmappedSources, // future links present in data but not voting yet
      regime: regimeInfo,
      config: { ...CONFIG, blacklist: undefined }
    };
  }

  // ── Nifty universe (trusted large/mid list) ────────────────────────────────
  // Static Nifty 50 (core large-caps). Inventory Nifty 500 sample fills midcaps.
  // Membership in 50 ∪ 100 ∪ 500 (whatever we have) = allowed in section 2.
  const NIFTY_50_STATIC = new Set([
    'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK', 'BAJAJ-AUTO',
    'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BHARTIARTL', 'CIPLA', 'COALINDIA', 'DRREDDY',
    'EICHERMOT', 'ETERNAL', 'GRASIM', 'HCLTECH', 'HDFCBANK', 'HDFCLIFE', 'HEROMOTOCO',
    'HINDALCO', 'HINDUNILVR', 'ICICIBANK', 'INDUSINDBK', 'INFY', 'ITC', 'JIOFIN',
    'JSWSTEEL', 'KOTAKBANK', 'LT', 'M&M', 'MARUTI', 'MAXHEALTH', 'NESTLEIND', 'NTPC',
    'ONGC', 'POWERGRID', 'RELIANCE', 'SBILIFE', 'SBIN', 'SUNPHARMA', 'TCS', 'TATACONSUM',
    'TATAMOTORS', 'TATASTEEL', 'TECHM', 'TITAN', 'TRENT', 'ULTRACEMCO', 'WIPRO'
  ]);

  function normalizeNiftySymbol(value) {
    return String(value || '')
      .trim()
      .toUpperCase()
      .replace(/^NSE:/, '')
      .replace(/\.NS$/, '')
      .replace(/-EQ$/, '');
  }

  function buildNiftyUniverse(inventory) {
    const official500 = new Set();
    let completeOfficial500 = false;
    const items = Array.isArray(inventory) ? inventory : [];
    for (const item of items) {
      const keys = String(item.active_source_keys || '');
      if (!/nifty500_constituents|nifty_500|ind_nifty500/i.test(keys)) continue;
      const rows = item.records_sample || [];
      const use = rows.length ? rows : (item.sample_row ? [item.sample_row] : []);
      for (const r of use) {
        if (!r || typeof r !== 'object') continue;
        const sym = normalizeNiftySymbol(
          r.Symbol || r.symbol || r.SYMBOL || r.TckrSymb || ''
        );
        if (sym && !CONFIG.blacklist.has(sym)) {
          official500.add(sym);
        }
      }
      for (const e of (item.entity_list || [])) {
        const sym = normalizeNiftySymbol(e);
        if (sym && !CONFIG.blacklist.has(sym)) {
          official500.add(sym);
        }
      }
      const normalizedRows = Number(item.normalized_row_count || rows.length || 0);
      const sourceRows = Number(item.source_row_count || item.usable_rows || 0);
      if (official500.size >= 500 && normalizedRows >= 500 && sourceRows >= 500) {
        completeOfficial500 = true;
      }
    }

    // A complete official Nifty 500 file is authoritative. The static Nifty 50
    // fallback is used only when the archived membership source is incomplete.
    const set = completeOfficial500 ? official500 : new Set(NIFTY_50_STATIC);
    if (!completeOfficial500) official500.forEach(sym => set.add(sym));
    return {
      set,
      size: set.size,
      nifty50: NIFTY_50_STATIC.size,
      fromInventoryExtra: Math.max(0, set.size - NIFTY_50_STATIC.size),
      completeOfficial500,
      sourceLabel: completeOfficial500
        ? `Complete official Nifty 500 (${set.size} symbols)`
        : set.size > NIFTY_50_STATIC.size
          ? `Nifty 50 + partial Nifty 500 (${set.size} symbols)`
          : `Nifty 50 core (${set.size} symbols)`
    };
  }

  function filterToNifty(rankedList, niftySet, limit = 5) {
    if (!rankedList || !rankedList.length) return [];
    return rankedList.filter(e => niftySet.has(normalizeNiftySymbol(e.symbol))).slice(0, limit);
  }

  function attachRanks(list, fullRanked) {
    const rankMap = new Map((fullRanked || []).map((entry, index) => [entry.symbol, index + 1]));
    return (list || []).map((entry, index) => ({
      ...entry,
      crossRank: rankMap.get(entry.symbol) || null,
      niftyRank: index + 1
    }));
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // UI
  // ═══════════════════════════════════════════════════════════════════════════
  let _consensusData = null;
  /** Last inventory used for consensus — for stock→link verification in modal */
  let _consensusInventory = null;

  function renderConsensusStrip(inventory) {
    const consensus = computeConsensus(inventory);
    _consensusData = consensus;
    _consensusInventory = Array.isArray(inventory) ? inventory : null;
    const el = document.getElementById('consensus-strip');
    if (!el) return consensus;

    // Nifty-filtered section (same scores, membership gate only)
    const niftyUni = buildNiftyUniverse(inventory);
    const fullBuyRanked = consensus.buyRanked || consensus.buy;
    const fullSellRanked = consensus.sellRanked || consensus.sell;
    const niftyBuyFiltered = filterToNifty(fullBuyRanked, niftyUni.set, CONFIG.uiTopN);
    const niftySellFiltered = filterToNifty(fullSellRanked, niftyUni.set, CONFIG.uiTopN);
    const niftyBuy = CONFIG.showRankDelta
      ? attachRanks(niftyBuyFiltered, fullBuyRanked)
      : niftyBuyFiltered;
    const niftySell = CONFIG.showRankDelta
      ? attachRanks(niftySellFiltered, fullSellRanked)
      : niftySellFiltered;
    consensus.nifty = {
      buy: niftyBuy,
      sell: niftySell,
      universeSize: niftyUni.size,
      sourceLabel: niftyUni.sourceLabel,
      regime: consensus.regime
    };

    const mkPill = (entry, side) => {
      const score = side === 'BUY' ? entry.buyScore : entry.sellScore;
      const boards = entry.boards.filter(b => b.side === side);
      const boardCount = boards.length;
      const conf = entry.confidence || 'LOW';
      const baseColor = side === 'BUY' ? '#22c55e' : '#ef4444';
      const dimColor = side === 'BUY' ? 'rgba(34,197,94,0.12)' : 'rgba(239,68,68,0.12)';
      const borderColor = side === 'BUY' ? 'rgba(34,197,94,0.35)' : 'rgba(239,68,68,0.35)';
      const confColor = conf === 'HIGH' ? '#fbbf24' : conf === 'MED' ? '#94a3b8' : '#475569';
      const stars = conf === 'HIGH' ? '★★★' : conf === 'MED' ? '★★' : '★';
      const mixedTag = entry.isMixed
        ? `<span style="font-size:0.58rem;background:rgba(251,191,36,0.2);color:#fbbf24;border-radius:3px;padding:0 3px;margin-left:3px;">MIXED</span>`
        : '';
      const safeSym = esc(entry.symbol);
      // CRITICAL: use single-quoted HTML attribute; JSON.stringify uses double quotes.
      // onclick="showConsensusBreakdown("IIFL",...)" breaks parsing — modal never opens.
      const jsSym = JSON.stringify(entry.symbol);
      const jsSide = JSON.stringify(side);
      const rankLine = CONFIG.showRankDelta && Number.isInteger(entry.crossRank) && Number.isInteger(entry.niftyRank)
        ? `<span style="font-size:0.58rem;color:#64748b;">#${entry.crossRank} cross · #${entry.niftyRank} nifty</span>`
        : '';
      const badgeLine = CONFIG.showInfoBadges && Array.isArray(entry.infoBadges) && entry.infoBadges.length
        ? `<span style="font-size:0.54rem;color:#38bdf8;border:1px solid rgba(56,189,248,0.25);border-radius:3px;padding:0 3px;">${entry.infoBadges.map(esc).join(' · ')}</span>`
        : '';
      return `
      <button type="button" onclick='showConsensusBreakdown(${jsSym}, ${jsSide})'
              style="display:inline-flex;flex-direction:column;align-items:flex-start;gap:1px;
                     padding:0.4rem 0.7rem;border-radius:8px;border:1px solid ${borderColor};
                     background:${dimColor};cursor:pointer;min-width:90px;max-width:140px;
                     transition:transform 0.15s,box-shadow 0.15s;font-family:inherit;"
              onmouseover="this.style.transform='translateY(-1px)';this.style.boxShadow='0 4px 14px rgba(0,0,0,0.35)'"
              onmouseout="this.style.transform='';this.style.boxShadow=''">
        <span style="font-weight:800;font-size:0.82rem;color:${baseColor};letter-spacing:0.02em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:120px;">
          ${safeSym}${mixedTag}
        </span>
        <span style="font-size:0.63rem;color:${confColor};">${stars} ${conf}</span>
        <span style="font-size:0.62rem;color:#64748b;">${boardCount}×board · ${score.toFixed(1)}pt</span>
        ${rankLine}
        ${badgeLine}
      </button>`;
    };

    const emptyBuy = '<span style="font-size:0.75rem;color:#64748b;padding:0.3rem 0.5rem;font-style:italic;">No multi-board BUY consensus yet</span>';
    const emptySell = '<span style="font-size:0.75rem;color:#64748b;padding:0.3rem 0.5rem;font-style:italic;">No multi-board SELL consensus yet</span>';
    const emptyNiftyBuy = '<span style="font-size:0.75rem;color:#64748b;padding:0.3rem 0.5rem;font-style:italic;">No Nifty-listed BUY in top consensus</span>';
    const emptyNiftySell = '<span style="font-size:0.75rem;color:#64748b;padding:0.3rem 0.5rem;font-style:italic;">No Nifty-listed SELL in top consensus</span>';

    const buyPills = consensus.buy.length ? consensus.buy.map(e => mkPill(e, 'BUY')).join('') : emptyBuy;
    const sellPills = consensus.sell.length ? consensus.sell.map(e => mkPill(e, 'SELL')).join('') : emptySell;
    const niftyBuyPills = niftyBuy.length ? niftyBuy.map(e => mkPill(e, 'BUY')).join('') : emptyNiftyBuy;
    const niftySellPills = niftySell.length ? niftySell.map(e => mkPill(e, 'SELL')).join('') : emptyNiftySell;

    const unmappedHint = (consensus.unmappedSources && consensus.unmappedSources.length)
      ? `<div style="font-size:0.55rem;color:#334155;margin-top:2px;" title="${esc(consensus.unmappedSources.slice(0, 12).join(', '))}">+${consensus.unmappedSources.length} unmapped sources</div>`
      : '';
    const regimeReasons = (consensus.regime && consensus.regime.reasons || []).map(esc).join(' · ');
    const regimeMultiplier = consensus.regime ? consensus.regime.multiplier : CONFIG.regimeDefault;
    const regimeLine = `Regime ×${Number(regimeMultiplier).toFixed(2)}` +
      (regimeReasons ? ` · ${regimeReasons}` : '') +
      ` · boards active ${consensus.boardCount}/${consensus.totalConfiguredBoards}`;

    const rowStyle = 'display:flex;align-items:stretch;gap:0;min-height:58px;';
    const labelCol = 'display:flex;flex-direction:column;justify-content:center;padding:0.5rem 0.85rem 0.5rem 1rem;border-right:1px solid rgba(255,255,255,0.07);min-width:118px;flex-shrink:0;';
    const sideCol = 'display:flex;align-items:center;gap:0.5rem;padding:0.5rem 0.75rem;flex:1;flex-wrap:wrap;';
    const noteCol = 'display:flex;flex-direction:column;justify-content:center;padding:0.4rem 0.75rem;border-left:1px solid rgba(255,255,255,0.07);min-width:120px;flex-shrink:0;';

    el.innerHTML = `
    <!-- Section 1: All-universe cross-board consensus (unchanged behaviour) -->
    <div class="consensus-row" style="${rowStyle}">
      <div class="consensus-label-col" style="${labelCol}">
        <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.08em;color:#64748b;margin-bottom:1px;">Cross-Board</div>
        <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;">Consensus v${consensus.version}</div>
        <div style="font-size:0.6rem;color:#475569;margin-top:2px;">${consensus.boardCount} active / ${consensus.totalConfiguredBoards} boards · ${consensus.symbolCount} symbols</div>
        <div style="font-size:0.56rem;color:#64748b;margin-top:2px;">${regimeLine}</div>
        ${unmappedHint}
      </div>
      <div class="consensus-side-col" style="${sideCol};border-right:1px solid rgba(255,255,255,0.07);">
        <span class="consensus-side-sr">BUY candidates</span>
        ${buyPills}
      </div>
      <div class="consensus-side-col" style="${sideCol}">
        <span class="consensus-side-sr">SELL candidates</span>
        ${sellPills}
      </div>
      <div class="consensus-note-col" style="${noteCol}">
        <div style="font-size:0.58rem;color:#475569;line-height:1.4;max-width:130px;">
          ⚠ All boards · may include small names.<br>Not financial advice.<br>Click pill → breakdown.
        </div>
      </div>
    </div>

    <!-- Section 2: Same scores, only Nifty 50/100/500 members -->
    <div class="consensus-row" style="${rowStyle};border-top:1px solid rgba(56,189,248,0.2);background:rgba(14,165,233,0.04);">
      <div class="consensus-label-col" style="${labelCol}">
        <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.08em;color:#38bdf8;margin-bottom:1px;">Nifty filter</div>
        <div style="font-size:0.75rem;font-weight:700;color:#7dd3fc;">Trusted index only</div>
        <div style="font-size:0.58rem;color:#475569;margin-top:2px;line-height:1.35;">
          ${esc(niftyUni.sourceLabel)}<br>
          BUY ${niftyBuy.length} · SELL ${niftySell.length}
        </div>
      </div>
      <div class="consensus-side-col" style="${sideCol};border-right:1px solid rgba(255,255,255,0.07);">
        <span class="consensus-side-sr">BUY candidates</span>
        ${niftyBuyPills}
      </div>
      <div class="consensus-side-col" style="${sideCol}">
        <span class="consensus-side-sr">SELL candidates</span>
        ${niftySellPills}
      </div>
      <div class="consensus-note-col" style="${noteCol}">
        <div style="font-size:0.58rem;color:#475569;line-height:1.4;max-width:130px;">
          ✓ High score + Nifty 50/500 member.<br>Filters penny / thin names.<br>Click pill → breakdown.
        </div>
      </div>
    </div>`;
    return consensus;
  }

  /**
   * Scan inventory samples for symbol presence (which catalog links contain this stock).
   */
  function findInventoryLinksForSymbol(symbol) {
    const sym = String(symbol || '').trim().toUpperCase();
    const inv = _consensusInventory || (typeof window !== 'undefined' && window.inventory) || [];
    if (!sym || !Array.isArray(inv)) return [];

    const hits = [];
    const SYM_KEYS = [
      'symbol', 'Symbol', 'SYMBOL', 'scripname', 'SCRIP_CODE', 'underlying',
      'Security', 'scrip_code', 'TckrSymb', 'Company', 'companyName'
    ];

    for (const item of inv) {
      const rows = item.records_sample || [];
      const checkRows = rows.length ? rows : (item.sample_row ? [item.sample_row] : []);
      let matchCount = 0;
      for (const r of checkRows) {
        if (!r || typeof r !== 'object') continue;
        let found = false;
        for (const k of SYM_KEYS) {
          if (r[k] != null && String(r[k]).trim().toUpperCase() === sym) {
            found = true;
            break;
          }
        }
        if (!found && r.metadata && String(r.metadata.symbol || '').trim().toUpperCase() === sym) {
          found = true;
        }
        if (found) matchCount++;
      }
      if (matchCount > 0) {
        hits.push({
          row_no: item.row_no,
          title: item.title || '',
          sourceKey: item.active_source_keys || '',
          status: item.status || '',
          topic: item.topic || '',
          matchCount,
          sampleRows: (item.records_sample || []).length,
          usable_rows: item.usable_rows,
          url: item.canonical_url || ''
        });
      }
    }
    hits.sort((a, b) => b.matchCount - a.matchCount || a.row_no - b.row_no);
    return hits;
  }

  function showConsensusBreakdown(symbol, activeSide) {
    if (!_consensusData) {
      console.warn('[Consensus] No consensus data yet');
      return;
    }
    const symKey = String(symbol || '').trim().toUpperCase();
    let data = _consensusData.allScores && _consensusData.allScores[symKey];

    // Fallback: buy/sell list payloads (same boards/scores)
    if (!data) {
      const fromList = []
        .concat(_consensusData.buy || [], _consensusData.sell || [])
        .find(e => String(e.symbol).toUpperCase() === symKey);
      if (fromList) {
        data = {
          buyScore: fromList.buyScore,
          sellScore: fromList.sellScore,
          buyBoards: fromList.buyBoards,
          sellBoards: fromList.sellBoards,
          boards: fromList.boards || [],
          buyFamilies: fromList.buyFamilies,
          sellFamilies: fromList.sellFamilies,
          confidence: fromList.confidence
        };
      }
    }
    if (!data) {
      console.warn('[Consensus] No score entry for', symKey);
      return;
    }

    const buyBoards = (data.boards || []).filter(b => b.side === 'BUY').sort((a, b) => b.points - a.points);
    const sellBoards = (data.boards || []).filter(b => b.side === 'SELL').sort((a, b) => b.points - a.points);
    const linkHits = findInventoryLinksForSymbol(symKey);

    const mkBoardRows = (boards, color) => boards.length
      ? boards.map(b => `
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
          <td style="padding:0.4rem 0.6rem;font-size:0.78rem;color:#e2e8f0;">
            ${esc(b.boardLabel || b.boardId)}
            ${b.family ? `<div style="font-size:0.6rem;color:#475569;">${esc(b.family)}${b.familyDecay != null && b.familyDecay < 1 ? ` · decay ×${b.familyDecay}` : ''}</div>` : (b.familyDecay != null && b.familyDecay < 1 ? ` <span style="font-size:0.6rem;color:#64748b;">(×${b.familyDecay} fam)</span>` : '')}
          </td>
          <td style="padding:0.4rem 0.6rem;font-size:0.75rem;color:#94a3b8;text-align:center;">#${b.rank}</td>
          <td style="padding:0.4rem 0.6rem;font-size:0.75rem;color:#94a3b8;text-align:center;">×${b.weight}</td>
          <td style="padding:0.4rem 0.6rem;font-size:0.78rem;font-weight:700;color:${color};text-align:right;font-family:var(--font-mono);">${b.points}</td>
        </tr>`).join('')
      : `<tr><td colspan="4" style="padding:0.75rem;font-size:0.75rem;color:#475569;text-align:center;">No boards on this side</td></tr>`;

    const mkLinkRows = (hits) => hits.length
      ? hits.map(h => `
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
          <td style="padding:0.35rem 0.5rem;font-size:0.72rem;color:#94a3b8;font-family:var(--font-mono);">#${h.row_no}</td>
          <td style="padding:0.35rem 0.5rem;font-size:0.75rem;color:#e2e8f0;">
            ${esc(h.title)}
            <div style="font-size:0.6rem;color:#475569;font-family:var(--font-mono);">${esc(h.sourceKey)}</div>
          </td>
          <td style="padding:0.35rem 0.5rem;font-size:0.65rem;color:#94a3b8;text-align:center;">${esc(h.status)}</td>
          <td style="padding:0.35rem 0.5rem;font-size:0.72rem;color:#94a3b8;text-align:center;">${h.matchCount}</td>
          <td style="padding:0.35rem 0.5rem;font-size:0.72rem;color:#64748b;text-align:right;">${h.sampleRows}</td>
          <td style="padding:0.35rem 0.5rem;text-align:right;">
            <button type="button"
              onclick="(function(){var m=document.getElementById('consensus-modal');if(m)m.remove();if(typeof openDrawer==='function')openDrawer(${h.row_no});})()"
              style="background:rgba(56,189,248,0.12);border:1px solid rgba(56,189,248,0.3);color:#38bdf8;padding:0.15rem 0.4rem;border-radius:4px;cursor:pointer;font-size:0.65rem;">Details</button>
          </td>
        </tr>`).join('')
      : `<tr><td colspan="6" style="padding:0.75rem;font-size:0.75rem;color:#475569;text-align:center;">No inventory link samples contain this symbol</td></tr>`;

    const buyTotal = buyBoards.reduce((s, b) => s + b.points, 0).toFixed(1);
    const sellTotal = sellBoards.reduce((s, b) => s + b.points, 0).toFixed(1);
    const isMixed = buyBoards.length > 0 && sellBoards.length > 0;
    const safeSym = esc(symbol);
    const conf = data.confidence || '';
    const totalVoteBoards = (data.boards || []).length;
    const uniqueFamilies = new Set((data.boards || []).map(b => b.family || b.boardId)).size;

    const existing = document.getElementById('consensus-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'consensus-modal';
    modal.style.cssText = `position:fixed;inset:0;z-index:10050;display:flex;align-items:center;justify-content:center;
      background:rgba(0,0,0,0.75);backdrop-filter:blur(4px);`;
    modal.innerHTML = `
    <div style="background:#0f1629;border:1px solid rgba(255,255,255,0.12);border-radius:12px;
                width:min(720px,96vw);max-height:90vh;overflow-y:auto;box-shadow:0 24px 60px rgba(0,0,0,0.6);"
         onclick="event.stopPropagation()">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:1.1rem 1.4rem;
                  border-bottom:1px solid rgba(255,255,255,0.08);position:sticky;top:0;background:#0f1629;z-index:1;">
        <div>
          <div style="font-size:1.25rem;font-weight:800;color:#e2e8f0;font-family:var(--font-mono);">${safeSym}</div>
          <div style="font-size:0.72rem;color:#64748b;margin-top:4px;line-height:1.5;">
            <strong style="color:#94a3b8;">${totalVoteBoards}</strong> consensus board${totalVoteBoards !== 1 ? 's' : ''} ·
            <strong style="color:#94a3b8;">${uniqueFamilies}</strong> families ·
            <strong style="color:#38bdf8;">${linkHits.length}</strong> inventory link${linkHits.length !== 1 ? 's' : ''} contain this symbol
            ${conf ? ` · confidence <span style="color:#fbbf24;">${esc(conf)}</span>` : ''}
            ${isMixed ? ' <span style="background:rgba(251,191,36,0.15);color:#fbbf24;padding:1px 5px;border-radius:3px;">MIXED</span>' : ''}
          </div>
        </div>
        <button type="button" onclick="document.getElementById('consensus-modal').remove()"
                style="background:none;border:1px solid rgba(255,255,255,0.15);color:#94a3b8;padding:0.3rem 0.65rem;
                       border-radius:6px;cursor:pointer;font-size:0.85rem;">✕ Close</button>
      </div>

      <div style="display:flex;gap:0.75rem;padding:0.85rem 1.4rem;border-bottom:1px solid rgba(255,255,255,0.06);flex-wrap:wrap;">
        <div style="flex:1;min-width:120px;background:rgba(34,197,94,0.07);border:1px solid rgba(34,197,94,0.2);border-radius:8px;padding:0.6rem 0.9rem;">
          <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.06em;color:#22c55e;margin-bottom:2px;">▲ BUY</div>
          <div style="font-size:1.35rem;font-weight:800;color:#22c55e;font-family:var(--font-mono);">${buyTotal}</div>
          <div style="font-size:0.68rem;color:#64748b;">${buyBoards.length} boards</div>
        </div>
        <div style="flex:1;min-width:120px;background:rgba(239,68,68,0.07);border:1px solid rgba(239,68,68,0.2);border-radius:8px;padding:0.6rem 0.9rem;">
          <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.06em;color:#ef4444;margin-bottom:2px;">▼ SELL</div>
          <div style="font-size:1.35rem;font-weight:800;color:#ef4444;font-family:var(--font-mono);">${sellTotal}</div>
          <div style="font-size:0.68rem;color:#64748b;">${sellBoards.length} boards</div>
        </div>
        <div style="flex:1;min-width:120px;background:rgba(56,189,248,0.07);border:1px solid rgba(56,189,248,0.2);border-radius:8px;padding:0.6rem 0.9rem;">
          <div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.06em;color:#38bdf8;margin-bottom:2px;">Inventory links</div>
          <div style="font-size:1.35rem;font-weight:800;color:#38bdf8;font-family:var(--font-mono);">${linkHits.length}</div>
          <div style="font-size:0.68rem;color:#64748b;">catalog rows with symbol</div>
        </div>
      </div>

      <div style="padding:0.75rem 1.4rem 0.35rem;">
        <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#22c55e;margin-bottom:0.4rem;">▲ BUY Votes</div>
        <table style="width:100%;border-collapse:collapse;">
          <thead><tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
            <th style="text-align:left;padding:0.3rem 0.6rem;font-size:0.65rem;color:#475569;text-transform:uppercase;">Board</th>
            <th style="text-align:center;padding:0.3rem 0.6rem;font-size:0.65rem;color:#475569;text-transform:uppercase;">Rank</th>
            <th style="text-align:center;padding:0.3rem 0.6rem;font-size:0.65rem;color:#475569;text-transform:uppercase;">Weight</th>
            <th style="text-align:right;padding:0.3rem 0.6rem;font-size:0.65rem;color:#475569;text-transform:uppercase;">Points</th>
          </tr></thead>
          <tbody>${mkBoardRows(buyBoards, '#22c55e')}</tbody>
        </table>
      </div>

      <div style="padding:0.5rem 1.4rem 0.5rem;">
        <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#ef4444;margin-bottom:0.4rem;">▼ SELL Votes</div>
        <table style="width:100%;border-collapse:collapse;">
          <thead><tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
            <th style="text-align:left;padding:0.3rem 0.6rem;font-size:0.65rem;color:#475569;text-transform:uppercase;">Board</th>
            <th style="text-align:center;padding:0.3rem 0.6rem;font-size:0.65rem;color:#475569;text-transform:uppercase;">Rank</th>
            <th style="text-align:center;padding:0.3rem 0.6rem;font-size:0.65rem;color:#475569;text-transform:uppercase;">Weight</th>
            <th style="text-align:right;padding:0.3rem 0.6rem;font-size:0.65rem;color:#475569;text-transform:uppercase;">Points</th>
          </tr></thead>
          <tbody>${mkBoardRows(sellBoards, '#ef4444')}</tbody>
        </table>
      </div>

      <div style="padding:0.5rem 1.4rem 0.85rem;">
        <div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:#38bdf8;margin-bottom:0.4rem;">
          Inventory links containing ${safeSym}
        </div>
        <table style="width:100%;border-collapse:collapse;">
          <thead><tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
            <th style="text-align:left;padding:0.3rem 0.5rem;font-size:0.62rem;color:#475569;text-transform:uppercase;">Row</th>
            <th style="text-align:left;padding:0.3rem 0.5rem;font-size:0.62rem;color:#475569;text-transform:uppercase;">Link / source key</th>
            <th style="text-align:center;padding:0.3rem 0.5rem;font-size:0.62rem;color:#475569;text-transform:uppercase;">Status</th>
            <th style="text-align:center;padding:0.3rem 0.5rem;font-size:0.62rem;color:#475569;text-transform:uppercase;">Hits</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;font-size:0.62rem;color:#475569;text-transform:uppercase;">Sample</th>
            <th></th>
          </tr></thead>
          <tbody>${mkLinkRows(linkHits)}</tbody>
        </table>
      </div>

      <div style="padding:0.6rem 1.4rem;border-top:1px solid rgba(255,255,255,0.06);font-size:0.62rem;color:#334155;line-height:1.6;">
        ⚠ Cached inventory only. Not real-time. Not financial advice.<br>
        Consensus points = weight × (11 − rank) × sample_quality × family_decay.
        Inventory table lists every catalog link whose samples include this symbol.
      </div>
    </div>`;
    modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
    document.body.appendChild(modal);
  }

  // Public API
  return {
    CONFIG,
    METRICS,
    PREPROCESSORS,
    ConsensusBoards,
    registerConsensusBoard,
    registerConsensusBoards,
    unregisterConsensusBoard,
    listConsensusBoards,
    clearConsensusBoards,
    loadDefaultBoards,
    registerMetric(name, fn) { METRICS[name] = fn; },
    registerPreprocessor(name, fn) { PREPROCESSORS[name] = fn; },
    computeConsensus,
    renderConsensusStrip,
    showConsensusBreakdown,
    // utils exposed for tests / diag
    utils: {
      num, firstField, pickNum, isBuySide, isSellSide, stageRank, surveillanceStageRank, esc,
      normalizeNiftySymbol, buildNiftyUniverse, filterToNifty, attachRanks,
      computeRegimeMultiplier, collectBuyVetoSet
    }
  };
})();

// Window bindings (backward compatible with app.js)
window.ConsensusEngine = ConsensusEngine;
window.ConsensusBoards = ConsensusEngine.ConsensusBoards;
window.registerConsensusBoard = ConsensusEngine.registerConsensusBoard;
window.registerConsensusBoards = ConsensusEngine.registerConsensusBoards;
window.unregisterConsensusBoard = ConsensusEngine.unregisterConsensusBoard;
window.listConsensusBoards = ConsensusEngine.listConsensusBoards;
window.computeConsensus = ConsensusEngine.computeConsensus;
window.renderConsensusStrip = ConsensusEngine.renderConsensusStrip;
window.showConsensusBreakdown = ConsensusEngine.showConsensusBreakdown;
