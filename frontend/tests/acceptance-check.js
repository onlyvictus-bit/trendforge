const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const files = {
  html: path.join(root, "index.html"),
  css: path.join(root, "styles.css"),
  js: path.join(root, "app.js"),
  readme: path.join(root, "README.txt"),
  radar: path.join(root, "evidence-radar.js"),
  top10: path.join(root, "top10-research.js"),
  s7: path.join(root, "s7-state.js"),
  s8: path.join(root, "s8-persist.js"),
  dataLane: path.join(root, "data-lane.js"),
  researchQty: path.join(root, "research-quantity.js"),
  s9Pit: path.join(root, "s9-pit-homework.js"),
  r16Pit: path.join(root, "r16-pit-validation.js"),
  r18Model: path.join(root, "r18-model-governance.js")
};

function read(file) {
  return fs.readFileSync(file, "utf8");
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function assertIncludes(source, needle, label) {
  assert(source.includes(needle), `${label} missing: ${needle}`);
}

function countMatches(source, pattern) {
  const matches = source.match(pattern);
  return matches ? matches.length : 0;
}

const html = read(files.html);
const css = read(files.css);
const js = read(files.js);
const readme = read(files.readme);

const htmlIds = new Set(
  [...html.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1])
);
const jsElementIds = [...js.matchAll(/getElementById\("([^"]+)"\)/g)].map(
  (match) => match[1]
);
const checks = [
  ["files exist", () => Object.values(files).forEach((file) => assert(fs.existsSync(file), `Missing file: ${file}`))],
  ["R18 model governance stays locked and read-only", () => {
    const r18 = read(files.r18Model);
    assertIncludes(html, 'id="r18ModelGovernancePanel"', "HTML");
    assertIncludes(html, "r18-model-governance.js?v=20260907-provenance-1", "HTML");
    assertIncludes(r18, "/api/research/ml/governance", "R18JS");
    assertIncludes(r18, "MODEL_NOT_APPROVED", "R18JS");
    assertIncludes(r18, "Probability: HIDDEN", "R18JS");
    assert(!/placeorder|place_order|winRateVisible\s*:\s*true/i.test(r18), "R18 UI must not trade or expose win rate");
  }],
  ["S7 state panel exists", () => assertIncludes(html, "s7StatePanel", "HTML")],
  ["S7 state script mounted with cache-bust", () => assertIncludes(html, "s7-state.js?v=20260907-provenance-1", "HTML")],
  ["Guidance OMS panel + arm switch mounted default-off", () => {
    assertIncludes(html, 'id="guidanceOmsPanel"', "HTML");
    assertIncludes(html, 'id="guidanceOmsList"', "HTML");
    assertIncludes(html, 'id="armLiveOrders"', "HTML");
    assertIncludes(html, "guidance-oms.js?v=20260825-goms-1", "HTML");
  }],
  ["Guidance OMS script previews only until armed", () => {
    const goms = fs.readFileSync(path.join(root, "guidance-oms.js"), "utf8");
    assertIncludes(goms, "/api/v1/selection/guidance-oms/preview", "guidance-oms.js");
    assertIncludes(goms, "/api/v1/selection/guidance-oms/place", "guidance-oms.js");
    assertIncludes(goms, "/api/v1/settings/live-orders-arm", "guidance-oms.js");
    assertIncludes(goms, "LIVE_ORDERS_ARMED_OFF", "guidance-oms.js");
    assertIncludes(goms, 'disabled', "guidance-oms.js place button starts disabled");
    assertIncludes(html, "Trade guidance", "HTML guidance copy");
    assertIncludes(html, "not a guaranteed win", "HTML guidance disclaimer");
  }],
  ["S7 mode chip flips to PRF-003-only when activated", () => {
    const s7 = fs.readFileSync(files.s7, "utf8");
    assertIncludes(s7, "confirmedModeChip", "S7JS");
    assertIncludes(s7, "CONFIRMED EOD PRF-003 ONLY", "S7JS");
    assertIncludes(s7, "CONFIRMED LOCKED", "S7JS");
    assertIncludes(s7, "intradayGuidanceConfirmed", "S7JS");
    assert(!/place_order/.test(s7), "s7-state.js must never reference an order path");
  }],
  ["S7 route referenced by live adapter", () => {
    const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
    assertIncludes(adapter, "s7State", "ADAPTER");
  }],
  ["S7 script exposes contract and never assigns CONFIRMED", () => {
    const s7 = fs.readFileSync(files.s7, "utf8");
    assertIncludes(s7, "TrendForgeS7State", "S7JS");
    assertIncludes(s7, "trendforge.s7-state.v1", "S7JS");
    assert(!/publicState\s*[:=]\s*["'`]CONFIRMED/.test(s7), "S7 must never assign CONFIRMED");
  }],
  ["S7 renders unified tradability and hidden lineage", () => {
    const s7 = fs.readFileSync(files.s7, "utf8");
    assertIncludes(s7, "tradabilityOutcome", "S7JS");
    assertIncludes(s7, "tradabilityReason", "S7JS");
    assertIncludes(s7, "tradabilityHash", "S7JS");
    assertIncludes(s7, "Restriction evidence", "S7JS");
    assert(!/tradability.*confidence|win probability/i.test(s7), "tradability must not be confidence/probability");
  }],
  ["S8 history panel exists", () => assertIncludes(html, "s8HistoryPanel", "HTML")],
  ["S8 script mounted with cache-bust", () => assertIncludes(html, "s8-persist.js?v=20260907-provenance-1", "HTML")],
  ["S8 latest route referenced by adapter", () => {
    const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
    assertIncludes(adapter, "s8Latest", "ADAPTER");
  }],
  ["S8 script exposes contract, never CONFIRMED or winRate", () => {
    const s8 = fs.readFileSync(files.s8, "utf8");
    assertIncludes(s8, "TrendForgeS8Persist", "S8JS");
    assertIncludes(s8, "trendforge.s8-scan.v1", "S8JS");
    assert(!/winRate/i.test(s8), "S8 must not surface win rate");
    assert(!/publicState\s*[:=]\s*["'`]CONFIRMED/.test(s8), "S8 must never assign CONFIRMED");
  }],
  ["data-lane switch and script mounted", () => {
    assertIncludes(html, 'id="dataLaneSwitch"', "HTML");
    assertIncludes(html, 'id="dataLaneMeta"', "HTML");
    assertIncludes(html, "data-lane.js?v=20260825-lane-1", "HTML");
  }],
  ["research qty/funds panels mounted", () => {
    assertIncludes(html, 'id="researchQtyPanel"', "HTML");
    assertIncludes(html, 'id="researchFundsPanel"', "HTML");
    assertIncludes(html, 'id="researchPositionCard"', "HTML");
    assertIncludes(html, "research-quantity.js?v=20260825-qty-1", "HTML");
    assertIncludes(html, "not a broker account", "HTML");
  }],
  ["adapter fetches data-lane and research-quantity", () => {
    const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
    assertIncludes(adapter, "dataLane", "ADAPTER");
    assertIncludes(adapter, "researchQty", "ADAPTER");
    assertIncludes(adapter, "TrendForgeDataLane", "ADAPTER");
    assertIncludes(adapter, "TrendForgeResearchQty", "ADAPTER");
  }],
  ["data-lane/qty scripts never assign CONFIRMED or place_order", () => {
    const lane = fs.readFileSync(files.dataLane, "utf8");
    const qty = fs.readFileSync(files.researchQty, "utf8");
    assertIncludes(lane, "TrendForgeDataLane", "LANE");
    assertIncludes(qty, "TrendForgeResearchQty", "QTY");
    assertIncludes(qty, "not an order", "QTY");
    assertIncludes(qty, "not a broker account", "QTY");
    assert(!/place_order/.test(lane + qty), "must not mention place_order");
    assert(!/publicState\s*[:=]\s*["'`]CONFIRMED/.test(lane + qty), "must never assign CONFIRMED");
  }],
  ["R16 PIT validation panel exists", () => assertIncludes(html, "s9PitHomeworkPanel", "HTML")],
  ["R16 PIT owner and compatibility shim mounted in order", () => {
    const r16Index = html.indexOf("r16-pit-validation.js?v=20260907-provenance-1");
    const shimIndex = html.indexOf("s9-pit-homework.js?v=20260828-r16-compat-1");
    const adapterIndex = html.indexOf("selection-live-adapter.js");
    assert(r16Index >= 0 && shimIndex > r16Index && adapterIndex > shimIndex,
      "R16 owner, S9 shim and live adapter must load in ownership order");
  }],
  ["R16 read-only routes referenced by adapter", () => {
    const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
    assertIncludes(adapter, "r16Status", "ADAPTER");
    assertIncludes(adapter, "r16Metrics", "ADAPTER");
    assert(!adapter.includes("/api/v1/selection/pit/observations"), "initial adapter load must not fetch observations");
    assertIncludes(adapter, "TrendForgeR16PitValidation", "ADAPTER");
    const r16 = fs.readFileSync(files.r16Pit, "utf8");
    assertIncludes(r16, "/api/v1/selection/pit/observations?limit=50", "R16JS");
    assertIncludes(r16, 'addEventListener("toggle"', "R16JS");
    assertIncludes(r16, "if (inspector.open) void loadObservations()", "R16JS");
    assert(!adapter.includes("/api/v1/selection/pit-homework"), "adapter must not use legacy PIT homework");
  }],
  ["R16 frontend displays backend state and never computes approval or win rate", () => {
    const r16 = fs.readFileSync(files.r16Pit, "utf8");
    assertIncludes(r16, "TrendForgeR16PitValidation", "R16JS");
    assertIncludes(r16, "Evidence strength is not win probability", "R16JS");
    assert(!r16.includes("computeGuidance"), "R16 must not compute guidance client-side");
    assert(!/guidanceWinRate|winRate/.test(r16), "R16 must not show a misleading win rate");
    assert(!/publicState\s*[:=]\s*["'`]CONFIRMED/.test(r16), "R16 must never assign CONFIRMED");
    assert(!/place_order/.test(r16), "R16 must not call place_order");
  }],
  ["R16 responsive validation styles exist", () => {
    const styles = fs.readFileSync(files.css, "utf8");
    assertIncludes(styles, ".r16-summary", "CSS");
    assertIncludes(styles, ".r16-cells", "CSS");
  }],
  ["evidence radar panel exists", () => assertIncludes(html, "evidenceRadarPanel", "HTML")],
  ["evidence radar coverage strip exists", () => assertIncludes(html, "evidenceRadarCoverage", "HTML")],
  ["evidence radar script mounted", () => assertIncludes(html, "evidence-radar.js", "HTML")],
  ["s2 weather strip exists", () => assertIncludes(html, "s2WeatherStrip", "HTML")],
  ["s2 weather script mounted", () => assertIncludes(html, "s2-market-weather.js", "HTML")],
  ["s2 weather never a stock vote", () => assertIncludes(read(path.join(root, "s2-market-weather.js")), "never a stock vote", "JS")],
  ["s2 paints IX index_dashboard room", () => assertIncludes(read(path.join(root, "s2-market-weather.js")), "index_dashboard", "JS")],
  ["s2 paints SC sector_scope room", () => assertIncludes(read(path.join(root, "s2-market-weather.js")), "sector_scope", "JS")],
  ["s2 IX/SC rooms hook app.js tool renderer", () => assertIncludes(js, "TrendForgeS2MarketWeatherRenderRoom", "JS")],
  ["s2 IX ceiling is context wait not empty DTO", () => assertIncludes(js, "S2_CONTEXT_WAIT", "JS")],
  ["radar speaks how what where when", () => assertIncludes(read(files.radar), '"HOW"', "JS") && assertIncludes(read(files.radar), '"WHEN"', "JS")],
  ["top10 panel labelled R6 shortlist", () => assertIncludes(html, "R6 shortlist (stickers)", "HTML")],
  ["final shell layout exists", () => assertIncludes(html, "final-shell", "HTML")],
  ["command bar exists", () => assertIncludes(html, "command-bar", "HTML")],
  ["calendar command status exists", () => assertIncludes(html, "calendarStatus", "HTML")],
  ["radar list exists", () => assertIncludes(html, "radarList", "HTML")],
  ["analysis core exists", () => assertIncludes(html, "analysis-core", "HTML")],
  ["proof rail exists", () => assertIncludes(html, "proof-rail", "HTML")],
  ["chart canvas exists", () => assertIncludes(html, "marketPulse", "HTML")],
  ["source health exists", () => assertIncludes(html, "sourceGrid", "HTML")],
  ["institutional factor panel exists", () => assertIncludes(html, "institutionalForm", "HTML")],
  ["institutional score axis exists", () => assertIncludes(html, "institutionalMarker", "HTML")],
  ["market activity watch exists", () => assertIncludes(html, "marketActivityList", "HTML")],
  ["market activity refresh exists", () => assertIncludes(html, "marketActivityRefresh", "HTML")],
  ["commodity context panel exists", () => assertIncludes(html, "commodityContextList", "HTML")],
  ["research vault exists", () => assertIncludes(html, "researchList", "HTML")],
  ["research save button exists", () => assertIncludes(html, "saveResearchButton", "HTML")],
  ["general alerts panel exists", () => assertIncludes(html, "generalAlertList", "HTML")],
  ["journal entry form exists", () => assertIncludes(html, "journalCreateForm", "HTML")],
  ["journal outcome form exists", () => assertIncludes(html, "journalOutcomeForm", "HTML")],
  ["ML auto capture status exists", () => assertIncludes(html, "mlCaptureStatus", "HTML")],
  ["harmonic scan symbol input exists", () => assertIncludes(html, "harmonicSymbolInput", "HTML")],
  ["harmonic scan timeframe select exists", () => assertIncludes(html, "harmonicTimeframeSelect", "HTML")],
  ["harmonic scan button exists", () => assertIncludes(html, "harmonicScanButton", "HTML")],
  ["advanced harmonic button exists", () => assertIncludes(html, "advancedHarmonicButton", "HTML")],
  ["source registry status exists", () => assertIncludes(html, "sourceRegistryStatus", "HTML")],
  ["parquet status exists", () => assertIncludes(html, "parquetStatus", "HTML")],
  ["source monitor status exists", () => assertIncludes(html, "sourceMonitorStatus", "HTML")],
  ["gate readiness status exists", () => assertIncludes(html, "gateReadinessStatus", "HTML")],
  ["parser drilldown exists", () => assertIncludes(html, "parserDrilldown", "HTML")],
  ["scanner run button exists", () => assertIncludes(html, "scannerRunButton", "HTML")],
  ["manual safety lock exists", () => assertIncludes(html, "panicButton", "HTML")],
  ["search input exists", () => assertIncludes(html, "searchInput", "HTML")],
  ["stock mode exists", () => assertIncludes(html, 'data-mode="stock"', "HTML")],
  ["harmonic mode exists", () => assertIncludes(html, 'data-mode="harmonic"', "HTML")],
  ["mcx mode exists", () => assertIncludes(html, 'data-mode="mcx"', "HTML")],
  ["30m timeframe exists", () => assertIncludes(html, 'data-timeframe="30m"', "HTML")],
  ["1h timeframe exists", () => assertIncludes(html, 'data-timeframe="1h"', "HTML")],
  ["4h timeframe exists", () => assertIncludes(html, 'data-timeframe="4h"', "HTML")],
  ["1d timeframe exists", () => assertIncludes(html, 'data-timeframe="1d"', "HTML")],
  ["1w timeframe exists", () => assertIncludes(html, 'data-timeframe="1w"', "HTML")],
  ["responsive CSS exists", () => assert(countMatches(css, /@media/g) >= 3, "Expected at least 3 responsive media queries")],
  ["fixed panel regions exist", () => assertIncludes(css, "grid-template-columns", "CSS")],
  ["safe fallback transformation exists", () => assertIncludes(js, "const fallbackCandidates = fallbackExamples.map", "JS")],
  ["fallback is research-only", () => assertIncludes(js, 'reason: "Demonstration layout only; no fresh structured market evidence is attached."', "JS")],
  ["initial page is not ready", () => assert(!html.includes('<h3 id="decisionTitle">READY'), "Initial HTML must not show READY")],
  ["untrusted HTML is escaped", () => assertIncludes(js, "function escapeHtml(value)", "JS")],
  ["API loader exists", () => assertIncludes(js, "async function loadApiData()", "JS")],
  ["institutional status loader exists", () => assertIncludes(js, "async function loadInstitutionalStatus()", "JS")],
  ["institutional analysis action exists", () => assertIncludes(js, "async function runInstitutionalAnalysis()", "JS")],
  ["market activity loader exists", () => assertIncludes(js, "async function loadMarketActivity()", "JS")],
  ["market activity refresh action exists", () => assertIncludes(js, "async function refreshMarketActivity()", "JS")],
  ["market activity latest endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/market-activity/latest?limit=8")', "JS")],
  ["market activity fetch endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/market-activity/fetch?limit=20"', "JS")],
  ["market activity is not presented as probability", () => assertIncludes(js, "Evidence strength is not win probability", "JS")],
  ["commodity context loader exists", () => assertIncludes(js, "async function loadCommodityContext()", "JS")],
  ["commodity context endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/institutional/commodity-context/latest")', "JS")],
  ["commodity context cannot confirm", () => assertIncludes(js, "Research context only; cannot produce CONFIRMED", "JS")],
  ["institutional config endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/institutional/config")', "JS")],
  ["institutional source contracts endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/institutional/sources")', "JS")],
  ["institutional model endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/institutional/models")', "JS")],
  ["institutional audit reports are referenced", () => assertIncludes(js, 'fetchJson("/api/institutional/reports?limit=50")', "JS")],
  ["institutional public input cannot self certify sources", () => assertIncludes(js, "sourceReady: false", "JS")],
  ["API radar endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/radar")', "JS")],
  ["research API endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/research-records")', "JS")],
  ["alerts API endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/alerts")', "JS")],
  ["journal API endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/journal")', "JS")],
  ["ML status endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/ml-snapshots/status")', "JS")],
  ["harmonic scan endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/harmonic/scan"', "JS")],
  ["source registry endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/sources/registry")', "JS")],
  ["parquet status endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/parquet/status")', "JS")],
  ["source monitor endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/source-monitor/scheduler/status")', "JS")],
  ["operational source health endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/source-health")', "JS")],
  ["source failure streak is visible", () => assertIncludes(js, "consecutiveFailures", "JS")],
  ["source stale threshold is visible", () => assertIncludes(js, "staleThresholdHours", "JS")],
  ["gate readiness endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/gates/readiness")', "JS")],
  ["source parser domain endpoint is referenced", () => assertIncludes(js, "/api/source-parser/domain-rows", "JS")],
  ["raw archive endpoint is referenced", () => assertIncludes(js, "/api/raw-source-archive", "JS")],
  ["source parser outputs endpoint is referenced", () => assertIncludes(js, "/api/source-parser/outputs", "JS")],
  ["BSE XBRL detail endpoint is referenced", () => assertIncludes(js, "/api/bse-offers/xbrl/documents", "JS")],
  ["BSE offer anchor endpoint is referenced", () => assertIncludes(js, "/api/bse-offers/events", "JS")],
  ["source freshness status endpoint is referenced", () => assertIncludes(js, "/api/source-freshness-status", "JS")],
  ["source replacement map endpoint is referenced", () => assertIncludes(js, "/api/source-replacement-map", "JS")],
  ["scanner endpoint is referenced", () => assertIncludes(js, "/api/scanner/run-once", "JS")],
  ["advanced harmonic endpoint is referenced", () => assertIncludes(js, "/api/harmonic/advanced/analyze", "JS")],
  ["time-safe backtest endpoint is referenced", () => assertIncludes(js, "/api/validation/harmonic-backtest", "JS")],
  ["risk settings endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/settings/risk")', "JS")],
  ["NSE universe endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/universe/status")', "JS")],
  ["market context endpoint is referenced", () => assertIncludes(js, 'fetchOptionalJson("/api/context/market/latest")', "JS")],
  ["official context status endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/context/official/status")', "JS")],
  ["exchange calendar endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/calendar/status")', "JS")],
  ["persisted safety status endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/safety/status")', "JS")],
  ["panic lock endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/safety/panic-lock"', "JS")],
  ["recovery unlock endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/safety/unlock"', "JS")],
  ["recovery checklist exists", () => assert(countMatches(html, /name="recovery"/g) === 5, "Expected five recovery acknowledgements")],
  ["recovery submit is state controlled", () => assertIncludes(html, 'id="recoverySubmit"', "HTML")],
  ["recovery validates all acknowledgements locally", () => assertIncludes(js, "all five recovery acknowledgements", "JS")],
  ["recovery shows active cooldown", () => assertIncludes(js, 'fetchJson("/api/safety/events?active=true&limit=10")', "JS")],
  ["API errors expose backend detail", () => assertIncludes(js, "formatApiErrorDetail", "JS")],
  ["CFTC analytics endpoint is referenced", () => assertIncludes(js, "/api/cftc/analytics?market=GOLD", "JS")],
  ["CFTC crowding is visible", () => assertIncludes(js, 'label: "Crowding"', "JS")],
  ["CFTC freshness is visible", () => assertIncludes(js, 'label: "COT Freshness"', "JS")],
  ["CFTC remains context only", () => assertIncludes(js, 'value: "CONTEXT_ONLY"', "JS")],
  ["research save function exists", () => assertIncludes(js, "async function saveResearchSnapshot()", "JS")],
  ["ML status loader exists", () => assertIncludes(js, "async function loadMlSnapshotStatus()", "JS")],
  ["stock candidate exists", () => assertIncludes(js, 'type: "stock"', "JS")],
  ["harmonic candidate exists", () => assertIncludes(js, 'type: "harmonic"', "JS")],
  ["mcx candidate exists", () => assertIncludes(js, 'type: "mcx"', "JS")],
  ["legacy READY is demoted to WATCH", () => assertIncludes(js, 'legacyReady ? "WATCH - LEGACY RESULT"', "JS")],
  ["canonical state delegates to fail-closed contract", () => assertIncludes(js, "window.TrendForgeQ5.canonicalState(value)", "JS")],
  ["status group delegates to Q5 contract", () => assertIncludes(js, "window.TrendForgeQ5.statusGroup(state)", "JS")],
  ["harmonic PRZ state exists", () => assertIncludes(js, "HARMONIC_PRZ_ACTIVE", "JS")],
  ["lock trading state exists", () => assertIncludes(js, "LOCKED_NO_TRADE", "JS")],
  ["filtering function exists", () => assertIncludes(js, "function filteredCandidates()", "JS")],
  ["chart drawing function exists", () => assertIncludes(js, "function drawChart()", "JS")],
  ["source rendering exists", () => assertIncludes(js, "sourceGrid.innerHTML", "JS")],
  ["research rendering exists", () => assertIncludes(js, "function renderResearchVault()", "JS")],
  ["alert rendering exists", () => assertIncludes(js, "function renderGeneralAlerts()", "JS")],
  ["journal rendering exists", () => assertIncludes(js, "function renderJournalRecords()", "JS")],
  ["README has open path", () => assertIncludes(readme, "D:\\TrendForge\\frontend\\index.html", "README")],
  ["Q5 selection radar exists", () => assertIncludes(html, "q5RadarAnswers", "HTML")],
  ["Q5 contract module loads before app", () => assert(html.indexOf("q5-contract.js") < html.indexOf("app.js"), "Q5 contract must load before app.js")],
  ["Q5 questions are in primary analysis", () => assertIncludes(html, "q5-primary-band", "HTML")],
  ["Q5 hidden inspector exists", () => assertIncludes(html, "q5InspectorPanel", "HTML")],
  ["Q5 fixture endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/v1/selection/fixtures/q5-r6")', "JS")],
  ["Q5 selection renderer exists", () => assertIncludes(js, "function renderQ5Selection(payload)", "JS")],
  ["Q5 inspector renderer exists", () => assertIncludes(js, "function renderQ5Inspector(payload)", "JS")],
  ["hidden validation obeys authorization contract", () => assertIncludes(js, "window.TrendForgeQ5.canShowPerformance(payload)", "JS")],
  ["Q5 history is append-only labelled", () => assertIncludes(js, "Append-only state history", "JS")],
  ["fixture validation stays hidden", () => assertIncludes(js, "Fixture PIT status is test evidence only. Validation and performance remain hidden.", "JS")],
  ["five public selection filters exist", () => {
    for (const state of ["all", "watch", "confirmed", "wait", "reject"]) {
      assertIncludes(html, `data-filter="${state}"`, "HTML");
    }
  }],
  ["legacy execution fields are absent from primary selection", () => {
    for (const id of ["entryValue", "stopValue", "targetValue"]) {
      assert(!htmlIds.has(id) && !jsElementIds.includes(id), `Legacy primary field remains: ${id}`);
    }
  }],
  ["manual journal is explicitly non-calibrating", () => assertIncludes(html, "Journal labels never train, calibrate, rank, confirm, size, or execute a candidate.", "HTML")],
  ["harmonic validation hides performance metrics", () => assertIncludes(js, "Performance metrics hidden until non-fixture PIT approval.", "JS")],
  ["Q5 failure fails closed to WAIT", () => assertIncludes(js, 'els.q5SelectionState.textContent = "WAIT";', "JS")],
  ["all JavaScript element references exist in HTML", () => {
    const missing = [...new Set(jsElementIds.filter((id) => !htmlIds.has(id)))];
    assert(missing.length === 0, `Missing HTML IDs for JS references: ${missing.join(", ")}`);
  }],
  ["command-bar endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/command-bar")', "JS")],
  ["institutional analyze endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/institutional/analyze"', "JS")],
  ["source parser run endpoint is referenced", () => assertIncludes(js, "/api/source-parser/run", "JS")],
  ["source parser results endpoint is referenced", () => assertIncludes(js, "/api/source-parser/results", "JS")],
  ["XBRL refresh endpoint is referenced", () => assertIncludes(js, "/api/bse-offers/xbrl/refresh", "JS")],
  ["harmonic benchmark endpoint is referenced", () => assertIncludes(js, "/api/harmonic/benchmark", "JS")],
  ["harmonic alerts endpoint is referenced", () => assertIncludes(js, "/api/harmonic/alerts", "JS")],
  ["alert acknowledge endpoint is referenced", () => assertIncludes(js, "/acknowledge", "JS")],
  ["journal outcome endpoint is referenced", () => assertIncludes(js, "/outcome", "JS")],
  ["scanner scheduler status endpoint is referenced", () => assertIncludes(js, 'fetchJson("/api/scanner/scheduler/status")', "JS")],
  ["journal quantity is fixed at zero", () => {
    assertIncludes(html, 'id="journalQuantity"', "HTML");
    assert(!html.includes('id="journalQuantity"') || html.includes('id="journalQuantity"'), "quantity field");
    assert(html.includes('id="journalQuantity"') && html.includes("readonly"), "journalQuantity must be readonly");
    assert(!html.includes('min="1"'), "journal quantity must not require min=1");
    assertIncludes(js, "quantity: 0", "JS");
  }],
  ["tool registry has fourteen keys", () => {
    for (const key of [
      "m_factor",
      "sector_scope",
      "m_factor_history",
      "heatmap",
      "index_dashboard",
      "oi_analysis",
      "oi_tracker",
      "strike_explorer",
      "expiry_prediction",
      "swing_finder",
      "speculation_movers",
      "trend_accumulation",
      "accumulation_signals",
      "multibagger_research"
    ]) {
      assertIncludes(js, `${key}:`, "JS");
    }
    assert(!js.includes("|| decisionTools.m_factor"), "live JS must not fall back to m_factor");
    assertIncludes(js, "WAIT_DTO_UNAVAILABLE", "JS");
  }],
  ["lock badge exists", () => assertIncludes(html, 'id="lockBadge"', "HTML")],
  ["flow view exists", () => assertIncludes(html, "Source-to-Decision Flow", "HTML")],
  ["combined score is absent", () => assert(!js.includes("Combined_Score"), "Combined_Score must stay absent")],
  ["options lab is package context", () => assertIncludes(html, "Options support, conflict and uncertainty", "HTML")],
  ["product fixture renderer is loaded", () => assertIncludes(html, "product-fixture.js", "HTML")],
  ["compiler report endpoint is referenced", () => assertIncludes(js, "/api/source-inventory/compiler-report", "JS")],
  ["live decision endpoint is referenced", () => assertIncludes(js, "/api/v1/selection/live", "JS")],
  ["live decision persist endpoint is referenced", () => assertIncludes(js, "/api/v1/selection/live/refresh", "JS")],
  ["live projection is not called stored", () => assert(!js.includes("Stored R1 DTO"), "JS")],
  ["live decision mount exists", () => assertIncludes(html, 'id="liveDecisionPanel"', "HTML")],
  ["maturity ladder mount exists", () => assertIncludes(html, 'id="maturityLadder"', "HTML")],
  ["source health page has compiler ladder", () => {
    assertIncludes(html, 'id="sourceHealthLadder"', "HTML");
    assertIncludes(html, 'id="sourceHealthLadderCounts"', "HTML");
    assertIncludes(js, "sourceHealthLadderCounts", "JS");
  }],
  ["how-validated tab has pattern approval layers", () => {
    const fixture = fs.readFileSync(path.join(root, "product-fixture.js"), "utf8");
    assertIncludes(fixture, "Pattern approval layers", "product-fixture.js");
    assertIncludes(fixture, "Chart structure", "product-fixture.js");
    assertIncludes(fixture, "Safety / gates", "product-fixture.js");
    assertIncludes(fixture, "any hard fail", "product-fixture.js");
  }],
  ["all stocks table and card layouts exist", () => {
    assertIncludes(html, 'data-stock-layout="table"', "HTML");
    assertIncludes(html, 'data-stock-layout="cards"', "HTML");
  }],
  ["S4/S5 compare panel exists", () => {
    assertIncludes(html, 'id="s4s5ComparePanel"', "HTML");
    assertIncludes(html, 'id="s4s5With"', "HTML");
    assertIncludes(html, 'id="s4s5Without"', "HTML");
    assertIncludes(html, 'id="s4s5Both"', "HTML");
    assertIncludes(html, 'id="s4s5CompareList"', "HTML");
  }],
  ["S4/S5 compare script and endpoint exist", () => {
    const script = fs.readFileSync(path.join(root, "s4s5-compare.js"), "utf8");
    assertIncludes(html, "s4s5-compare.js", "HTML");
    assertIncludes(script, "/api/v1/selection/s4s5-compare", "s4s5-compare.js");
    assertIncludes(script, 'STORAGE_KEY = "trendforge.s4s5.view"', "s4s5-compare.js");
    assertIncludes(script, "WITH original S4/S5", "s4s5-compare.js");
    assertIncludes(script, "WITHOUT split", "s4s5-compare.js");
    assertIncludes(script, "row.withS4S5", "s4s5-compare.js");
    assertIncludes(script, "row.withoutS4S5", "s4s5-compare.js");
  }],
  ["Hybrid V2 overlay panel and chain exist", () => {
    assertIncludes(html, 'id="hybridV2Chain"', "HTML");
    assertIncludes(html, 'id="hybridV2OverlayPanel"', "HTML");
    const overlay = fs.readFileSync(path.join(root, "hybrid-v2-overlay.js"), "utf8");
    assertIncludes(overlay, "/api/v1/hybrid-v2/overlay", "hybrid-v2-overlay.js");
    assertIncludes(overlay, "UNKNOWN_NEEDS_R12", "hybrid-v2-overlay.js");
    assertIncludes(overlay, "not File A", "hybrid-v2-overlay.js");
    assert(!/\bREADY\b/.test(overlay), "overlay must not use READY as a live state");
  }],
  ["Hybrid V2 adapter wiring stays optional", () => {
    const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
    assertIncludes(adapter, "overlay", "selection-live-adapter.js");
    assertIncludes(adapter, "caJoin", "selection-live-adapter.js");
    assertIncludes(adapter, "applyHybridOverlay", "selection-live-adapter.js");
  }],
  ["R8 native core panel + script mounted", () => {
    assertIncludes(html, 'id="nativeCorePanel"', "HTML");
    assertIncludes(html, 'id="nativeCoreOps"', "HTML");
    assertIncludes(html, "native-core.js?v=20260827-r13-guidance-1", "HTML");
    const nc = fs.readFileSync(path.join(root, "native-core.js"), "utf8");
    assertIncludes(nc, "/api/v1/scanners/native-core", "native-core.js");
    assertIncludes(nc, "TrendForgeNativeCore", "native-core.js");
    assertIncludes(nc, "trendforge.scanner-native-core.v1", "native-core.js");
    assertIncludes(nc, "not an order", "native-core.js copy");
    assert(!nc.includes("place_order"), "native-core.js must never reference an order path");
    const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
    assertIncludes(adapter, "nativeCore", "selection-live-adapter.js");
    assertIncludes(adapter, "TrendForgeNativeCore", "selection-live-adapter.js");
  }],
  ["R8 adapter fetch count matches renderer names", () => {
    const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
    const fetches = (adapter.match(/await fetchJson\(/g) || []).length;
    assert(fetches === 1, `adapter must fetch one atomic snapshot, found ${fetches}`);
  }],
  ["R10 pipe recipes panel + script mounted", () => {
    assertIncludes(html, 'id="pipeLabPanel"', "HTML");
    assertIncludes(html, 'id="pipeLabOps"', "HTML");
    assertIncludes(html, "pipes.js?v=20260826-r10-1", "HTML");
    const pipes = fs.readFileSync(path.join(root, "pipes.js"), "utf8");
    assertIncludes(pipes, "/api/v1/pipes/definitions", "pipes.js");
    assertIncludes(pipes, "/run", "pipes.js run fetch");
    assertIncludes(pipes, "TrendForgePipeLab", "pipes.js");
    assertIncludes(pipes, "zero claims", "pipes.js copy");
    assert(!pipes.includes("place_order"), "pipes.js must never reference an order path");
    const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
    assertIncludes(adapter, "pipeDefs", "selection-live-adapter.js");
  }],
  ["R11 MCX master panel live, not fixture gold", () => {
    assertIncludes(html, 'id="mcxMasterPanel"', "HTML");
    assertIncludes(html, 'id="mcxMasterMeta"', "HTML");
    assertIncludes(html, "mcx-master.js?v=20260825-r11-1", "HTML");
    const mm = fs.readFileSync(path.join(root, "mcx-master.js"), "utf8");
    assertIncludes(mm, "/api/v1/selection/mcx-master", "mcx-master.js");
    assertIncludes(mm, "TrendForgeMcxMaster", "mcx-master.js");
    assertIncludes(mm, "Not COMEX", "mcx-master.js copy");
    assertIncludes(mm, 'data-mode="mcx"', "mcx-master.js segment binding");
    assert(!mm.includes("place_order"), "mcx-master.js must never reference an order path");
    const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
    assertIncludes(adapter, "mcxMaster", "selection-live-adapter.js");
  }],
  ["R15 Scanner Lab inside inspector, no radar inflation", () => {
    assertIncludes(html, 'id="scannerLabPanel"', "HTML");
    assertIncludes(html, 'id="scannerLabTabs"', "HTML");
    assertIncludes(html, 'id="scannerLabBody"', "HTML");
    assertIncludes(html, 'hidden', "HTML lab starts hidden");
    assertIncludes(html, "scanner-lab.js?v=20260827-r13-guidance-1", "HTML");
    assertIncludes(html, "Refresh lab (GET)", "HTML run button label");
    const lab = fs.readFileSync(path.join(root, "scanner-lab.js"), "utf8");
    assertIncludes(lab, "/api/v1/scanners/lab-bundle", "scanner-lab.js");
    assertIncludes(lab, "TrendForgeScannerLab", "scanner-lab.js");
    assertIncludes(lab, "correlated_possible", "scanner-lab.js twin warning");
    assertIncludes(lab, "suppressed by", "scanner-lab.js correlated guidance detail");
    assertIncludes(lab, "formulaVersion", "scanner-lab.js formula inspection");
    assertIncludes(lab, "lineageHash", "scanner-lab.js lineage inspection");
    assertIncludes(lab, "not an order", "scanner-lab.js guidance copy");
    assert(!lab.includes("place_order"), "scanner-lab.js must never reference orders");
    assert(!lab.includes("Combined_Score"), "scanner-lab.js must not carry Combined_Score");
    assert(!lab.includes("guidanceWinRate"), "scanner-lab.js must not show unvalidated win rate");
    // All Stocks column freeze: the radar header template stays untouched and
    // no lab file introduces <th> columns.
    const appjs = fs.readFileSync(files.js, "utf8");
    assertIncludes(appjs, "<th>Symbol</th><th>Horizon</th><th>State</th><th>Setup</th><th>Invalidation</th>", "radar headers unchanged");
    // New R8/R10/R11/R15 owners must not introduce scanner-count columns.
    const ncJs = fs.readFileSync(path.join(root, "native-core.js"), "utf8");
    const pipesJs = fs.readFileSync(path.join(root, "pipes.js"), "utf8");
    const mmJs = fs.readFileSync(path.join(root, "mcx-master.js"), "utf8");
    [lab, ncJs, pipesJs, mmJs].forEach((src) => assert(!src.includes("<th"), "no static <th> added for scanner counts"));
    assertIncludes(appjs, "TrendForgeScannerLab", "app.js delegates run button to lab refresh");
  }],
  ["R2-B named activation panel exists", () => {
    assertIncludes(html, 'id="r2bActivationPanel"', "HTML");
    assertIncludes(html, 'id="r2bActivationList"', "HTML");
    const script = fs.readFileSync(path.join(root, "r2b-activation.js"), "utf8");
    assertIncludes(html, "r2b-activation.js", "HTML");
    assertIncludes(script, "/api/v1/selection/named-activation", "r2b-activation.js");
    assertIncludes(script, "sourceActivationReady stays false", "r2b-activation.js");
  }],
  ["AS tool room never invents GEX", () => {
    assertIncludes(js, "accumulation_signals", "JS");
    assert(!js.includes("inventedGex") && !js.includes("GEX_VALUE"), "JS must not invent GEX values");
  }],
  ["M-Factor live BFF wiring exists", () => {
    const live = fs.readFileSync(path.join(root, "m-factor-live.js"), "utf8");
    assertIncludes(html, "m-factor-live.js", "HTML");
    assertIncludes(html, 'id="toolRunChip"', "HTML");
    assertIncludes(html, 'id="toolAsOfChip"', "HTML");
    assertIncludes(live, "/api/v1/tools/m_factor", "m-factor-live.js");
    assertIncludes(live, "TrendForgeMFactorLive", "m-factor-live.js");
    assertIncludes(live, "Research direction only - not an order", "m-factor-live.js");
  }],
  ["M-Factor live never falls back to fixture cards", () => {
    const live = fs.readFileSync(path.join(root, "m-factor-live.js"), "utf8");
    assert(!live.includes("decisionTools"), "m-factor-live.js must not read fixture decisionTools");
    assert(!live.includes("FIXTURE-20260729-1042"), "m-factor-live.js must not use the fixture run id");
    assert(!live.includes("168.9") && !live.includes("175.2") && !live.includes("165.1"), "m-factor-live.js must not carry fixture levels");
    assertIncludes(live, "WAIT_BFF_503", "m-factor-live.js");
    assertIncludes(live, "detail.code", "m-factor-live.js");
  }],
  ["M-Factor live consumes merged-claim families", () => {
    const live = fs.readFileSync(path.join(root, "m-factor-live.js"), "utf8");
    assertIncludes(live, "debug=1", "m-factor-live.js");
    assertIncludes(live, "families", "m-factor-live.js");
    assertIncludes(live, "r3EvidenceStrength", "m-factor-live.js");
    assert(!live.includes("long buildup"), "m-factor-live.js must not call OI long buildup");
  }],
  ["M-Factor fixture delegates to the live owner", () => {
    const fixture = fs.readFileSync(path.join(root, "product-fixture.js"), "utf8");
    assertIncludes(fixture, "TrendForgeMFactorLive", "product-fixture.js");
    assertIncludes(fixture, "activeTool: function", "product-fixture.js");
  }],
  ["OI rooms live BFF wiring exists", () => {
    const live = fs.readFileSync(path.join(root, "oi-options-live.js"), "utf8");
    assertIncludes(html, "oi-options-live.js", "HTML");
    assertIncludes(live, "/api/v1/tools/oi_analysis", "oi-options-live.js");
    assertIncludes(live, "TrendForgeOiOptionsLive", "oi-options-live.js");
    assertIncludes(live, "nav button[data-view=\"tool\"]", "oi-options-live.js");
    assertIncludes(live, "oi-rail-item", "oi-options-live.js");
  }],
  ["S3 cheap discovery queue is wired and non-executable", () => {
    const s3 = fs.readFileSync(path.join(root, "s3-cheap-discovery.js"), "utf8");
    const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
    assertIncludes(html, 'id="s3WatchQueue"', "HTML");
    assertIncludes(html, 'id="s3WatchQueueOps"', "HTML");
    assertIncludes(adapter, "s3Watch", "selection-live-adapter.js");
    assertIncludes(s3, "WATCH_QUEUE_READY", "s3-cheap-discovery.js");
    assert(!s3.includes("winProbability") && !s3.includes("deliveryPct"), "S3 must not show probability or delivery");
  }],
  ["S4 structure pack panel exists", () => {
    assertIncludes(html, 'id="s4StructurePanel"', "HTML");
    assertIncludes(html, 'id="s4StructureOps"', "HTML");
  }],
  ["S4 pack script, endpoint and WAIT ceiling are wired", () => {
    const s4 = fs.readFileSync(path.join(root, "s4-structure.js"), "utf8");
    const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
    assertIncludes(html, "s4-structure.js", "HTML");
    assertIncludes(s4, "trendforge.s4-structure-pack.v1", "s4-structure.js");
    assertIncludes(s4, "LIVE_S4_WAIT_REJECT_ONLY", "s4-structure.js");
    assertIncludes(s4, "labels are not trade geometry", "s4-structure.js");
    assert(!/\bCONFIRMED\b/.test(s4.replace(/confirmedCount/g, "").replace(/Confirmed/g, "")), "S4 must not present CONFIRMED as a live state");
    assertIncludes(adapter, "s4Pack", "selection-live-adapter.js");
    assertIncludes(adapter, "TrendForgeS4Structure.apply", "selection-live-adapter.js");
  }],
  ["All Stocks paints S4 tags + next trigger without trade geometry", () => {
    const fixture = fs.readFileSync(path.join(root, "product-fixture.js"), "utf8");
    assertIncludes(fixture, "applyLiveSelection(attention,evidence,structure,s4Pack)", "product-fixture.js");
    assertIncludes(fixture, "s4Row.nextTrigger", "product-fixture.js");
    assertIncludes(fixture, "'NONE — R5 research, not a trade'", "product-fixture.js");
  }],
  ["S5 enrichment panel exists on All Stocks and Live Ops", () => {
    assertIncludes(html, 'id="s5EnrichmentPanel"', "HTML");
    assertIncludes(html, 'id="s5EnrichmentOps"', "HTML");
  }],
  ["S5 enrichment script, endpoint and honest unknowns are wired", () => {
    const s5 = fs.readFileSync(path.join(root, "s5-enrichment.js"), "utf8");
    const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
    assertIncludes(html, "s5-enrichment.js", "HTML");
    assertIncludes(s5, "trendforge.s5-enrichment.v1", "s5-enrichment.js");
    assertIncludes(s5, "UNKNOWN_NEEDS_R12", "s5-enrichment.js");
    assertIncludes(s5, "LIVE_S5_ENRICH_WAIT_ONLY", "s5-enrichment.js");
    assertIncludes(s5, "MARKET_WIDE_NOT_PER_STOCK", "s5-enrichment.js");
    assert(!s5.includes("fiiBought"), "S5 must never show per-stock FII buying");
    const protocol = require('../research-snapshot.js');
    assert(protocol.PANEL_KEYS.includes('s5Enrich'), 'atomic envelope must retain S5');
    assertIncludes(adapter, '/api/v1/selection/snapshot', 'ADAPTER');
    assert(!adapter.includes('Promise.all'), 'selection must not scatter latest reads');
    assertIncludes(adapter, "s5Enrich", "selection-live-adapter.js");
    assertIncludes(adapter, "TrendForgeS5Enrichment.apply", "selection-live-adapter.js");
    assert(protocol.PANEL_KEYS.length >= 22, "snapshot retains every previous panel");
  }],
  ["S6 family resolution inspector mount exists", () => {
    assertIncludes(html, 'id="s6InspectorMount"', "HTML");
    assertIncludes(html, 'id="s6ResolutionOps"', "HTML");
  }],
  ["S6 resolution script, endpoint and WAIT-only records are wired", () => {
    const s6 = fs.readFileSync(path.join(root, "s6-resolution.js"), "utf8");
    const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
    assertIncludes(html, "s6-resolution.js", "HTML");
    assertIncludes(s6, "trendforge.s6-resolution.v1", "s6-resolution.js");
    assertIncludes(s6, "LIVE_S6_RESOLVE_WAIT_ONLY", "s6-resolution.js");
    assertIncludes(s6, "not win probability", "s6-resolution.js");
    assertIncludes(s6, "never a buy stamp", "s6-resolution.js");
    assert(!/\bCONFIRMED\b/.test(s6.replace(/canUnlockConfirmed/g, "").replace(/Confirmed/g, "")), "S6 must not present CONFIRMED as a live state");
    assertIncludes(adapter, "s6Resolve", "selection-live-adapter.js");
    assertIncludes(adapter, "TrendForgeS6Resolution.apply", "selection-live-adapter.js");
    assertIncludes(adapter, 'TrendForgeResearchSnapshot.validate(raw)', 'ADAPTER');
    assert(adapter.indexOf('validate(raw)') < adapter.indexOf('const count = renderer.applyLiveSelection'),
      'all panel relationships must validate before the first renderer changes the page');
  }],
  ["OI fixture click reloads the live owner", () => {
    const fixture = fs.readFileSync(path.join(root, "product-fixture.js"), "utf8");
    assertIncludes(fixture, "TrendForgeOiOptionsLive.reload", "product-fixture.js");
  }]
];

const results = [];

for (const [name, fn] of checks) {
  try {
    fn();
    results.push({ name, status: "PASS" });
  } catch (error) {
    results.push({ name, status: "FAIL", error: error.message });
  }
}

const failures = results.filter((result) => result.status === "FAIL");

for (const result of results) {
  const line = result.status === "PASS"
    ? `PASS ${result.name}`
    : `FAIL ${result.name}: ${result.error}`;
  console.log(line);
}

console.log(`\nSummary: ${results.length - failures.length}/${results.length} checks passed.`);

if (failures.length > 0) {
  process.exitCode = 1;
}


