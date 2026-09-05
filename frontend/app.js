const fallbackExamples = [
  {
    symbol: "COFORGE",
    type: "stock",
    state: "WATCH",
    stateTone: "good",
    statusGroup: "wait",
    setup: "Smart money + OI long build-up",
    timeframe: ["30m", "1h", "1d"],
    price: "INR 7,862",
    move: "+1.8%",
    reason: "Smart money, OI, volume, futures basis, anchors, and safety align.",
    decisionTitle: "WATCH - DEMO",
    decisionText: "Execute only at trigger with predefined stop and position size.",
    trade: { entry: "7,862", stop: "7,780", target: "8,120" },
    quality: 86,
    metrics: [
      ["Smart Money", "10/10", "CEO buy, FII bulk deal, AMC add"],
      ["OI Quadrant", "LONG_BUILD_UP", "Price up + OI up, MWPL safe"],
      ["Volume", "2.8x RVOL", "Avg trade size institutional"],
      ["Basis", "+29 rising", "Futures premium expanding"],
      ["Anchors", "Accepted", "Above deal price and AVWAP"],
      ["Safety", "GREEN", "No FOMO or emotional lock"]
    ],
    proof: [
      ["AMFI", "MF add confirmed"],
      ["Bulk/Block", "FII premium deal"],
      ["MWPL", "54% safe"],
      ["SLB", "Low borrow risk"],
      ["Harmonic", "No conflict"],
      ["Expiry", "No distortion"]
    ],
    risk: [
      ["Risk/share", "INR 82"],
      ["Position", "60 shares"],
      ["Max loss", "INR 4,920"],
      ["R:R T2", "3.1"],
      ["Correlation", "Clean"]
    ],
    sources: [
      ["NSE", "GREEN"],
      ["BSE", "GREEN"],
      ["AMFI", "GREEN"],
      ["SLB", "AMBER"],
      ["SEBI", "GREEN"],
      ["Broker", "GREEN"]
    ],
    series: [30, 34, 33, 38, 43, 41, 47, 51, 49, 55, 62, 66, 64, 72, 78, 81]
  },
  {
    symbol: "TCS",
    type: "harmonic",
    state: "HARMONIC_PRZ_ACTIVE",
    stateTone: "warn",
    statusGroup: "wait",
    setup: "1D Bullish Bat in PRZ",
    timeframe: ["1h", "4h", "1d", "1w"],
    price: "INR 3,846",
    move: "+0.4%",
    reason: "Daily PRZ aligns with weekly support, but volume and VWAP confirmation are pending.",
    decisionTitle: "WAIT FOR CONFIRMATION",
    decisionText: "Alert only above PRZ high with RVOL-TOD confirmation.",
    trade: { entry: "3,875", stop: "3,790", target: "4,120" },
    quality: 68,
    metrics: [
      ["Pattern", "Bullish Bat", "PRZ active, D point forming"],
      ["PRZ", "3,820-3,870", "Current price inside zone"],
      ["MTF", "1W support", "Higher timeframe supports reversal"],
      ["Volume", "Pending", "Needs RVOL-TOD > 1.5"],
      ["VWAP", "Pending", "Reclaim not confirmed"],
      ["Data", "GREEN", "4H custom session labelled"]
    ],
    proof: [
      ["Ratios", "Valid normal"],
      ["1W", "Support aligned"],
      ["1H", "Trigger pending"],
      ["Volume", "Not confirmed"],
      ["VWAP", "Pending"],
      ["Invalidation", "3,790"]
    ],
    risk: [
      ["Pattern risk", "Normal"],
      ["Stop gap", "INR 85"],
      ["Target 1", "3,980"],
      ["Target 2", "4,120"],
      ["Mode", "Watch"]
    ],
    sources: [
      ["Feed", "GREEN"],
      ["1D", "GREEN"],
      ["1W", "GREEN"],
      ["4H", "WARN"],
      ["AMFI", "GREEN"],
      ["Pattern", "GREEN"]
    ],
    series: [72, 69, 65, 61, 58, 54, 49, 45, 42, 40, 43, 44, 46, 49, 52, 55]
  },
  {
    symbol: "RELIANCE",
    type: "stock",
    state: "WAIT_BASIS_CONFLICT",
    stateTone: "warn",
    statusGroup: "wait",
    setup: "Smart money bullish, futures basis falling",
    timeframe: ["30m", "1h", "1d"],
    price: "INR 2,914",
    move: "+0.6%",
    reason: "Price and volume are positive, but futures basis is falling and AVWAP acceptance is incomplete.",
    decisionTitle: "WAIT BASIS CONFLICT",
    decisionText: "Do not chase until basis stabilizes and price holds above AVWAP.",
    trade: { entry: "2,928", stop: "2,872", target: "3,040" },
    quality: 61,
    metrics: [
      ["Smart Money", "Strong", "Block interest detected"],
      ["OI", "LONG_BUILD_UP", "MWPL safe"],
      ["Volume", "1.9x RVOL", "Good but not decisive"],
      ["Basis", "Falling", "Institutional hedge risk"],
      ["AVWAP", "Testing", "Not accepted yet"],
      ["Safety", "GREEN", "No emotional block"]
    ],
    proof: [
      ["OI", "Bullish"],
      ["Basis", "Conflict"],
      ["AVWAP", "Testing"],
      ["Volume", "Good"],
      ["Source", "Official"],
      ["State", "WAIT"]
    ],
    risk: [
      ["Risk/share", "INR 56"],
      ["Position", "89 shares"],
      ["Max loss", "INR 4,984"],
      ["R:R T2", "2.0"],
      ["Conflict", "Basis"]
    ],
    sources: [
      ["NSE", "GREEN"],
      ["BSE", "GREEN"],
      ["F&O", "GREEN"],
      ["AMFI", "AMBER"],
      ["SLB", "GREEN"],
      ["SEBI", "GREEN"]
    ],
    series: [44, 48, 53, 56, 61, 59, 63, 64, 66, 65, 67, 66, 68, 67, 66, 65]
  },
  {
    symbol: "MCX GOLD MINI",
    type: "mcx",
    state: "WATCH",
    stateTone: "good",
    statusGroup: "wait",
    setup: "COMEX bull + INR stable + OI aligned",
    timeframe: ["30m", "1h", "4h"],
    price: "INR 68,950",
    move: "+0.9%",
    reason: "COMEX trend, real yields, DXY, COT, MCX OI, and premium align.",
    decisionTitle: "WATCH - DEMO",
    decisionText: "Use Gold Mini lot sizing. Exit if USD/INR conflict appears.",
    trade: { entry: "68,950", stop: "68,640", target: "69,700" },
    quality: 82,
    metrics: [
      ["COMEX", "Bullish", "Gold above ORB and 50 DMA"],
      ["USD/INR", "Stable", "Currency leg not blocking"],
      ["COT", "MM long up", "Week 3 trend build"],
      ["MCX OI", "LONG_BUILD_UP", "Local and global aligned"],
      ["Premium", "+320", "Domestic demand healthy"],
      ["Safety", "GREEN", "No event block"]
    ],
    proof: [
      ["COT", "Bullish"],
      ["DXY", "Falling"],
      ["Real Yield", "Falling"],
      ["MCX OI", "Aligned"],
      ["Premium", "Rising"],
      ["Event", "Clear"]
    ],
    risk: [
      ["Lot", "Gold Mini"],
      ["Risk/lot", "INR 3,100"],
      ["Max lots", "1"],
      ["Margin", "OK"],
      ["Key risk", "USD/INR"]
    ],
    sources: [
      ["MCX", "GREEN"],
      ["CFTC", "GREEN"],
      ["WGC", "GREEN"],
      ["FRED", "GREEN"],
      ["USDINR", "GREEN"],
      ["EIA", "NA"]
    ],
    series: [40, 42, 45, 44, 48, 52, 55, 58, 61, 64, 66, 68, 71, 74, 78, 80]
  },
  {
    symbol: "HDFCBANK",
    type: "stock",
    state: "REJECT_SUPPLY",
    stateTone: "bad",
    statusGroup: "reject",
    setup: "Supply overhang above anchor",
    timeframe: ["1h", "1d", "1w"],
    price: "INR 1,682",
    move: "-0.3%",
    reason: "Price is below AVWAP and supply overhang blocks clean upside.",
    decisionTitle: "REJECT FOR NOW",
    decisionText: "Keep in watchlist only. Needs anchor reclaim and supply absorption.",
    trade: { entry: "-", stop: "-", target: "-" },
    quality: 38,
    metrics: [
      ["Smart Money", "Mixed", "No strong current sponsor"],
      ["OI", "Long unwind", "Price down + OI down"],
      ["Volume", "Distribution", "High volume near highs"],
      ["AVWAP", "Below", "Anchor not accepted"],
      ["Supply", "High", "Seller not absorbed"],
      ["Safety", "GREEN", "No user lock"]
    ],
    proof: [
      ["Supply", "High"],
      ["AVWAP", "Failed"],
      ["OI", "Weak"],
      ["Volume", "Sell pressure"],
      ["State", "Reject"],
      ["Next", "Wait"]
    ],
    risk: [
      ["Trade", "Blocked"],
      ["Reason", "Supply"],
      ["R:R", "Invalid"],
      ["Trigger", "Anchor reclaim"],
      ["Mode", "Watch"]
    ],
    sources: [
      ["NSE", "GREEN"],
      ["BSE", "GREEN"],
      ["AMFI", "AMBER"],
      ["SHP", "GREEN"],
      ["SLB", "GREEN"],
      ["SEBI", "GREEN"]
    ],
    series: [70, 68, 66, 67, 64, 61, 60, 57, 55, 53, 51, 50, 48, 46, 45, 43]
  }
];

const fallbackCandidates = fallbackExamples.map((item) => ({
  ...item,
  state: "WAIT",
  stateTone: "warn",
  statusGroup: "wait",
  reason: "Demonstration layout only; no fresh structured market evidence is attached.",
  decisionTitle: "WAIT - DEMO DATA",
  decisionText: "Research-only fallback. Start the backend and verify source evidence.",
  nextConfirmation: "Load official source evidence and closed-bar proof.",
  invalidationCondition: "Demo evidence cannot support confirmation.",
  dataMode: "SYNTHETIC_TEST",
  trade: { entry: "-", stop: "-", target: "-" },
  quality: 0,
  metrics: [["Data", "DEMO_ONLY", "No market evidence attached"]],
  proof: [["Gate status", "NOT_EVALUATED"]],
  risk: [["Executable", "NO"], ["Reason", "DEMO_DATA"]],
  sources: [["Authority", "NA"], ["Freshness", "UNKNOWN"]]
}));

let candidates = fallbackCandidates;
const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";

const TOOL_REGISTRY = {
  m_factor: { title: "M-Factor", eyebrow: "INTRADAY F&O PRIORITY", purpose: "Rank eligible F&O names using the two canonical FUS-009 directional hypotheses. There is no second M-Factor score and no win-probability claim.", ceiling: "WAIT_SOURCE_ACTIVATION" },
  sector_scope: { title: "Sector Scope", eyebrow: "SECTOR MAP", purpose: "Show where relative strength concentrates. Attention only.", ceiling: "S2_CONTEXT_WAIT" },
  m_factor_history: { title: "M-Factor History", eyebrow: "POINT-IN-TIME FUS-009", purpose: "Compare immutable directional-strength snapshots without recomputing history from later data.", ceiling: "PIT_HISTORY_NOT_WIRED" },
  heatmap: { title: "Heatmap", eyebrow: "SECTOR X ACTIVITY", purpose: "Cross-section attention. Heat is not direction.", ceiling: "RESEARCH_SHADOW_ONLY" },
  index_dashboard: { title: "Index Dashboard", eyebrow: "NIFTY / BANKNIFTY", purpose: "Index context for eligible names. Not stock confirmation.", ceiling: "S2_CONTEXT_WAIT" },
  oi_analysis: { title: "OI Analysis", eyebrow: "NEUTRAL OPEN INTEREST", purpose: "Describe price and OI co-movement without naming institutional intent.", ceiling: "RESEARCH_SHADOW_ONLY" },
  oi_tracker: { title: "OI Tracker", eyebrow: "OI AND PCR PATH", purpose: "Show whether OI and PCR changes persist. Descriptive only.", ceiling: "WAIT_CHAIN" },
  strike_explorer: { title: "Strike Explorer", eyebrow: "OPTIONS SURFACE", purpose: "Inspect strikes only after the option surface passes quality checks.", ceiling: "WAIT_CHAIN" },
  expiry_prediction: { title: "Expiry Range Context", eyebrow: "ESTIMATE - NOT FORECAST", purpose: "Same-expiry research interval. Max pain is not a destination.", ceiling: "WAIT_CHAIN" },
  swing_finder: { title: "Swing Finder", eyebrow: "CLOSED SWING SCAN", purpose: "Closed multi-day structure candidates. Unclosed bars cannot confirm.", ceiling: "WAIT_DTO_UNAVAILABLE" },
  speculation_movers: { title: "Speculation Movers", eyebrow: "HIGH ACTIVITY", purpose: "Separate fast activity from delivery-backed accumulation. Attention only.", ceiling: "RESEARCH_SHADOW_ONLY" },
  trend_accumulation: { title: "Trend + Accumulation", eyebrow: "SWING PLUS EOD DELIVERY", purpose: "Closed structure plus official delivery. Direction, readiness and public state stay separate.", ceiling: "WAIT_SOURCE_ACTIVATION" },
  accumulation_signals: { title: "Accumulation Signals", eyebrow: "DELIVERY EVIDENCE", purpose: "Official delivery context for swing research. Not an intraday confirm.", ceiling: "WAIT_DTO_UNAVAILABLE" },
  multibagger_research: { title: "Multibagger Research", eyebrow: "LONG HORIZON", purpose: "Multi-week structure and ownership context. Targets are not promised.", ceiling: "LONG_HORIZON_UNCERTAINTY" }
};

const appState = {
  selectedSymbol: candidates[0].symbol,
  mode: "all",
  filter: "all",
  boardMode: "ALL",
  boardDirection: "ALL",
  activeView: "all-stocks",
  activeTool: "m_factor",
  timeframes: new Set(["30m", "1h", "4h", "1d", "1w"]),
  search: "",
  locked: false,
  parserSource: "nse_fno_ban",
  researchRecords: [],
  harmonicResults: [],
  generalAlerts: [],
  journalRecords: [],
  sourceHealth: [],
  institutionalConfig: null,
  institutionalSources: null,
  institutionalModels: null,
  institutionalReports: [],
  marketActivity: null,
  commodityContext: null,
  q5Selection: null,
  q5InspectorSection: "DECISION_PROOF",
  recoveryCooldownUntil: null,
  recoveryTimer: null
};

const els = {
  radarList: document.getElementById("radarList"),
  resultCount: document.getElementById("resultCount"),
  selectedType: document.getElementById("selectedType"),
  selectedSymbol: document.getElementById("selectedSymbol"),
  selectedState: document.getElementById("selectedState"),
  selectedReason: document.getElementById("selectedReason"),
  selectedPrice: document.getElementById("selectedPrice"),
  selectedMove: document.getElementById("selectedMove"),
  metricsGrid: document.getElementById("metricsGrid"),
  decisionTitle: document.getElementById("decisionTitle"),
  decisionText: document.getElementById("decisionText"),
  nextCheckValue: document.getElementById("nextCheckValue"),
  invalidationValue: document.getElementById("invalidationValue"),
  dataModeValue: document.getElementById("dataModeValue"),
  q5SelectionState: document.getElementById("q5SelectionState"),
  q5SelectionLabel: document.getElementById("q5SelectionLabel"),
  q5RadarAnswers: document.getElementById("q5RadarAnswers"),
  q5Inspector: document.getElementById("q5Inspector"),
  q5InspectorStatus: document.getElementById("q5InspectorStatus"),
  q5InspectorTabs: document.getElementById("q5InspectorTabs"),
  q5InspectorPanel: document.getElementById("q5InspectorPanel"),
  q5HistoryList: document.getElementById("q5HistoryList"),
  q5ValidationLock: document.getElementById("q5ValidationLock"),
  proofList: document.getElementById("proofList"),
  riskScore: document.getElementById("riskScore"),
  riskRing: document.getElementById("riskRing"),
  riskLines: document.getElementById("riskLines"),
  sourceGrid: document.getElementById("sourceGrid"),
  searchInput: document.getElementById("searchInput"),
  panicButton: document.getElementById("panicButton"),
  refreshButton: document.getElementById("refreshButton"),
  canvas: document.getElementById("marketPulse"),
  systemStatus: document.getElementById("systemStatus"),
  regimeStatus: document.getElementById("regimeStatus"),
  vixStatus: document.getElementById("vixStatus"),
  safetyStatus: document.getElementById("safetyStatus"),
  calendarStatus: document.getElementById("calendarStatus"),
  researchNote: document.getElementById("researchNote"),
  researchTags: document.getElementById("researchTags"),
  saveResearchButton: document.getElementById("saveResearchButton"),
  researchStatus: document.getElementById("researchStatus"),
  researchList: document.getElementById("researchList"),
  researchCount: document.getElementById("researchCount"),
  mlRunCount: document.getElementById("mlRunCount"),
  mlCandidateCount: document.getElementById("mlCandidateCount"),
  mlCaptureStatus: document.getElementById("mlCaptureStatus"),
  harmonicSymbolInput: document.getElementById("harmonicSymbolInput"),
  harmonicTimeframeSelect: document.getElementById("harmonicTimeframeSelect"),
  harmonicUseStored: document.getElementById("harmonicUseStored"),
  harmonicScanButton: document.getElementById("harmonicScanButton"),
  advancedHarmonicButton: document.getElementById("advancedHarmonicButton"),
  harmonicBacktestButton: document.getElementById("harmonicBacktestButton"),
  harmonicScanStatus: document.getElementById("harmonicScanStatus"),
  sourceRegistryStatus: document.getElementById("sourceRegistryStatus"),
  parquetStatus: document.getElementById("parquetStatus"),
  sourceMonitorStatus: document.getElementById("sourceMonitorStatus"),
  gateReadinessStatus: document.getElementById("gateReadinessStatus"),
  scannerSchedulerStatus: document.getElementById("scannerSchedulerStatus"),
  rawArchiveStatus: document.getElementById("rawArchiveStatus"),
  riskSettingsStatus: document.getElementById("riskSettingsStatus"),
  universeStatus: document.getElementById("universeStatus"),
  officialContextStatus: document.getElementById("officialContextStatus"),
  recoveryDialog: document.getElementById("recoveryDialog"),
  recoveryForm: document.getElementById("recoveryForm"),
  recoveryClose: document.getElementById("recoveryClose"),
  recoveryReason: document.getElementById("recoveryReason"),
  recoveryStatus: document.getElementById("recoveryStatus"),
  recoverySubmit: document.getElementById("recoverySubmit"),
  parserSourceSelect: document.getElementById("parserSourceSelect"),
  parserRefreshButton: document.getElementById("parserRefreshButton"),
  scannerRunButton: document.getElementById("scannerRunButton"),
  parserGrid: document.getElementById("parserGrid"),
  advancedHarmonicBox: document.getElementById("advancedHarmonicBox"),
  harmonicResultList: document.getElementById("harmonicResultList"),
  generalAlertCount: document.getElementById("generalAlertCount"),
  generalAlertList: document.getElementById("generalAlertList"),
  refreshAlertsButton: document.getElementById("refreshAlertsButton"),
  journalCount: document.getElementById("journalCount"),
  journalCreateForm: document.getElementById("journalCreateForm"),
  journalOutcomeForm: document.getElementById("journalOutcomeForm"),
  journalSymbol: document.getElementById("journalSymbol"),
  journalSetup: document.getElementById("journalSetup"),
  journalMode: document.getElementById("journalMode"),
  journalDirection: document.getElementById("journalDirection"),
  journalDecisionState: document.getElementById("journalDecisionState"),
  journalQuantity: document.getElementById("journalQuantity"),
  journalEntryPrice: document.getElementById("journalEntryPrice"),
  journalStopPrice: document.getElementById("journalStopPrice"),
  journalOpenedAt: document.getElementById("journalOpenedAt"),
  journalNotes: document.getElementById("journalNotes"),
  journalRecordSelect: document.getElementById("journalRecordSelect"),
  journalOutcomeState: document.getElementById("journalOutcomeState"),
  journalExitPrice: document.getElementById("journalExitPrice"),
  journalPnl: document.getElementById("journalPnl"),
  journalRMultiple: document.getElementById("journalRMultiple"),
  journalClosedAt: document.getElementById("journalClosedAt"),
  journalOutcomeNotes: document.getElementById("journalOutcomeNotes"),
  journalStatus: document.getElementById("journalStatus"),
  journalList: document.getElementById("journalList"),
  institutionalForm: document.getElementById("institutionalForm"),
  institutionalState: document.getElementById("institutionalState"),
  institutionalSourceCount: document.getElementById("institutionalSourceCount"),
  institutionalModelCount: document.getElementById("institutionalModelCount"),
  institutionalAccount: document.getElementById("institutionalAccount"),
  institutionalAuditCount: document.getElementById("institutionalAuditCount"),
  institutionalClassification: document.getElementById("institutionalClassification"),
  institutionalScore: document.getElementById("institutionalScore"),
  institutionalReason: document.getElementById("institutionalReason"),
  institutionalMarker: document.getElementById("institutionalMarker"),
  institutionalEvaluateButton: document.getElementById("institutionalEvaluateButton"),
  marketActivityRefresh: document.getElementById("marketActivityRefresh"),
  marketActivityStatus: document.getElementById("marketActivityStatus"),
  marketActivityMeta: document.getElementById("marketActivityMeta"),
  marketActivityList: document.getElementById("marketActivityList"),
  commodityContextStatus: document.getElementById("commodityContextStatus"),
  commodityContextMeta: document.getElementById("commodityContextMeta"),
  commodityContextList: document.getElementById("commodityContextList"),
  maturityLadder: document.getElementById("maturityLadder"),
  maturityLadderMeta: document.getElementById("maturityLadderMeta"),
  maturityLadderCounts: document.getElementById("maturityLadderCounts"),
  sourceHealthLadderMeta: document.getElementById("sourceHealthLadderMeta"),
  sourceHealthLadderCounts: document.getElementById("sourceHealthLadderCounts"),
  liveDecisionMeta: document.getElementById("liveDecisionMeta"),
  liveDecisionList: document.getElementById("liveDecisionList"),
  liveDecisionRefresh: document.getElementById("liveDecisionRefresh"),
  lockBadge: document.getElementById("lockBadge"),
  toolHero: document.getElementById("toolHero"),
  toolEyebrow: document.getElementById("toolEyebrow"),
  toolTitle: document.getElementById("toolTitle"),
  toolPurpose: document.getElementById("toolPurpose"),
  toolState: document.getElementById("toolState"),
  toolContent: document.getElementById("toolContent"),
  optionLab: document.getElementById("optionLab"),
  allStockContent: document.getElementById("allStockContent"),
  allStockCount: document.getElementById("allStockCount"),
  allStockSummary: document.getElementById("allStockSummary"),
  allStockMode: document.getElementById("allStockMode"),
  allStockDirection: document.getElementById("allStockDirection"),
  headerHistory: document.getElementById("headerHistory"),
  previewRefresh: document.getElementById("previewRefresh")
};

function formatApiErrorDetail(payload, fallback) {
  const detail = payload?.detail;
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg || item?.message)
      .filter(Boolean);
    if (messages.length) return messages.join(" ");
  }
  return fallback;
}

async function fetchJson(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body
  });
  if (!response.ok) {
    let payload = null;
    try {
      payload = await response.json();
    } catch (_error) {
      payload = null;
    }
    const error = new Error(formatApiErrorDetail(payload, `API ${path} failed with ${response.status}`));
    error.status = response.status;
    throw error;
  }
  return response.json();
}

async function fetchOptionalJson(path) {
  const response = await fetch(`${API_BASE}${path}`, { headers: { Accept: "application/json" } });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`API ${path} failed with ${response.status}`);
  return response.json();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;"
  })[character]);
}

function normalizeMetric(row) {
  return Array.isArray(row) ? row : [row.label, row.value, row.note];
}

function normalizePair(row) {
  return Array.isArray(row) ? row : [row.label, row.value];
}

function canonicalSelectionState(value) {
  return window.TrendForgeQ5.canonicalState(value);
}

function selectionTone(state) {
  if (state === "CONFIRMED") return "good";
  if (state === "REJECT") return "bad";
  return "warn";
}

function selectionStatusGroup(state) {
  return window.TrendForgeQ5.statusGroup(state);
}

function sanitizeDecisionText(value) {
  return String(value || "")
    .replace(/execute/gi, "Review")
    .replace(/position size/gi, "research geometry")
    .replace(/lot sizing/gi, "contract identity");
}

function normalizeCandidate(row) {
  const state = canonicalSelectionState(row.state);
  const legacyReady = String(row.state || "").toUpperCase().startsWith("READY");
  const decisionText = legacyReady
    ? "Legacy result is research evidence only. Q5 confirmation requires closed-bar and source gates."
    : sanitizeDecisionText(row.decisionText);
  return {
    ...row,
    state,
    quantity: 0,
    stateTone: selectionTone(state),
    statusGroup: selectionStatusGroup(state),
    decisionTitle: legacyReady ? "WATCH - LEGACY RESULT" : row.decisionTitle,
    decisionText,
    nextConfirmation: row.nextConfirmation || "Review missing proof in the evidence inspector.",
    invalidationCondition: row.invalidationCondition || "See evidence and source-health conflicts.",
    dataMode: row.dataMode || "RESEARCH",
    trade: { entry: row.trade?.entry || "-", stop: row.trade?.stop || "-", target: row.trade?.target || "-" },
    metrics: (row.metrics || []).map(normalizeMetric),
    proof: (row.proof || []).map(normalizePair),
    risk: (row.risk || []).map(normalizePair),
    sources: (row.sources || []).map(normalizePair)
  };
}

function harmonicTone(finalState) {
  return selectionTone(canonicalSelectionState(finalState));
}

function harmonicStatusGroup(finalState) {
  return selectionStatusGroup(canonicalSelectionState(finalState));
}

function formatOptionalPrice(value) {
  return typeof value === "number" ? value.toFixed(2) : "WAIT";
}

function harmonicPatternToCandidate(pattern, scanPayload) {
  const pointPrices = (pattern.points || []).map((point) => Math.round(point.price));
  const latestPoint = pattern.points?.[pattern.points.length - 1];
  const latestPrice = latestPoint ? latestPoint.price : 0;
  return normalizeCandidate({
    symbol: pattern.symbol,
    type: "harmonic",
    state: pattern.finalState,
    stateTone: harmonicTone(pattern.finalState),
    statusGroup: harmonicStatusGroup(pattern.finalState),
    setup: `${pattern.patternName} ${pattern.direction} harmonic`,
    timeframe: [pattern.timeframe],
    price: latestPrice ? latestPrice.toFixed(2) : "WAIT",
    move: "real scan",
    reason: (pattern.reasons || []).slice(0, 2).join("; ") || pattern.confirmationState,
    decisionTitle: `${pattern.finalState} - ${pattern.patternName}`,
    decisionText:
      "Real harmonic scan saved. CONFIRMED is blocked unless closed-bar, source, and independent-family gates pass.",
    trade: {
      entry: latestPrice ? latestPrice.toFixed(2) : "WAIT",
      stop: formatOptionalPrice(pattern.invalidationPrice),
      target: `${formatOptionalPrice(pattern.target1)} / ${formatOptionalPrice(pattern.target2)}`
    },
    quality: pattern.confidence,
    metrics: [
      { label: "Pattern", value: pattern.patternName, note: "Detected from stored/live candles" },
      { label: "Direction", value: pattern.direction, note: "Harmonic bias" },
      { label: "Candles", value: String(scanPayload.candleCount), note: scanPayload.source }
    ],
    proof: pattern.gates || [],
    risk: [
      { label: "Final State", value: pattern.finalState },
      { label: "Trust", value: scanPayload.trustLevel }
    ],
    sources: [
      { label: "OHLCV", value: scanPayload.source },
      { label: "Detector", value: pattern.sourceEngine }
    ],
    series: pointPrices.length > 1 ? pointPrices : [latestPrice, latestPrice]
  });
}

function renderCommandBar(commandBar) {
  if (!commandBar) return;
  els.systemStatus.textContent = commandBar.system;
  els.regimeStatus.textContent = commandBar.regime;
  els.vixStatus.textContent = commandBar.indiaVix;
  els.safetyStatus.textContent = commandBar.safety;
}

async function loadApiData() {
  try {
    const productOwnsSelection = productFixtureOwnsChrome();
    const [commandBar, radarRows, safety, marketContext, calendar, sourceHealth, compilerReport, liveBatch] = await Promise.all([
      fetchJson("/api/command-bar"),
      productOwnsSelection ? Promise.resolve(null) : fetchJson("/api/radar"),
      fetchJson("/api/safety/status"),
      fetchOptionalJson("/api/context/market/latest"),
      fetchJson("/api/calendar/status"),
      fetchJson("/api/source-health"),
      fetchOptionalJson("/api/source-inventory/compiler-report"),
      productOwnsSelection ? Promise.resolve(null) : fetchOptionalJson("/api/v1/selection/live")
    ]);
    if (!productOwnsSelection) candidates = radarRows.map(normalizeCandidate);
    appState.sourceHealth = sourceHealth;
    renderMaturityLadder(compilerReport);
    if (!productOwnsSelection) renderLiveDecision(liveBatch);
    renderCommandBar(commandBar);
    if (marketContext) {
      els.regimeStatus.textContent = marketContext.state;
      els.vixStatus.textContent = `${marketContext.indiaVix} ${marketContext.vixState}`;
    } else {
      els.regimeStatus.textContent = "WAIT_CONTEXT";
      els.vixStatus.textContent = "WAIT_DATA";
    }
    applySafetyStatus(safety);
    els.calendarStatus.textContent = calendar.state;
    els.calendarStatus.title = `${calendar.tradingDate}: ${calendar.reason}`;
    ensureSelectionVisible();
    render();
    seedJournalForm();
    loadMlSnapshotStatus();
  } catch (error) {
    console.warn("TrendForge API unavailable; using static fallback data.", error);
  }
}

async function loadMlSnapshotStatus() {
  try {
    const status = await fetchJson("/api/ml-snapshots/status");
    els.mlRunCount.textContent = status.totalRuns;
    els.mlCandidateCount.textContent = status.totalCandidates;
    const latest = status.latestRun;
    els.mlCaptureStatus.textContent = latest
      ? `Auto-saved latest full scan: ${latest.candidateCount} candidates at ${new Date(latest.createdAt).toLocaleString()}.`
      : "No full scan captured yet.";
    els.mlCaptureStatus.classList.toggle("good-text", Boolean(latest));
    els.mlCaptureStatus.classList.toggle("bad-text", false);
  } catch (error) {
    els.mlRunCount.textContent = "0";
    els.mlCandidateCount.textContent = "0";
    els.mlCaptureStatus.textContent = "ML auto-capture backend unavailable.";
    els.mlCaptureStatus.classList.toggle("good-text", false);
    els.mlCaptureStatus.classList.toggle("bad-text", true);
  }
}

function localDateTimeInputValue(date = new Date()) {
  const shifted = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return shifted.toISOString().slice(0, 16);
}

function inputIsoValue(element) {
  return element.value ? new Date(element.value).toISOString() : null;
}

function optionalNumber(element) {
  return element.value === "" ? null : Number(element.value);
}

async function loadOperationalRecords() {
  try {
    const [alerts, journal] = await Promise.all([
      fetchJson("/api/alerts"),
      fetchJson("/api/journal")
    ]);
    appState.generalAlerts = alerts;
    appState.journalRecords = journal;
    renderGeneralAlerts();
    renderJournalRecords();
  } catch (error) {
    els.generalAlertList.innerHTML = `<div class="operational-row"><strong>Alerts unavailable</strong><span>${escapeHtml(error.message)}</span></div>`;
    els.journalList.innerHTML = `<div class="operational-row"><strong>Journal unavailable</strong><span>${escapeHtml(error.message)}</span></div>`;
  }
}

function renderGeneralAlerts() {
  const rows = appState.generalAlerts || [];
  els.generalAlertCount.textContent = rows.filter((row) => !row.acknowledged).length;
  els.generalAlertList.innerHTML = "";
  if (!rows.length) {
    els.generalAlertList.innerHTML = `<div class="operational-row"><strong>No alerts</strong><span>System clear</span></div>`;
    return;
  }
  rows.slice(0, 12).forEach((alert) => {
    const row = document.createElement("article");
    row.className = `operational-row severity-${String(alert.severity || "INFO").toLowerCase()} ${alert.acknowledged ? "acknowledged" : ""}`;
    const riskText = Object.entries(alert.risk || {})
      .slice(0, 3)
      .map(([key, value]) => `${key}: ${value}`)
      .join(" | ");
    row.innerHTML = `
      <div class="operational-row-head">
        <strong>${escapeHtml(alert.alertType)}</strong>
        <span class="state-chip ${alert.severity === "CRITICAL" ? "bad" : alert.severity === "WARN" ? "warn" : "info"}">${escapeHtml(alert.state)}</span>
      </div>
      <span>${escapeHtml(alert.symbol || "SYSTEM")} - ${escapeHtml(alert.reason)}</span>
      <small>${escapeHtml(riskText || new Date(alert.createdAt).toLocaleString())}</small>
    `;
    if (!alert.acknowledged) {
      const acknowledge = document.createElement("button");
      acknowledge.type = "button";
      acknowledge.className = "row-icon-action";
      acknowledge.title = "Acknowledge alert";
      acknowledge.setAttribute("aria-label", `Acknowledge ${alert.alertType}`);
      acknowledge.innerHTML = `<i data-lucide="check" aria-hidden="true"></i>`;
      acknowledge.addEventListener("click", async () => {
        await fetchJson(`/api/alerts/${alert.id}/acknowledge`, { method: "PUT" });
        await loadOperationalRecords();
      });
      row.appendChild(acknowledge);
    }
    els.generalAlertList.appendChild(row);
  });
  if (window.lucide) window.lucide.createIcons();
}

function renderJournalRecords() {
  const rows = appState.journalRecords || [];
  els.journalCount.textContent = rows.length;
  els.journalRecordSelect.innerHTML = rows
    .map((row) => `<option value="${row.id}">${escapeHtml(row.symbol)} - ${escapeHtml(row.outcomeState)}</option>`)
    .join("");
  els.journalOutcomeForm.classList.toggle("is-disabled", rows.length === 0);
  els.journalOutcomeForm.querySelectorAll("input, select, textarea, button").forEach((control) => {
    control.disabled = rows.length === 0;
  });
  els.journalList.innerHTML = "";
  if (!rows.length) {
    els.journalList.innerHTML = `<div class="operational-row"><strong>No journal records</strong><span>Manual outcomes will appear here.</span></div>`;
    return;
  }
  rows.slice(0, 10).forEach((record) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "operational-row journal-row";
    row.innerHTML = `
      <div class="operational-row-head">
        <strong>${escapeHtml(record.symbol)} - ${escapeHtml(record.setup)}</strong>
        <span class="state-chip ${record.outcomeState === "WIN" ? "good" : record.outcomeState === "LOSS" ? "bad" : "info"}">${escapeHtml(record.outcomeState)}</span>
      </div>
      <span>${escapeHtml(record.mode)} ${escapeHtml(record.direction)} | ${escapeHtml(record.decisionState)}</span>
      <small>${record.rMultiple == null ? "R pending" : `${escapeHtml(record.rMultiple)}R`} | ${record.pnl == null ? "P&L pending" : escapeHtml(record.pnl)}</small>
    `;
    row.addEventListener("click", () => {
      els.journalRecordSelect.value = String(record.id);
    });
    els.journalList.appendChild(row);
  });
}

async function createJournalRecord() {
  const payload = {
    symbol: els.journalSymbol.value.trim(),
    mode: els.journalMode.value,
    direction: els.journalDirection.value,
    decisionState: els.journalDecisionState.value.trim(),
    setup: els.journalSetup.value.trim(),
    quantity: 0,
    entryPrice: optionalNumber(els.journalEntryPrice),
    stopPrice: optionalNumber(els.journalStopPrice),
    openedAt: inputIsoValue(els.journalOpenedAt),
    notes: els.journalNotes.value.trim()
  };
  Object.keys(payload).forEach((key) => payload[key] == null && delete payload[key]);
  try {
    await fetchJson("/api/journal", { method: "POST", body: JSON.stringify(payload) });
    els.journalStatus.textContent = "Journal record saved.";
    els.journalCreateForm.reset();
    seedJournalForm();
    await loadOperationalRecords();
  } catch (error) {
    els.journalStatus.textContent = error.message;
  }
}

async function updateJournalRecordOutcome() {
  const entryId = els.journalRecordSelect.value;
  if (!entryId) return;
  const payload = {
    outcomeState: els.journalOutcomeState.value,
    exitPrice: optionalNumber(els.journalExitPrice),
    closedAt: inputIsoValue(els.journalClosedAt),
    pnl: optionalNumber(els.journalPnl),
    rMultiple: optionalNumber(els.journalRMultiple),
    notes: els.journalOutcomeNotes.value.trim() || null
  };
  Object.keys(payload).forEach((key) => payload[key] == null && delete payload[key]);
  try {
    await fetchJson(`/api/journal/${entryId}/outcome`, { method: "PUT", body: JSON.stringify(payload) });
    els.journalStatus.textContent = "Journal outcome updated.";
    els.journalOutcomeForm.reset();
    els.journalClosedAt.value = localDateTimeInputValue();
    await loadOperationalRecords();
  } catch (error) {
    els.journalStatus.textContent = error.message;
  }
}

function seedJournalForm() {
  const selected = getSelected();
  els.journalSymbol.value = selected.symbol;
  els.journalSetup.value = selected.setup;
  els.journalDecisionState.value = canonicalSelectionState(selected.state);
  els.journalQuantity.value = "0";
  els.journalOpenedAt.value = localDateTimeInputValue();
  els.journalClosedAt.value = localDateTimeInputValue();
}

async function loadFunctionStatus() {
  try {
    const sourceKey = appState.parserSource;
    const cftcAnalyticsRequest = sourceKey === "cftc_cot"
      ? fetchJson("/api/cftc/analytics?market=GOLD&limit=1")
      : Promise.resolve(null);
    const isBseOffer = ["bse_buyback_tender", "bse_takeover_open_offer"].includes(sourceKey);
    const bseDocumentsRequest = isBseOffer
      ? fetchJson(`/api/bse-offers/xbrl/documents?sourceKey=${encodeURIComponent(sourceKey)}&limit=5`)
      : Promise.resolve([]);
    const bseEventsRequest = isBseOffer
      ? fetchJson(`/api/bse-offers/events?sourceKey=${encodeURIComponent(sourceKey)}&currentOnly=true&limit=5`)
      : Promise.resolve([]);
    const [sources, parquet, monitor, gates, parserResults, domainRows, archiveRows, parserOutputs, freshnessRows, replacementMap, scanner, riskSettings, safety, universe, officialContext, cftcAnalytics, bseDocuments, bseEvents] = await Promise.all([
      fetchJson("/api/sources/registry"),
      fetchJson("/api/parquet/status"),
      fetchJson("/api/source-monitor/scheduler/status"),
      fetchJson("/api/gates/readiness"),
      fetchJson(`/api/source-parser/results?sourceKey=${encodeURIComponent(sourceKey)}&limit=5`),
      fetchJson(`/api/source-parser/domain-rows?sourceKey=${encodeURIComponent(sourceKey)}&limit=20`),
      fetchJson(`/api/raw-source-archive?sourceKey=${encodeURIComponent(sourceKey)}&limit=5`),
      fetchJson(`/api/source-parser/outputs?sourceKey=${encodeURIComponent(sourceKey)}&limit=5`),
      fetchJson("/api/source-freshness-status"),
      fetchJson("/api/source-replacement-map"),
      fetchJson("/api/scanner/scheduler/status"),
      fetchJson("/api/settings/risk"),
      fetchJson("/api/safety/status"),
      fetchJson("/api/universe/status"),
      fetchJson("/api/context/official/status"),
      cftcAnalyticsRequest,
      bseDocumentsRequest,
      bseEventsRequest
    ]);
    const greenSources = sources.filter((row) => row.status === "GREEN").length;
    els.sourceRegistryStatus.textContent = `${greenSources}/${sources.length} green`;
    els.parquetStatus.textContent = parquet.available
      ? `${parquet.fileCount} files`
      : "unavailable";
    els.sourceMonitorStatus.textContent = monitor.running
      ? `running ${Math.round(monitor.intervalSeconds / 60)}m`
      : monitor.lastRunAt
        ? "checked"
        : "idle";
    const blockedGates = (gates.gates || []).filter((gate) => gate.tradeGateEffect !== "CAN_CONFIRM").length;
    els.gateReadinessStatus.textContent = blockedGates ? `${blockedGates} blocked` : "ready";
    els.scannerSchedulerStatus.textContent = scanner.running
      ? `running ${Math.round(scanner.intervalSeconds / 60)}m`
      : scanner.latestRun
        ? scanner.latestRun.status.toLowerCase()
        : "idle";
    els.rawArchiveStatus.textContent = `${archiveRows.length} rows`;
    els.riskSettingsStatus.textContent = `INR ${Number(riskSettings.account_size).toLocaleString("en-IN")}`;
    els.universeStatus.textContent = `${universe.instrumentCount} / ${universe.nifty500MembershipCount}`;
    els.officialContextStatus.textContent = officialContext.marketContextReady
      ? `${officialContext.nifty_count} sessions`
      : `WAIT ${officialContext.nifty_count}/200`;
    applySafetyStatus(safety);
    renderParserDrilldown(parserResults, domainRows.rows || [], archiveRows, parserOutputs, freshnessRows, replacementMap, cftcAnalytics, bseDocuments, bseEvents);
  } catch (error) {
    els.sourceRegistryStatus.textContent = "offline";
    els.parquetStatus.textContent = "offline";
    els.sourceMonitorStatus.textContent = "offline";
    els.gateReadinessStatus.textContent = "offline";
    els.scannerSchedulerStatus.textContent = "offline";
    els.rawArchiveStatus.textContent = "offline";
    els.riskSettingsStatus.textContent = "offline";
    els.universeStatus.textContent = "offline";
    els.officialContextStatus.textContent = "offline";
    els.parserGrid.innerHTML = `<div class="parser-row"><strong>offline</strong><span>parser drilldown unavailable</span><span>WAIT</span></div>`;
  }
}

function applySafetyStatus(safety) {
  appState.locked = Boolean(safety.locked) || Number(safety.riskMultiplier) === 0;
  els.safetyStatus.textContent = safety.state;
  els.safetyStatus.title = `${safety.reason} ${safety.nextAllowedAction}`;
  els.panicButton.classList.toggle("active", appState.locked);
  els.panicButton.querySelector("span").textContent = appState.locked ? "Review Safety" : "Lock Trading";
  render();
}

async function activatePanicLock() {
  const safety = await fetchJson("/api/safety/panic-lock", {
    method: "POST",
    body: JSON.stringify({ reason: "Manual panic lock activated from the dashboard.", cooldownMinutes: 30 })
  });
  applySafetyStatus(safety);
}

function recoveryInputs() {
  return Array.from(els.recoveryForm.querySelectorAll('input[name="recovery"]'));
}

function recoveryCooldownRemainingMs() {
  if (!appState.recoveryCooldownUntil) return 0;
  return Math.max(0, appState.recoveryCooldownUntil.getTime() - Date.now());
}

function formatRecoveryCountdown(remainingMs) {
  const totalSeconds = Math.ceil(remainingMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function updateRecoveryReadiness() {
  const inputs = recoveryInputs();
  const firstUnchecked = inputs.find((input) => !input.checked);
  const noteValid = els.recoveryReason.value.trim().length >= 3;
  const remainingMs = recoveryCooldownRemainingMs();
  const ready = !firstUnchecked && noteValid && remainingMs === 0;

  els.recoverySubmit.disabled = !ready;
  if (remainingMs > 0) {
    const endTime = appState.recoveryCooldownUntil.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit"
    });
    els.recoveryStatus.textContent = `Safety cooldown ends at ${endTime}. ${formatRecoveryCountdown(remainingMs)} remaining.`;
  } else if (firstUnchecked) {
    els.recoveryStatus.textContent = "Accept all five recovery acknowledgements to continue.";
  } else if (!noteValid) {
    els.recoveryStatus.textContent = "Enter a review note of at least 3 characters.";
  } else {
    els.recoveryStatus.textContent = "Recovery requirements complete. Unlock request is available.";
  }
  return { ready, firstUnchecked };
}

function stopRecoveryTimer() {
  if (appState.recoveryTimer) {
    window.clearInterval(appState.recoveryTimer);
    appState.recoveryTimer = null;
  }
}

async function prepareRecoveryDialog() {
  stopRecoveryTimer();
  appState.recoveryCooldownUntil = null;
  els.recoveryStatus.textContent = "Checking active safety lock...";
  els.recoverySubmit.disabled = true;
  try {
    const events = await fetchJson("/api/safety/events?active=true&limit=10");
    const cooldowns = events
      .filter((event) => event.active && event.cooldown_until)
      .map((event) => new Date(event.cooldown_until))
      .filter((value) => !Number.isNaN(value.getTime()) && value.getTime() > Date.now());
    if (cooldowns.length) {
      appState.recoveryCooldownUntil = new Date(Math.max(...cooldowns.map((value) => value.getTime())));
    }
  } catch (error) {
    els.recoveryStatus.textContent = error.message || "Could not read the active safety lock.";
    return;
  }
  updateRecoveryReadiness();
  appState.recoveryTimer = window.setInterval(updateRecoveryReadiness, 1000);
}

async function submitRecoveryReview() {
  const readiness = updateRecoveryReadiness();
  if (!readiness.ready) {
    readiness.firstUnchecked?.focus();
    return;
  }
  const checklist = recoveryInputs().map((input) => input.checked);
  els.recoverySubmit.disabled = true;
  els.recoverySubmit.textContent = "Checking...";
  try {
    const safety = await fetchJson("/api/safety/unlock", {
      method: "POST",
      body: JSON.stringify({ recoveryChecklist: checklist, reason: els.recoveryReason.value.trim() })
    });
    applySafetyStatus(safety);
    if (!appState.locked) {
      stopRecoveryTimer();
      els.recoveryDialog.close();
      els.recoveryForm.reset();
    } else {
      els.recoveryStatus.textContent = safety.reason;
    }
  } catch (error) {
    els.recoveryStatus.textContent = error.message || "Safety lock remains active.";
  } finally {
    els.recoverySubmit.textContent = "Request Unlock";
    if (els.recoveryDialog.open) updateRecoveryReadiness();
  }
}

function renderParserDrilldown(parserResults, domainRows, archiveRows, parserOutputs = [], freshnessRows = [], replacementMap = [], cftcAnalytics = null, bseDocuments = [], bseEvents = []) {
  const latest = parserResults[0];
  const archive = archiveRows[0];
  const output = parserOutputs[0];
  const freshness = freshnessRows.find((row) => row.source_key === appState.parserSource);
  const replacement = replacementMap.find((row) => row.source_key === appState.parserSource);
  const rows = [
    {
      label: "Parser",
      value: latest ? latest.parserState : "MISSING",
      note: latest ? `${latest.recordCount} rows` : "run parse"
    },
    {
      label: "Data Date",
      value: latest?.dataDate || "WAIT",
      note: latest?.summary || "no parser result"
    },
    {
      label: "Domain Rows",
      value: String(domainRows.length),
      note: "row-level table"
    },
    {
      label: "Output Status",
      value: output?.parser_status || "WAIT",
      note: output?.freshness_status || "no artifact"
    },
    {
      label: "Source Role",
      value: replacement?.source_role || "UNMAPPED",
      note: replacement?.can_unlock_ready ? "can unlock" : "cannot unlock alone"
    },
    {
      label: "Freshness",
      value: freshness?.is_fresh ? "FRESH" : "WAIT",
      note: freshness?.reason || "no freshness row"
    },
    {
      label: "Raw Hash",
      value: archive?.content_hash ? archive.content_hash.slice(0, 10) : "WAIT",
      note: archive?.parser_state_after_parse || "not archived"
    }
  ];
  if (cftcAnalytics) {
    const cot = cftcAnalytics.rows?.[0];
    rows.push(
      {
        label: "COT Freshness",
        value: cftcAnalytics.state,
        note: cftcAnalytics.sourceEvidence?.reason || "official source state unavailable"
      },
      {
        label: "COT Context",
        value: cot?.positionState || cftcAnalytics.state,
        note: cot ? `${cot.reportDate} weekly delayed` : "historical rows required"
      },
      {
        label: "MM Change 1W",
        value: cot?.managedMoneyNetChange1w == null ? "WAIT" : Number(cot.managedMoneyNetChange1w).toLocaleString("en-IN"),
        note: cot?.contractMarketCode || "official contract code unavailable"
      },
      {
        label: "Crowding",
        value: cot?.crowdingState || "WAIT",
        note: cot?.managedMoneyPercentile52w == null ? "52w history incomplete" : `52w percentile ${Math.round(cot.managedMoneyPercentile52w * 100)}%`
      },
      {
        label: "COT Proof Role",
        value: "CONTEXT_ONLY",
        note: "cannot produce CONFIRMED"
      }
    );
  }
  if (bseDocuments.length || bseEvents.length) {
    const document = bseDocuments[0];
    const event = bseEvents[0];
    rows.push(
      {
        label: "XBRL Detail",
        value: document?.parser_state || "WAIT_BSE_DETAIL",
        note: document ? `${document.phase} ${document.data_date || "date missing"}` : "linked terms not fetched"
      },
      {
        label: "Offer Anchor",
        value: event?.offer_price == null ? "WAIT" : `INR ${Number(event.offer_price).toLocaleString("en-IN")}`,
        note: event ? `${event.company} | ${Number(event.quantity || 0).toLocaleString("en-IN")} shares` : "structured terms required"
      },
      {
        label: "Revision",
        value: event?.revision_status || "WAIT",
        note: event?.document_hash ? event.document_hash.slice(0, 10) : "no current XBRL hash"
      },
      {
        label: "Trade Role",
        value: "CONTEXT_ONLY",
        note: "price acceptance and structure still required"
      }
    );
  }
  els.parserGrid.innerHTML = rows
    .map((row) => `<div class="parser-row"><strong>${escapeHtml(row.label)}</strong><span>${escapeHtml(row.value)}</span><span>${escapeHtml(row.note)}</span></div>`)
    .join("");
}

async function refreshSelectedParser() {
  const sourceKey = appState.parserSource;
  els.parserGrid.innerHTML = `<div class="parser-row"><strong>${escapeHtml(sourceKey)}</strong><span>running parser</span><span>WAIT</span></div>`;
  try {
    await fetchJson(`/api/source-parser/run?sourceKey=${encodeURIComponent(sourceKey)}`, { method: "POST" });
    if (["bse_buyback_tender", "bse_takeover_open_offer"].includes(sourceKey)) {
      await fetchJson(`/api/bse-offers/xbrl/refresh?sourceKey=${encodeURIComponent(sourceKey)}&maxDocuments=5`, { method: "POST" });
    }
    await loadFunctionStatus();
  } catch (error) {
    els.parserGrid.innerHTML = `<div class="parser-row"><strong>${escapeHtml(sourceKey)}</strong><span>parse failed</span><span>BLOCK</span></div>`;
  }
}

async function runScannerOnce() {
  els.scannerSchedulerStatus.textContent = "running";
  try {
    const result = await fetchJson("/api/scanner/run-once?universe=WATCHLIST_ONLY&fetch=false", { method: "POST" });
    els.scannerSchedulerStatus.textContent = `${result.status.toLowerCase()} ${result.candidateCount || 0}`;
    await loadApiData();
    await loadFunctionStatus();
    await loadMlSnapshotStatus();
  } catch (error) {
    els.scannerSchedulerStatus.textContent = "error";
  }
}

function parseTags(value) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function localResearchKey() {
  return "trendforge.researchRecords";
}

function loadLocalResearchRecords() {
  try {
    return JSON.parse(localStorage.getItem(localResearchKey()) || "[]");
  } catch {
    return [];
  }
}

function saveLocalResearchRecord(record) {
  const rows = loadLocalResearchRecords();
  rows.unshift(record);
  localStorage.setItem(localResearchKey(), JSON.stringify(rows.slice(0, 100)));
  return rows;
}

async function loadResearchRecords() {
  try {
    appState.researchRecords = await fetchJson("/api/research-records");
    setResearchStatus("Research vault synced from SQLite.", "good");
  } catch (error) {
    appState.researchRecords = loadLocalResearchRecords();
    setResearchStatus("Backend vault unavailable. Showing local browser records only.", "bad");
  }
  renderResearchVault();
}

function setResearchStatus(message, tone = "") {
  els.researchStatus.textContent = message;
  els.researchStatus.classList.toggle("good-text", tone === "good");
  els.researchStatus.classList.toggle("bad-text", tone === "bad");
}

async function saveResearchSnapshot() {
  const item = getSelected();
  const note = els.researchNote.value.trim();
  const tags = parseTags(els.researchTags.value);
  const payload = {
    symbol: item.symbol,
    title: `${item.symbol} - ${appState.locked ? "LOCKED_NO_TRADE" : item.state}`,
    note,
    tags
  };

  try {
    const saved = await fetchJson("/api/research-records", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    appState.researchRecords.unshift(saved);
    setResearchStatus(`Saved ${item.symbol} to SQLite research vault.`, "good");
  } catch (error) {
    const fallbackRecord = {
      id: Date.now(),
      symbol: item.symbol,
      title: payload.title,
      note,
      tags,
      createdAt: new Date().toISOString(),
      candidate: item,
      commandBar: {
        system: els.systemStatus.textContent,
        regime: els.regimeStatus.textContent,
        indiaVix: els.vixStatus.textContent,
        safety: els.safetyStatus.textContent
      },
      sourceHealth: item.sources.map(([name, state]) => ({ name, state }))
    };
    appState.researchRecords = saveLocalResearchRecord(fallbackRecord);
    setResearchStatus(`Saved ${item.symbol} to local browser storage only.`, "bad");
  }

  els.researchNote.value = "";
  els.researchTags.value = "";
  renderResearchVault();
  loadMlSnapshotStatus();
}

function toneClass(tone) {
  return tone === "good" ? "good" : tone === "bad" ? "bad" : tone === "info" ? "info" : "warn";
}

function getSelected() {
  return candidates.find((item) => item.symbol === appState.selectedSymbol) || candidates[0];
}

function researchHorizon(item) {
  if (item.type === "mcx") return "MCX";
  const tfs = item.timeframe || [];
  const swing = tfs.some((tf) => tf === "1d" || tf === "1w");
  const intra = tfs.some((tf) => ["30m", "1h", "4h", "15m", "5m"].includes(tf));
  if (intra && !swing) return "INTRADAY";
  if (swing && !intra) return "SWING";
  if (intra) return "INTRADAY";
  return "SWING";
}

function researchDirection(item) {
  const blob = `${item.setup || ""} ${item.reason || ""} ${item.decisionTitle || ""}`.toUpperCase();
  if (/\bSHORT\b|\bBEAR|\bSELL\b/.test(blob)) return "SELL";
  if (/\bLONG\b|\bBULL|\bBUY\b/.test(blob)) return "BUY";
  return "NONE";
}

function filteredCandidates() {
  const search = appState.search.trim().toLowerCase();
  return candidates.filter((item) => {
    const modeOk = appState.mode === "all" || item.type === appState.mode;
    const filterOk = appState.filter === "all" || item.statusGroup === appState.filter;
    const timeframeOk = item.timeframe.some((tf) => appState.timeframes.has(tf));
    const horizon = researchHorizon(item);
    const boardOk = appState.boardMode === "ALL" || horizon === appState.boardMode;
    const directionOk = appState.boardDirection === "ALL" || researchDirection(item) === appState.boardDirection;
    const searchText = `${item.symbol} ${item.state} ${item.setup} ${item.reason}`.toLowerCase();
    const searchOk = !search || searchText.includes(search);
    return modeOk && filterOk && timeframeOk && boardOk && directionOk && searchOk;
  });
}

function renderRadar() {
  const rows = filteredCandidates();
  els.resultCount.textContent = rows.length;
  els.radarList.innerHTML = "";

  rows.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `radar-item ${item.symbol === appState.selectedSymbol ? "active" : ""}`;
    button.addEventListener("click", () => {
      appState.selectedSymbol = item.symbol;
      showView("stock");
      render();
      seedJournalForm();
    });

    const bars = item.series
      .slice(-9)
      .map((value) => `<span class="mini-bar" style="height:${Math.max(8, value / 1.25)}%"></span>`)
      .join("");

    button.innerHTML = `
      <div class="radar-top">
        <span class="radar-symbol">${escapeHtml(item.symbol)}</span>
        <span class="state-chip ${toneClass(item.stateTone)}">${escapeHtml(item.state)}</span>
      </div>
      <div class="radar-meta">
        <span>${escapeHtml(item.setup)}</span>
        <span>${escapeHtml(item.timeframe.join(" / "))}</span>
      </div>
      <div class="mini-bars" aria-hidden="true">${bars}</div>
    `;

    els.radarList.appendChild(button);
  });
}

function renderSelected() {
  const item = getSelected();
  els.selectedType.textContent =
    item.type === "mcx" ? "MCX Commodity Intelligence" : item.type === "harmonic" ? "Harmonic Intelligence" : "Stock Intelligence";
  els.selectedSymbol.textContent = item.symbol;
  els.selectedState.textContent = item.state;
  els.selectedState.className = `state-chip ${toneClass(item.stateTone)}`;
  if (els.lockBadge) els.lockBadge.classList.toggle("is-on", Boolean(appState.locked));
  els.selectedReason.textContent = appState.locked
    ? "Research is locked. Radar remains visible for monitoring only."
    : item.reason;
  els.selectedPrice.textContent = item.price;
  els.selectedMove.textContent = item.move;
  els.selectedMove.style.color = item.move.startsWith("-") ? "var(--red)" : "var(--green)";

  els.metricsGrid.innerHTML = item.metrics
    .map(
      ([label, value, note]) => `
        <div class="metric">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
          <small>${escapeHtml(note)}</small>
        </div>
      `
    )
    .join("");

  els.decisionTitle.textContent = appState.locked ? "LOCKED NO TRADE" : item.decisionTitle;
  els.decisionText.textContent = appState.locked
    ? "Research review is locked. Candidate evidence remains visible for monitoring."
    : item.decisionText;
  els.nextCheckValue.textContent = appState.locked ? "LOCKED" : item.nextConfirmation;
  els.invalidationValue.textContent = item.invalidationCondition;
  els.dataModeValue.textContent = item.dataMode;
}

function fillMaturityLadder(metaEl, countsEl, report) {
  if (!countsEl) return;
  if (!report || typeof report !== "object") {
    if (metaEl) {
      metaEl.textContent =
        "Compiler report unavailable. Ladder cannot be shown; activation remains false.";
    }
    countsEl.innerHTML = "";
    return;
  }
  const counts = report.maturityStageCounts || {};
  const activation = report.sourceActivationReady ? "true" : "false";
  const authorized = report.gateAuthorizedSourceKeyCount ?? 0;
  const passed = report.h1a0AcceptancePassed;
  const total = report.h1a0AcceptanceTotal;
  const h1a0 = Number.isFinite(passed) && Number.isFinite(total) ? `${passed}/${total}` : "unavailable";
  if (metaEl) {
    metaEl.textContent =
      `Read-only compiler counts. H1A0=${h1a0}; sourceActivationReady=${activation}; gateAuthorized=${authorized}. GREEN health is not GATE_AUTHORIZED.`;
  }
  const order = [
    "REGISTERED",
    "TRANSPORT_OK",
    "ARTIFACT_VALID",
    "VALID_EMPTY",
    "PARSER_SCHEMA_OK",
    "NORMALIZED",
    "FRESH_FOR_JOB",
    "DECISION_WIRED",
    "GATE_AUTHORIZED",
    "EXECUTION_AUTHORIZED",
  ];
  const keys = [...order, ...Object.keys(counts).filter((key) => !order.includes(key))];
  countsEl.innerHTML = keys
    .filter((key) => counts[key] != null)
    .map((key) => {
      const locked = key === "GATE_AUTHORIZED" || key === "EXECUTION_AUTHORIZED";
      return `<div class="maturity-step${locked ? " locked" : ""}"><span>${escapeHtml(key)}</span><strong>${escapeHtml(counts[key])}</strong></div>`;
    })
    .join("");
}

function renderMaturityLadder(report) {
  fillMaturityLadder(els.maturityLadderMeta, els.maturityLadderCounts, report);
  fillMaturityLadder(els.sourceHealthLadderMeta, els.sourceHealthLadderCounts, report);
}

function renderLiveDecision(batch) {
  if (!els.liveDecisionList) return;
  const paintS6Records = () => {
    if (window.TrendForgeS6Resolution && typeof window.TrendForgeS6Resolution.renderRecords === "function") {
      window.TrendForgeS6Resolution.renderRecords(els.liveDecisionList);
    }
  };
  if (!batch || typeof batch !== "object") {
    if (els.liveDecisionMeta) {
      els.liveDecisionMeta.textContent =
        "Live decision API unavailable. Fixture radar is not a live CONFIRMED path.";
    }
    els.liveDecisionList.innerHTML = "";
    paintS6Records();
    return;
  }
  const activation = batch.sourceActivationReady ? "true" : "false";
  const confirmed = batch.liveConfirmedCount ?? 0;
  const h1a0 = `${batch.h1a0Passed ?? "?"}/${batch.h1a0Total ?? "?"}`;
  if (els.liveDecisionMeta) {
    const storage = batch.storage || (batch.persisted ? "STORED" : "NONE");
    els.liveDecisionMeta.textContent =
      `R1 ${storage}. H1A0=${h1a0}; activation=${activation}; liveConfirmed=${confirmed}. Refresh persists a new run.`;
  }
  const rows = Array.isArray(batch.candidates) ? batch.candidates : [];
  if (!rows.length) {
    els.liveDecisionList.innerHTML =
      "<div class=\"empty-board\">Successful empty: no official attention names in the latest scanner run.</div>";
    paintS6Records();
    return;
  }
  els.liveDecisionList.innerHTML = rows
    .map((row) => {
      const symbol = row.instrument?.symbol || row.symbol || "UNKNOWN";
      const state = row.state || "WAIT";
      const reason = row.topReason || row.discoveryReason || "WAIT";
      const missing = Array.isArray(row.missingProof) ? row.missingProof.join(", ") : "UNKNOWN";
      return `<div class="live-decision-row"><span>${escapeHtml(symbol)}</span><strong class="state-chip warn">${escapeHtml(state)}</strong><small>${escapeHtml(reason)} | missing ${escapeHtml(missing)}</small></div>`;
    })
    .join("");
  paintS6Records();
}

async function refreshLiveDecision() {
  if (!els.liveDecisionRefresh) return;
  els.liveDecisionRefresh.disabled = true;
  try {
    const batch = await fetchJson("/api/v1/selection/live/refresh", { method: "POST" });
    renderLiveDecision(batch);
  } catch (error) {
    if (els.liveDecisionMeta) {
      els.liveDecisionMeta.textContent = "Persist failed. Activation stays false.";
    }
  } finally {
    els.liveDecisionRefresh.disabled = false;
  }
}

function renderProof() {
  const item = getSelected();
  els.proofList.innerHTML = item.proof
    .map(([label, value]) => `<div class="proof-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("");

  const quality = appState.locked ? 0 : item.quality;
  els.riskScore.textContent = quality;
  const angle = Math.round((quality / 100) * 360);
  const color = quality >= 75 ? "var(--teal)" : quality >= 55 ? "var(--gold)" : "var(--red)";
  els.riskRing.style.background = `radial-gradient(circle at center, #fff 0 48%, transparent 50%), conic-gradient(${color} 0deg, ${color} ${angle}deg, #d9e1e9 ${angle}deg 360deg)`;

  els.riskLines.innerHTML = item.risk
    .map(([label, value]) => `<div class="risk-line"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("");

  if (appState.sourceHealth.length > 0) {
    const severity = { RED: 0, AMBER: 1, WARN: 1, NA: 2, GREEN: 3 };
    const rows = [...appState.sourceHealth].sort(
      (left, right) => (severity[left.state] ?? 4) - (severity[right.state] ?? 4)
    );
    els.sourceGrid.innerHTML = rows
      .map((source) => {
        const stateClass = source.state === "GREEN" ? "good" : source.state === "AMBER" || source.state === "WARN" ? "warn" : source.state === "NA" ? "info" : "bad";
        const attempted = source.lastAttemptedAt ? new Date(source.lastAttemptedAt).toLocaleString() : "never";
        const threshold = source.staleThresholdHours == null ? "policy n/a" : `${source.staleThresholdHours}h stale limit`;
        const maturity = source.maturityState || "UNMAPPED";
        const gate = source.gatePermission ? "gate:yes" : "gate:no";
        const activation = source.sourceActivationReady ? "activation:ready" : "activation:false";
        const detail = `${source.trustLabel}; maturity ${maturity}; ${gate}; ${activation}; last attempt ${attempted}; ${threshold}; ${source.limitation}`;
        return `
          <div class="source-item source-health-item" title="${escapeHtml(detail)}">
            <span class="source-health-copy">
              <b>${escapeHtml(source.name)}</b>
              <small>Data ${escapeHtml(source.latestDataDate)} | maturity ${escapeHtml(maturity)} | failures ${escapeHtml(source.consecutiveFailures)}</small>
            </span>
            <strong class="${stateClass} state-chip">${escapeHtml(source.state)}</strong>
          </div>`;
      })
      .join("");
    return;
  }

  els.sourceGrid.innerHTML = item.sources
    .map(([source, state]) => {
      const stateClass = state === "GREEN" ? "good" : state === "AMBER" || state === "WARN" ? "warn" : state === "NA" ? "info" : "bad";
      return `<div class="source-item"><span>${escapeHtml(source)}</span><strong class="${stateClass} state-chip">${escapeHtml(state)}</strong></div>`;
    })
    .join("");
}

function renderResearchVault() {
  const rows = appState.researchRecords || [];
  els.researchCount.textContent = rows.length;
  if (rows.length === 0) {
    els.researchList.innerHTML = `
      <div class="research-record" aria-label="No saved research">
        <strong>No saved records yet</strong>
        <span>Save a snapshot to build a research memory.</span>
      </div>
    `;
    return;
  }

  els.researchList.innerHTML = "";
  rows.slice(0, 8).forEach((record) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "research-record";
    button.addEventListener("click", () => {
      const candidate = candidates.find((item) => item.symbol === record.symbol);
      if (candidate) {
        appState.selectedSymbol = candidate.symbol;
      }
      els.researchNote.value = record.note || "";
      els.researchTags.value = (record.tags || []).join(", ");
      render();
      setResearchStatus(`Loaded research snapshot for ${record.symbol}.`, "good");
    });

    const created = record.createdAt ? new Date(record.createdAt).toLocaleString() : "saved";
    const tagLine = record.tags && record.tags.length > 0 ? record.tags.join(", ") : "no tags";
    button.innerHTML = `
      <strong>${escapeHtml(record.title || record.symbol)}</strong>
      <span>${escapeHtml(created)}</span>
      <small>${escapeHtml(tagLine)}</small>
    `;
    els.researchList.appendChild(button);
  });
}

function setHarmonicStatus(message, tone = "") {
  els.harmonicScanStatus.textContent = message;
  els.harmonicScanStatus.classList.toggle("good-text", tone === "good");
  els.harmonicScanStatus.classList.toggle("bad-text", tone === "bad");
}

function renderHarmonicResults() {
  if (!appState.harmonicResults.length) {
    els.harmonicResultList.innerHTML = "";
    return;
  }
  els.harmonicResultList.innerHTML = "";
  appState.harmonicResults.slice(0, 3).forEach((item) => {
    const row = document.createElement("div");
    row.className = "harmonic-result";
    row.innerHTML = `
      <strong>${escapeHtml(item.symbol)} - ${escapeHtml(item.state)}</strong>
      <span>${escapeHtml(item.setup)} | ${escapeHtml(item.timeframe.join(", "))} | evidence strength ${escapeHtml(item.quality)}</span>
      <span>${escapeHtml(item.reason)}</span>
    `;
    els.harmonicResultList.appendChild(row);
  });
}

async function runHarmonicScan() {
  const symbol = els.harmonicSymbolInput.value.trim().toUpperCase();
  if (!symbol) {
    setHarmonicStatus("Enter a symbol before scanning.", "bad");
    return;
  }

  els.harmonicScanButton.disabled = true;
  setHarmonicStatus(`Scanning ${symbol}. Storing candles and checking confirmation gates...`);
  try {
    const scanPayload = await fetchJson("/api/harmonic/scan", {
      method: "POST",
      body: JSON.stringify({
        symbol,
        timeframe: els.harmonicTimeframeSelect.value,
        useStored: els.harmonicUseStored.checked,
        saveMlSnapshot: true
      })
    });

    if (!scanPayload.patterns.length) {
      setHarmonicStatus(scanPayload.warning || "No valid harmonic pattern found.", "bad");
      appState.harmonicResults = [];
      renderHarmonicResults();
      return;
    }

    const realCandidates = scanPayload.patterns.map((pattern) =>
      harmonicPatternToCandidate(pattern, scanPayload)
    );
    const incomingKeys = new Set(realCandidates.map((item) => `${item.symbol}:${item.setup}:${item.timeframe[0]}`));
    candidates = [
      ...realCandidates,
      ...candidates.filter((item) => !incomingKeys.has(`${item.symbol}:${item.setup}:${item.timeframe[0]}`))
    ];
    appState.harmonicResults = realCandidates;
    appState.selectedSymbol = realCandidates[0].symbol;
    appState.mode = "harmonic";
    setActiveButtons("[data-mode]", (btn) => btn.dataset.mode === appState.mode);
    render();
    loadMlSnapshotStatus();
    loadFunctionStatus();
    setHarmonicStatus(
      `${scanPayload.symbol} saved. Output: ${realCandidates[0].state}. ML run ${scanPayload.savedMlRunId || "not saved"}.`,
      "good"
    );
  } catch (error) {
    console.warn("Harmonic scan failed.", error);
    setHarmonicStatus(
      "Harmonic scan failed. Check source data, stored candles, or backend logs. No CONFIRMED state was produced.",
      "bad"
    );
  } finally {
    els.harmonicScanButton.disabled = false;
  }
}

async function runAdvancedHarmonicAnalysis() {
  const symbol = els.harmonicSymbolInput.value.trim().toUpperCase();
  if (!symbol) {
    setHarmonicStatus("Enter a symbol before advanced analysis.", "bad");
    return;
  }
  els.advancedHarmonicButton.disabled = true;
  els.advancedHarmonicBox.innerHTML = "Running G00-G14 gates, pivots, ratios, lifecycle, alerts, and benchmark...";
  try {
    const timeframe = els.harmonicTimeframeSelect.value;
    const [analysis, benchmark, alerts] = await Promise.all([
      fetchJson(`/api/harmonic/advanced/analyze?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&persistAlerts=true`, {
        method: "POST"
      }),
      fetchJson(`/api/harmonic/benchmark?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`, {
        method: "POST"
      }),
      fetchJson(`/api/harmonic/alerts?symbol=${encodeURIComponent(symbol)}&limit=3`)
    ]);
    const topPattern = analysis.validations?.[0]?.patternName || "No ratio match";
    els.advancedHarmonicBox.innerHTML = `
      <strong>${escapeHtml(symbol)} ${escapeHtml(timeframe)}: ${escapeHtml(analysis.finalState)}</strong>
      <span>Pattern: ${escapeHtml(topPattern)} | Lifecycle: ${escapeHtml(analysis.lifecycleState)}</span>
      <span>Quality: ${escapeHtml(analysis.hybridQualityScore)} | Gate Ratio: ${escapeHtml(analysis.gateRatio)} | Pivots: ${escapeHtml(analysis.pivots.length)}</span>
      <span>Benchmark: ${escapeHtml(benchmark.durationSeconds)}s | Alerts: ${escapeHtml(alerts.length)}</span>
    `;
    setHarmonicStatus("Advanced harmonic functions completed and saved where applicable.", "good");
  } catch (error) {
    console.warn("Advanced harmonic analysis failed.", error);
    els.advancedHarmonicBox.innerHTML = "Advanced analysis needs stored candles first. Run Harmonic Scan or fetch OHLCV.";
    setHarmonicStatus("Advanced analysis unavailable for this symbol/timeframe until candles exist.", "bad");
  } finally {
    els.advancedHarmonicButton.disabled = false;
  }
}

async function runHarmonicBacktest() {
  const symbol = els.harmonicSymbolInput.value.trim().toUpperCase();
  const timeframe = els.harmonicTimeframeSelect.value;
  if (!symbol) {
    setHarmonicStatus("Enter a symbol before backtesting.", "bad");
    return;
  }
  els.harmonicBacktestButton.disabled = true;
  els.advancedHarmonicBox.textContent = "Running expanding-prefix validation without future candles...";
  try {
    const report = await fetchJson(
      `/api/validation/harmonic-backtest?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&warmup=80&maxHoldingBars=40`,
      { method: "POST" }
    );
    els.advancedHarmonicBox.innerHTML = `
      <strong>${escapeHtml(symbol)} ${escapeHtml(timeframe)}: ${escapeHtml(report.status)}</strong>
      <span>Observations retained: ${escapeHtml(report.observationCount)} | Status: ${escapeHtml(report.status)}</span>
      <span>${escapeHtml(report.validationMethod)} | ${escapeHtml(report.sameBarRule)}</span>
      <span>Performance metrics hidden until non-fixture PIT approval.</span>
    `;
    setHarmonicStatus("Time-safe validation completed from stored candles.", "good");
  } catch (error) {
    els.advancedHarmonicBox.textContent = "Backtest needs enough stored candles for this symbol and timeframe.";
    setHarmonicStatus("Time-safe validation could not run.", "bad");
  } finally {
    els.harmonicBacktestButton.disabled = false;
  }
}

function drawChart() {
  const item = getSelected();
  const canvas = els.canvas;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const pad = 22;
  const values = item.series;
  const min = Math.min(...values) - 6;
  const max = Math.max(...values) + 6;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#f6f8fb";
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "#d8dee8";
  ctx.lineWidth = 1;
  for (let i = 0; i < 5; i += 1) {
    const y = pad + ((height - pad * 2) / 4) * i;
    ctx.beginPath();
    ctx.moveTo(pad, y);
    ctx.lineTo(width - pad, y);
    ctx.stroke();
  }

  const anchorY = pad + (height - pad * 2) * 0.48;
  ctx.fillStyle = "rgba(169, 109, 0, 0.13)";
  ctx.fillRect(pad, anchorY - 18, width - pad * 2, 36);
  ctx.strokeStyle = "rgba(169, 109, 0, 0.7)";
  ctx.setLineDash([8, 6]);
  ctx.beginPath();
  ctx.moveTo(pad, anchorY);
  ctx.lineTo(width - pad, anchorY);
  ctx.stroke();

  const invalidY = height - pad - 18;
  ctx.strokeStyle = "rgba(191, 48, 48, 0.62)";
  ctx.beginPath();
  ctx.moveTo(pad, invalidY);
  ctx.lineTo(width - pad, invalidY);
  ctx.stroke();
  ctx.setLineDash([]);

  function point(index, value) {
    const x = pad + ((width - pad * 2) / (values.length - 1)) * index;
    const y = height - pad - ((value - min) / (max - min)) * (height - pad * 2);
    return [x, y];
  }

  const gradient = ctx.createLinearGradient(0, pad, 0, height - pad);
  gradient.addColorStop(0, "rgba(15, 143, 138, 0.24)");
  gradient.addColorStop(1, "rgba(15, 143, 138, 0.02)");

  ctx.beginPath();
  values.forEach((value, index) => {
    const [x, y] = point(index, value);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  const [lastX] = point(values.length - 1, values[values.length - 1]);
  ctx.lineTo(lastX, height - pad);
  ctx.lineTo(pad, height - pad);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  ctx.beginPath();
  values.forEach((value, index) => {
    const [x, y] = point(index, value);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = "#0f8f8a";
  ctx.lineWidth = 3;
  ctx.stroke();

  const [x, y] = point(values.length - 1, values[values.length - 1]);
  ctx.fillStyle = "#0f8f8a";
  ctx.beginPath();
  ctx.arc(x, y, 5, 0, Math.PI * 2);
  ctx.fill();
}

function setActiveButtons(selector, matcher) {
  document.querySelectorAll(selector).forEach((button) => {
    button.classList.toggle("active", matcher(button));
  });
}

function institutionalFactorValues() {
  const values = {};
  document.querySelectorAll("[data-factor]").forEach((input) => {
    const raw = input.value.trim();
    values[input.dataset.factor] = raw === "" ? null : Number(raw);
  });
  return values;
}

function renderInstitutionalResult(result) {
  const score = Number(result.factorScore || 0);
  const marker = Math.max(0, Math.min(100, ((score + 3) / 6) * 100));
  const state = canonicalSelectionState(result.state);
  const tone = selectionTone(state);
  els.institutionalState.className = `state-chip ${tone}`;
  els.institutionalState.textContent = state;
  els.institutionalClassification.textContent = result.classification;
  els.institutionalScore.textContent = `Evidence strength ${score.toFixed(2)} - not win probability`;
  els.institutionalMarker.style.left = `${marker}%`;
  els.institutionalReason.textContent = (result.reasons || []).join(" ") || "No decision reason returned.";
}

async function loadInstitutionalStatus() {
  try {
    const [config, sources, models, reports] = await Promise.all([
      fetchJson("/api/institutional/config"),
      fetchJson("/api/institutional/sources"),
      fetchJson("/api/institutional/models"),
      fetchJson("/api/institutional/reports?limit=50")
    ]);
    appState.institutionalConfig = config;
    appState.institutionalSources = sources;
    appState.institutionalModels = models;
    appState.institutionalReports = reports;
    const modelRows = Object.values(models.models || {});
    const validatedModels = modelRows.filter((row) => row.can_unlock_ready).length;
    els.institutionalSourceCount.textContent = `${sources.endpointCount || 0} raw / ${sources.normalizationLinkedCount || 0} linked`;
    els.institutionalModelCount.textContent = `${validatedModels}/${modelRows.length} validated`;
    els.institutionalAccount.textContent = `INR ${Number(config.risk?.account_size || 0).toLocaleString("en-IN")}`;
    els.institutionalAuditCount.textContent = String(reports.length);
    if (reports[0]?.report) renderInstitutionalResult(reports[0].report);
  } catch (error) {
    els.institutionalState.className = "state-chip bad";
    els.institutionalState.textContent = "OFFLINE";
    els.institutionalReason.textContent = "Institutional engine API is unavailable.";
    console.warn("Institutional engine status unavailable.", error);
  }
}

async function runInstitutionalAnalysis() {
  els.institutionalEvaluateButton.disabled = true;
  els.institutionalReason.textContent = "Evaluating normalized factor inputs...";
  const selected = candidates.find((row) => row.symbol === appState.selectedSymbol);
  const modelRows = Object.values(appState.institutionalModels?.models || {});
  const modelsReady = modelRows.length > 0 && modelRows.every((row) => row.can_unlock_ready);
  const payload = {
    symbol: (selected?.symbol || "RELIANCE").replace("MCX ", "").replaceAll(" ", "_"),
    asOf: new Date().toISOString(),
    timeframe: selected?.timeframe?.[0] || "1D",
    market: selected?.type === "mcx" ? "MCX" : "NSE",
    factors: institutionalFactorValues(),
    hardFilters: {},
    sourceReady: false,
    modelsReady,
    modelProbabilities: {}
  };
  try {
    const result = await fetchJson("/api/institutional/analyze", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    renderInstitutionalResult(result);
    const reports = await fetchJson("/api/institutional/reports?limit=50");
    appState.institutionalReports = reports;
    els.institutionalAuditCount.textContent = String(reports.length);
  } catch (error) {
    els.institutionalState.className = "state-chip bad";
    els.institutionalState.textContent = "ERROR";
    els.institutionalReason.textContent = error.message;
  } finally {
    els.institutionalEvaluateButton.disabled = false;
  }
}

function activityMetric(value, options = {}) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return number.toLocaleString("en-IN", options);
}

function focusMarketActivitySymbol(symbol) {
  const radarCandidate = candidates.find((row) => row.symbol === symbol);
  els.harmonicSymbolInput.value = symbol;
  if (radarCandidate) {
    appState.selectedSymbol = symbol;
    appState.search = "";
    els.searchInput.value = "";
    render();
    els.marketActivityMeta.textContent = `${symbol} selected in the radar. Activity evidence still requires every normal gate.`;
    return;
  }
  els.marketActivityMeta.textContent = `${symbol} loaded into the harmonic symbol field. Run a real scan before making a decision.`;
}

function renderMarketActivity(snapshot) {
  appState.marketActivity = snapshot;
  const rows = snapshot?.candidates || [];
  const completeness = Math.round(Number(snapshot?.sourceCompleteness || 0) * 100);
  const timestamp = snapshot?.fetchedAt ? new Date(snapshot.fetchedAt).toLocaleString() : "not fetched";
  els.marketActivityStatus.textContent = snapshot?.state || "WAIT_SNAPSHOT";
  els.marketActivityMeta.textContent = `${completeness}% source completeness | ${timestamp} | Evidence strength is not win probability.`;
  els.marketActivityList.innerHTML = "";

  if (!rows.length) {
    els.marketActivityList.innerHTML = '<div class="market-activity-empty">No saved activity rows. Use refresh during or after an NSE session.</div>';
    return;
  }

  rows.slice(0, 8).forEach((candidate) => {
    const row = document.createElement("button");
    row.type = "button";
    row.className = `market-activity-row ${candidate.direction === "BULLISH" ? "bull" : candidate.direction === "BEARISH" ? "bear" : "mixed"}`;
    const volumeChange = candidate.week1VolumeChangePct == null
      ? "volume rank only"
      : `${activityMetric(candidate.week1VolumeChangePct, { maximumFractionDigits: 0 })}% vs 1W avg`;
    const priceChange = candidate.priceChangePct == null
      ? "price -"
      : `${candidate.priceChangePct >= 0 ? "+" : ""}${activityMetric(candidate.priceChangePct, { maximumFractionDigits: 2 })}%`;
    const activeRanks = [
      candidate.mostActiveVolumeRank ? `Vol #${candidate.mostActiveVolumeRank}` : null,
      candidate.mostActiveValueRank ? `Value #${candidate.mostActiveValueRank}` : null
    ].filter(Boolean).join(" | ") || "Activity rank -";
    const reason = candidate.reasons?.[0] || "Waiting for complete activity evidence.";
    row.innerHTML = `
      <span class="market-activity-primary">
        <strong>${escapeHtml(candidate.symbol)}</strong>
        <span class="state-chip ${toneClass(selectionTone(canonicalSelectionState(candidate.state)))}">${escapeHtml(canonicalSelectionState(candidate.state))}</span>
      </span>
      <span class="market-activity-score">Evidence ${activityMetric(candidate.activityScore, { maximumFractionDigits: 0 })}/100 <b>${escapeHtml(priceChange)}</b></span>
      <span class="market-activity-facts">${escapeHtml(volumeChange)} | ${escapeHtml(activeRanks)}</span>
      <small>${escapeHtml(reason)}</small>
    `;
    row.addEventListener("click", () => focusMarketActivitySymbol(candidate.symbol));
    els.marketActivityList.appendChild(row);
  });
}

async function loadMarketActivity() {
  try {
    renderMarketActivity(await fetchJson("/api/market-activity/latest?limit=8"));
  } catch (error) {
    els.marketActivityStatus.textContent = "OFFLINE";
    els.marketActivityMeta.textContent = error.message || "Market activity API is unavailable.";
    els.marketActivityList.innerHTML = '<div class="market-activity-empty">Stored activity evidence is unavailable.</div>';
  }
}

async function refreshMarketActivity() {
  els.marketActivityRefresh.disabled = true;
  els.marketActivityStatus.textContent = "FETCHING";
  els.marketActivityMeta.textContent = "Fetching and archiving four official NSE activity responses...";
  try {
    const snapshot = await fetchJson("/api/market-activity/fetch?limit=20", { method: "POST" });
    renderMarketActivity(snapshot);
  } catch (error) {
    els.marketActivityStatus.textContent = "WAIT_SOURCE";
    els.marketActivityMeta.textContent = error.message || "NSE activity refresh failed.";
  } finally {
    els.marketActivityRefresh.disabled = false;
  }
}

function commoditySourceState(snapshot, endpointKey) {
  return snapshot?.sources?.find((source) => source.endpointKey === endpointKey)?.parserState || "WAIT_SOURCE";
}

function commodityContextRow(title, state, facts, note) {
  const tone = state === "STRUCTURED_OK" || state === "CONTEXT_AVAILABLE" ? "bull" : state === "FETCH_FAILED" || state === "SCHEMA_MISMATCH" ? "bear" : "mixed";
  return `
    <div class="market-activity-row ${tone}">
      <span class="market-activity-primary"><strong>${escapeHtml(title)}</strong><span class="state-chip ${tone === "bull" ? "good" : tone === "bear" ? "bad" : "warn"}">${escapeHtml(state)}</span></span>
      <span class="market-activity-facts">${escapeHtml(facts)}</span>
      <small>${escapeHtml(note)}</small>
    </div>`;
}

function renderCommodityContext(snapshot) {
  appState.commodityContext = snapshot;
  els.commodityContextStatus.textContent = snapshot?.state || "WAIT_SNAPSHOT";
  const timestamp = snapshot?.normalizedAt ? new Date(snapshot.normalizedAt).toLocaleString() : "not normalized";
  els.commodityContextMeta.textContent = `${timestamp} | Research context only; cannot produce CONFIRMED.`;
  const rows = [];
  const option = snapshot?.mcxOptionMetrics?.[0];
  if (option) {
    const pcr = option.pcrOi == null ? "PCR unknown" : `PCR ${activityMetric(option.pcrOi, { maximumFractionDigits: 2 })}`;
    rows.push(commodityContextRow(
      `${option.symbol} options`,
      commoditySourceState(snapshot, "mcx_option_chain"),
      `${pcr} | Call wall ${activityMetric(option.callWallStrike)} | Put wall ${activityMetric(option.putWallStrike)} | Max pain ${activityMetric(option.maxPainStrike)}`,
      `${option.dataDate || "date unknown"} | ${option.signalState}; positioning context, not direction.`
    ));
  }
  const sge = snapshot?.sgeBenchmark;
  if (sge) {
    rows.push(commodityContextRow(
      "SGE gold benchmark",
      commoditySourceState(snapshot, "sge_benchmark_gold"),
      `ZP ${activityMetric(sge.latestZp, { maximumFractionDigits: 2 })} | WP ${activityMetric(sge.latestWp, { maximumFractionDigits: 2 })} | ${sge.trendState}`,
      `${sge.dataDate} | No SGE/LBMA premium without synchronized LBMA, FX, tax and unit inputs.`
    ));
  }
  const rigs = snapshot?.bakerHughes;
  if (rigs) {
    rows.push(commodityContextRow(
      "North America rigs",
      commoditySourceState(snapshot, "baker_hughes_na_rig_count"),
      `Total ${activityMetric(rigs.northAmericaTotal)} | Weekly ${rigs.northAmericaWeeklyChange >= 0 ? "+" : ""}${activityMetric(rigs.northAmericaWeeklyChange)} | ${rigs.supplySignal}`,
      `${rigs.dataDate} | Delayed crude supply context, not an intraday trigger.`
    ));
  }
  els.commodityContextList.innerHTML = rows.join("") || '<div class="market-activity-empty">No normalized MCX/global commodity context is stored.</div>';
}

async function loadCommodityContext() {
  try {
    renderCommodityContext(await fetchJson("/api/institutional/commodity-context/latest"));
  } catch (error) {
    els.commodityContextStatus.textContent = "WAIT_SOURCE";
    els.commodityContextMeta.textContent = error.message || "Commodity context API is unavailable.";
    els.commodityContextList.innerHTML = '<div class="market-activity-empty">No normalized commodity snapshot is available.</div>';
  }
}

function q5VisibleSections(payload) {
  const performanceAllowed = window.TrendForgeQ5.canShowPerformance(payload);
  return (payload?.inspector?.sections || []).filter((section) =>
    section.status !== "HIDDEN" && (section.sectionId !== "VALIDATION" || performanceAllowed)
  );
}

function q5InspectorSection(payload) {
  const sections = q5VisibleSections(payload);
  const selected = sections.find((section) => section.sectionId === appState.q5InspectorSection);
  return selected || sections[0] || null;
}

function renderQ5Inspector(payload) {
  const inspector = payload.inspector || {};
  const visibleSections = q5VisibleSections(payload);
  const selected = q5InspectorSection(payload);
  appState.q5InspectorSection = selected?.sectionId || "DECISION_PROOF";
  els.q5InspectorTabs.innerHTML = visibleSections
    .map((section) => `
      <button type="button" class="q5-inspector-tab ${section.sectionId === appState.q5InspectorSection ? "active" : ""}"
        data-q5-section="${escapeHtml(section.sectionId)}" role="tab"
        aria-selected="${section.sectionId === appState.q5InspectorSection}">
        ${escapeHtml(section.title)}
      </button>
    `)
    .join("");
  els.q5InspectorPanel.innerHTML = selected
    ? `
      <div class="q5-inspector-summary">
        <span class="state-chip ${selected.status === "AVAILABLE" ? "good" : "warn"}">${escapeHtml(selected.status)}</span>
        <p>${escapeHtml(selected.summary)}</p>
      </div>
      <ul>${(selected.items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>No additional normalized items.</li>"}</ul>
    `
    : "<p>No inspector section is available.</p>";
  els.q5InspectorTabs.querySelectorAll("[data-q5-section]").forEach((button) => {
    button.addEventListener("click", () => {
      appState.q5InspectorSection = button.dataset.q5Section;
      renderQ5Inspector(payload);
    });
  });
  const history = payload.histories?.[0]?.events || [];
  els.q5HistoryList.innerHTML = `
    <h3>Append-only state history</h3>
    ${history.map((event) => `
      <div class="q5-history-event">
        <strong>${escapeHtml(event.priorState)} -> ${escapeHtml(event.resultingState)}</strong>
        <span>${escapeHtml(event.reasonCode)} | ${escapeHtml(new Date(event.occurredAt).toLocaleString())}</span>
        <small>${escapeHtml(event.accepted ? "accepted" : "denied and recorded")}</small>
      </div>
    `).join("") || "<p>No state history is available.</p>"}
  `;
  const performanceAllowed = window.TrendForgeQ5.canShowPerformance(payload);
  els.q5ValidationLock.textContent = payload.fixtureOnly
    ? "Fixture PIT status is test evidence only. Validation and performance remain hidden."
    : performanceAllowed
      ? "PIT-approved validation is available in the authorized inspector."
      : "Validation details remain hidden until PIT approval and production authorization both pass.";
}

function renderQ5Selection(payload) {
  const validated = window.TrendForgeQ5.validatePayload(payload);
  appState.q5Selection = validated;
  const row = validated.radar[0];
  const state = canonicalSelectionState(row.state);
  els.q5SelectionState.textContent = state;
  els.q5SelectionState.className = `state-chip ${selectionTone(state)}`;
  els.q5SelectionLabel.textContent = row.evidenceStrengthLabel;
  els.q5InspectorStatus.textContent = validated.fixtureOnly ? "FIXTURE ONLY" : validated.inspector.validationStatus;
  const answers = window.TrendForgeQ5.answers(row);
  els.q5RadarAnswers.innerHTML = answers
    .map(([label, value]) => `<div class="q5-answer"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`)
    .join("");
  renderQ5Inspector(validated);
}

async function loadQ5Selection() {
  try {
    renderQ5Selection(await fetchJson("/api/v1/selection/fixtures/q5-r6"));
  } catch (error) {
    appState.q5Selection = null;
    els.q5SelectionState.textContent = "WAIT";
    els.q5SelectionState.className = "state-chip warn";
    els.q5SelectionLabel.textContent = "Q5 evidence inspector unavailable; no confirmation can be shown.";
    els.q5InspectorStatus.textContent = "OFFLINE";
    els.q5RadarAnswers.innerHTML = `<div class="q5-answer"><span>Reason</span><strong>${escapeHtml(error.message)}</strong></div>`;
    els.q5InspectorTabs.innerHTML = "";
    els.q5InspectorPanel.textContent = "No inspector payload is available.";
    els.q5HistoryList.textContent = "No state history is available.";
  }
}

function productFixtureOwnsChrome() {
  return Boolean(window.TrendForgeProductFixture);
}

function showView(view, tool) {
  if (productFixtureOwnsChrome() && window.TrendForgeProductFixture.go) {
    if (tool) {
      const button = document.querySelector(`.nav button[data-tool="${tool}"]`);
      if (button) {
        button.click();
        return;
      }
    }
    window.TrendForgeProductFixture.go(view);
    return;
  }
  appState.activeView = view;
  if (tool) appState.activeTool = tool;
  document.querySelectorAll(".final-shell .view").forEach((node) => {
    node.classList.toggle("active", node.id === view);
  });
  document.querySelectorAll(".final-shell .nav button[data-view]").forEach((button) => {
    const on = button.dataset.view === view && (!button.dataset.tool || button.dataset.tool === appState.activeTool);
    button.classList.toggle("active", on);
  });
  if (view === "tool") renderToolRoom(appState.activeTool);
  if (view === "stock") drawChart();
}

function renderToolRoom(toolId) {
  const spec = TOOL_REGISTRY[toolId];
  if (!spec) {
    if (els.toolTitle) els.toolTitle.textContent = toolId || "Unknown tool";
    if (els.toolState) {
      els.toolState.textContent = "WAIT_DTO_UNAVAILABLE";
      els.toolState.className = "chip wait";
    }
    if (els.toolPurpose) els.toolPurpose.textContent = "This nav key is not in the 14-tool registry.";
    if (els.toolContent) {
      els.toolContent.innerHTML = `<div class="tool-wait"><strong>WAIT_DTO_UNAVAILABLE</strong><p>No m_factor fallback. File A has not provided a DTO for ${escapeHtml(toolId || "unknown")}.</p></div>`;
    }
    return;
  }
  if (els.toolEyebrow) els.toolEyebrow.textContent = spec.eyebrow;
  if (els.toolTitle) els.toolTitle.textContent = spec.title;
  if (els.toolPurpose) els.toolPurpose.textContent = spec.purpose;
  if (els.toolState) {
    els.toolState.textContent = spec.ceiling;
    els.toolState.className = "chip wait";
  }
  if ((toolId === "index_dashboard" || toolId === "sector_scope") && window.TrendForgeS2WeatherPayload && typeof window.TrendForgeS2MarketWeatherRenderRoom === "function") {
    if (els.toolState) {
      els.toolState.textContent = "RESEARCH_CONTEXT_NOT_CONFIRMED";
      els.toolState.className = "chip wait";
    }
    if (els.toolContent) {
      els.toolContent.innerHTML = "";
      delete els.toolContent.dataset.s2Room;
    }
    window.TrendForgeS2MarketWeatherRenderRoom();
    return;
  }
  if (toolId === "accumulation_signals" && window.TrendForgeHybridOverlay && window.TrendForgeHybridOverlay.loaded) {
    const overlayRow = window.TrendForgeHybridOverlay.rowFor(String(appState.selectedSymbol || "").toUpperCase());
    if (overlayRow) {
      if (els.toolState) {
        els.toolState.textContent = overlayRow.asStatus === "USABLE" ? "RESEARCH_PROXY_NOT_CALIBRATED" : spec.ceiling;
      }
      if (els.toolContent) {
        els.toolContent.innerHTML = `<div class="tool-wait hybrid-as-row"><strong>${escapeHtml(overlayRow.symbol)} · asStatus ${escapeHtml(overlayRow.asStatus)}</strong><p>asDeliveryZ ${overlayRow.asStatus === "USABLE" && overlayRow.asDeliveryZ != null ? escapeHtml(overlayRow.asDeliveryZ) : "UNKNOWN"} · B3 z ${overlayRow.asStatus === "USABLE" && overlayRow.b3Z != null ? escapeHtml(overlayRow.b3Z) : "UNKNOWN"} · CA ${escapeHtml(overlayRow.r14CaState)}</p><p>B4 package ${escapeHtml(overlayRow.b4Package)} · S6 ${escapeHtml(overlayRow.s6VehicleStatus)} · Kelly illustration ${escapeHtml(overlayRow.kellyIllustration)} (not size)</p><p>Official delivery evidence only. Still not CONFIRMED; no invented GEX/IV.</p></div>`;
      }
      return;
    }
  }
  if (els.toolContent) {
    els.toolContent.innerHTML = `<div class="tool-wait"><strong>${escapeHtml(spec.ceiling)}</strong><p>${escapeHtml(spec.purpose)}</p><p>No fixture rows, cards or invented OI/IV/GEX are shown. This room waits for a File A DTO.</p></div>`;
  }
}

function renderAllStocksBoard() {
  if (!els.allStockContent) return;
  const rows = filteredCandidates();
  if (els.allStockCount) els.allStockCount.textContent = `${rows.length} live research rows`;
  if (els.allStockSummary) {
    const byState = { WATCH: 0, WAIT: 0, CONFIRMED: 0, REJECT: 0 };
    rows.forEach((item) => {
      byState[item.state] = (byState[item.state] || 0) + 1;
    });
    els.allStockSummary.innerHTML = `
      <div><span>Visible</span><strong>${rows.length}</strong></div>
      <div><span>WATCH</span><strong>${byState.WATCH}</strong></div>
      <div><span>WAIT</span><strong>${byState.WAIT}</strong></div>
      <div><span>CONFIRMED</span><strong>${byState.CONFIRMED}</strong></div>
      <div><span>REJECT</span><strong>${byState.REJECT}</strong></div>
    `;
  }
  if (!rows.length) {
    const emptyReason = appState.boardMode === "MCX"
      ? "MCX mode has no verified contract rows. Commodity context below stays Context Only."
      : "No live candidates match these filters. Successful-empty is not an API failure.";
    els.allStockContent.innerHTML = `<div class="empty-board">${emptyReason}</div>`;
    return;
  }
  els.allStockContent.innerHTML = `
    <div class="table-wrap">
      <table class="research-table">
        <thead>
          <tr>
            <th>Symbol</th><th>Horizon</th><th>State</th><th>Setup</th><th>Invalidation</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((item) => `
            <tr class="${item.symbol === appState.selectedSymbol ? "selected" : ""} ${researchDirection(item) === "BUY" ? "buy" : researchDirection(item) === "SELL" ? "sell" : ""}">
              <td><button type="button" class="stock" data-board-symbol="${escapeHtml(item.symbol)}">${escapeHtml(item.symbol)}</button></td>
              <td>${escapeHtml(researchHorizon(item))}</td>
              <td><span class="state-chip ${toneClass(item.stateTone)}">${escapeHtml(item.state)}</span></td>
              <td>${escapeHtml(item.setup || "")}</td>
              <td>${escapeHtml(item.invalidationCondition || item.trade?.stop || "UNKNOWN")}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
  els.allStockContent.querySelectorAll("[data-board-symbol]").forEach((button) => {
    button.addEventListener("click", () => {
      appState.selectedSymbol = button.dataset.boardSymbol;
      showView("stock");
      render();
      seedJournalForm();
    });
  });
}

function bindEvents() {
  if (!productFixtureOwnsChrome()) {
    document.querySelectorAll(".final-shell .nav button[data-view]").forEach((button) => {
      button.addEventListener("click", () => {
        showView(button.dataset.view, button.dataset.tool);
      });
    });
    if (els.headerHistory) {
      els.headerHistory.addEventListener("click", () => showView("tool", "m_factor_history"));
    }
  }
  if (els.previewRefresh) {
    els.previewRefresh.addEventListener("click", () => {
      loadApiData();
      loadMarketActivity();
      loadCommodityContext();
    });
  }
  if (!productFixtureOwnsChrome() && els.allStockMode) {
    els.allStockMode.addEventListener("change", () => {
      appState.boardMode = els.allStockMode.value;
      if (appState.boardMode === "MCX") {
        appState.mode = "mcx";
        setActiveButtons("[data-mode]", (btn) => btn.dataset.mode === "mcx");
      }
      ensureSelectionVisible();
      render();
    });
  }
  if (!productFixtureOwnsChrome() && els.allStockDirection) {
    els.allStockDirection.addEventListener("change", () => {
      appState.boardDirection = els.allStockDirection.value;
      ensureSelectionVisible();
      render();
    });
  }

  els.searchInput.addEventListener("input", (event) => {
    appState.search = event.target.value;
    render();
  });

  document.querySelectorAll("[data-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      appState.mode = button.dataset.mode;
      setActiveButtons("[data-mode]", (btn) => btn.dataset.mode === appState.mode);
      ensureSelectionVisible();
      render();
    });
  });

  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      appState.filter = button.dataset.filter;
      setActiveButtons("[data-filter]", (btn) => btn.dataset.filter === appState.filter);
      ensureSelectionVisible();
      render();
    });
  });

  document.querySelectorAll("[data-timeframe]").forEach((button) => {
    button.addEventListener("click", () => {
      const tf = button.dataset.timeframe;
      if (appState.timeframes.has(tf) && appState.timeframes.size > 1) {
        appState.timeframes.delete(tf);
      } else {
        appState.timeframes.add(tf);
      }
      setActiveButtons("[data-timeframe]", (btn) => appState.timeframes.has(btn.dataset.timeframe));
      ensureSelectionVisible();
      render();
    });
  });

  els.panicButton.addEventListener("click", async () => {
    if (appState.locked) {
      els.recoveryDialog.showModal();
      prepareRecoveryDialog();
      return;
    }
    try {
      await activatePanicLock();
    } catch (error) {
      els.safetyStatus.textContent = "SAFETY_API_ERROR";
    }
  });

  els.recoveryClose.addEventListener("click", () => {
    stopRecoveryTimer();
    els.recoveryDialog.close();
  });
  els.recoveryForm.addEventListener("input", updateRecoveryReadiness);
  els.recoveryForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitRecoveryReview();
  });

  els.refreshButton.addEventListener("click", async () => {
    els.refreshButton.animate(
      [{ transform: "rotate(0deg)" }, { transform: "rotate(360deg)" }],
      { duration: 420, easing: "ease-out" }
    );
    try {
      appState.sourceHealth = await fetchJson("/api/source-health");
    } catch (error) {
      console.warn("Source health refresh failed.", error);
    }
    renderProof();
  });

  els.saveResearchButton.addEventListener("click", () => {
    saveResearchSnapshot();
  });

  els.harmonicScanButton.addEventListener("click", () => {
    runHarmonicScan();
  });

  els.advancedHarmonicButton.addEventListener("click", () => {
    runAdvancedHarmonicAnalysis();
  });

  els.harmonicBacktestButton.addEventListener("click", () => {
    runHarmonicBacktest();
  });

  els.parserSourceSelect.addEventListener("change", (event) => {
    appState.parserSource = event.target.value;
    loadFunctionStatus();
  });

  els.parserRefreshButton.addEventListener("click", () => {
    refreshSelectedParser();
  });

  els.scannerRunButton.addEventListener("click", () => {
    // R15: refresh the Scanner Lab via GET. No collector fire, no orders.
    if (window.TrendForgeScannerLab && typeof window.TrendForgeScannerLab.refresh === "function") {
      window.TrendForgeScannerLab.refresh();
    }
  });

  els.refreshAlertsButton.addEventListener("click", () => {
    loadOperationalRecords();
  });

  els.journalCreateForm.addEventListener("submit", (event) => {
    event.preventDefault();
    createJournalRecord();
  });

  els.journalOutcomeForm.addEventListener("submit", (event) => {
    event.preventDefault();
    updateJournalRecordOutcome();
  });

  els.institutionalForm.addEventListener("submit", (event) => {
    event.preventDefault();
    runInstitutionalAnalysis();
  });

  els.marketActivityRefresh.addEventListener("click", () => {
    refreshMarketActivity();
  });
  if (els.liveDecisionRefresh) {
    els.liveDecisionRefresh.addEventListener("click", () => {
      refreshLiveDecision();
    });
  }
}

function ensureSelectionVisible() {
  const rows = filteredCandidates();
  if (!rows.some((item) => item.symbol === appState.selectedSymbol) && rows.length > 0) {
    appState.selectedSymbol = rows[0].symbol;
  }
}

function render() {
  renderRadar();
  if (!productFixtureOwnsChrome()) renderAllStocksBoard();
  renderSelected();
  renderProof();
  renderResearchVault();
  renderHarmonicResults();
  renderGeneralAlerts();
  renderJournalRecords();
  if (!productFixtureOwnsChrome() && appState.activeView === "stock") drawChart();
  if (!productFixtureOwnsChrome() && appState.activeView === "tool") renderToolRoom(appState.activeTool);
  if (window.lucide) window.lucide.createIcons();
}

bindEvents();
render();
seedJournalForm();
loadApiData();
loadResearchRecords();
loadFunctionStatus();
loadOperationalRecords();
loadInstitutionalStatus();
loadMarketActivity();
loadCommodityContext();
loadQ5Selection();
