"""Build frontend/index.html = exact FINAL_PRODUCT chrome + hidden/live-ops remounts."""
from pathlib import Path

root = Path(r"D:\TrendForge\frontend")
body = (root / "_fixture_body.html").read_text(encoding="utf-8")
body = body.replace('id="sourceGrid"', 'id="fixtureSourceGrid"')
body = body.replace('<header class="top">', '<header class="top command-bar">')
body = body.replace(
    '<span class="chip header-mode">RESEARCH_SHADOW_ONLY</span>',
    """<span class="chip header-mode">RESEARCH_SHADOW_ONLY</span>
              <span class="chip bad lock-badge" id="lockBadge">LOCKED_NO_TRADE</span>
              <div class="status-strip" aria-label="Global market state">
                <div class="status-pill"><span>System</span><strong id="systemStatus">RESEARCH_ONLY</strong></div>
                <div class="status-pill"><span>Regime</span><strong id="regimeStatus">UNVERIFIED</strong></div>
                <div class="status-pill"><span>India VIX</span><strong id="vixStatus">WAIT_DATA</strong></div>
                <div class="status-pill"><span>Safety</span><strong id="safetyStatus">LOCKED_DATA</strong></div>
                <div class="status-pill"><span>NSE Session</span><strong id="calendarStatus">WAIT_CALENDAR</strong></div>
              </div>
              <button class="panic-button" type="button" id="panicButton"><span>Lock Research</span></button>""",
)
body = body.replace(
    '<button data-view="flow">',
    """<button data-view="live-ops"><span><span class="nav-glyph">LO</span>Live Ops</span><small>wired</small></button>
    <button data-view="flow">""",
    1,
)

live_ops = r'''
<section class="view" id="live-ops">
  <div class="head"><div><h2>Live wired panels</h2><p>Existing :8000 APIs remounted here. Product rooms above keep the exact fixture details.</p></div><span class="chip">LIVE APIS</span></div>
  <input id="searchInput" type="search" placeholder="Search symbol, state, setup, source" />
  <div class="segmented" aria-label="Asset mode">
    <button type="button" class="segment active" data-mode="all">All</button>
    <button type="button" class="segment" data-mode="stock">Stocks</button>
    <button type="button" class="segment" data-mode="harmonic">Harmonic</button>
    <button type="button" class="segment" data-mode="mcx">MCX</button>
  </div>
  <div class="timeframe-strip" aria-label="Timeframes">
    <button type="button" class="tf active" data-timeframe="30m">30m</button>
    <button type="button" class="tf active" data-timeframe="1h">1h</button>
    <button type="button" class="tf active" data-timeframe="4h">4h</button>
    <button type="button" class="tf active" data-timeframe="1d">1D</button>
    <button type="button" class="tf active" data-timeframe="1w">1W</button>
  </div>
  <div class="filter-row">
    <button type="button" class="filter active" data-filter="all">All</button>
    <button type="button" class="filter" data-filter="watch">Watch</button>
    <button type="button" class="filter" data-filter="confirmed">Confirmed</button>
    <button type="button" class="filter" data-filter="wait">Wait</button>
    <button type="button" class="filter" data-filter="reject">Reject</button>
  </div>
  <span class="count-badge" id="resultCount">0</span>
  <div class="radar-list" id="radarList"></div>
  <section class="analysis-core" aria-label="Selected candidate analysis">
    <p class="eyebrow" id="selectedType">Stock Intelligence</p>
    <div class="symbol-line"><h2 id="selectedSymbol">WAIT</h2><span class="state-chip warn" id="selectedState">WAIT</span></div>
    <p class="reason-line" id="selectedReason">Live candidate</p>
    <span id="selectedPrice">-</span><strong id="selectedMove">-</strong>
    <canvas id="marketPulse" width="860" height="220" aria-label="Mock price path visual"></canvas>
    <div class="metrics-grid" id="metricsGrid"></div>
    <h3 id="decisionTitle">WAIT</h3>
    <p id="decisionText">Research state only.</p>
    <strong id="nextCheckValue">WAIT</strong>
    <strong id="invalidationValue">UNKNOWN</strong>
    <strong id="dataModeValue">RESEARCH</strong>
    <section class="q5-primary-band">
      <span class="state-chip warn" id="q5SelectionState">WAIT</span>
      <p class="research-status" id="q5SelectionLabel">Evidence strength - not win probability</p>
      <div class="q5-answer-grid" id="q5RadarAnswers"></div>
    </section>
  </section>
  <aside class="proof-rail">
    <details class="q5-inspector" id="q5Inspector">
      <summary><span>Evidence Inspector</span><span id="q5InspectorStatus">FIXTURE ONLY</span></summary>
      <div class="q5-inspector-tabs" id="q5InspectorTabs"></div>
      <div class="q5-inspector-panel" id="q5InspectorPanel"></div>
      <div class="q5-history-list" id="q5HistoryList"></div>
      <p class="q5-validation-lock" id="q5ValidationLock">Validation details remain hidden until non-fixture PIT approval.</p>
    </details>
    <button class="icon-button" type="button" id="refreshButton">Refresh health</button>
    <div class="proof-list" id="proofList"></div>
    <div class="risk-ring" id="riskRing"><span id="riskScore">0</span></div>
    <div class="risk-lines" id="riskLines"></div>
    <div class="source-grid" id="sourceGrid"></div>
  </aside>
  <div class="market-activity-panel">
    <strong id="marketActivityStatus">WAIT_SNAPSHOT</strong>
    <button type="button" id="marketActivityRefresh">Refresh activity</button>
    <p id="marketActivityMeta">Research-only evidence. Refresh to rank volume spurts, most-active stocks, and named large deals.</p>
    <div id="marketActivityList"></div>
  </div>
  <div class="commodity-context-panel">
    <strong id="commodityContextStatus">WAIT_SNAPSHOT</strong>
    <p id="commodityContextMeta">Research context only. No individual source can produce CONFIRMED.</p>
    <div id="commodityContextList"></div>
  </div>
  <input id="harmonicSymbolInput" type="text" value="RELIANCE" />
  <select id="harmonicTimeframeSelect"><option value="30m">30m</option><option value="1h">1h</option><option value="4h">4h</option><option value="1d" selected>1d</option><option value="1w">1w</option></select>
  <input id="harmonicUseStored" type="checkbox" />
  <button type="button" id="harmonicScanButton">Run Harmonic Scan</button>
  <button type="button" id="advancedHarmonicButton">Advanced Gates</button>
  <button type="button" id="harmonicBacktestButton">Time-Safe Backtest</button>
  <p id="harmonicScanStatus">Research-only scan. Unofficial or incomplete evidence cannot produce CONFIRMED.</p>
  <div id="advancedHarmonicBox"></div>
  <div id="harmonicResultList"></div>
  <strong id="sourceRegistryStatus">-</strong>
  <strong id="parquetStatus">-</strong>
  <strong id="sourceMonitorStatus">-</strong>
  <strong id="gateReadinessStatus">-</strong>
  <strong id="scannerSchedulerStatus">-</strong>
  <strong id="rawArchiveStatus">-</strong>
  <strong id="riskSettingsStatus">-</strong>
  <strong id="universeStatus">-</strong>
  <strong id="officialContextStatus">-</strong>
  <div class="parser-drilldown" id="parserDrilldown">
    <select id="parserSourceSelect">
      <option value="nse_index_close_eod">NSE Indices / VIX</option>
      <option value="nse_bhavcopy_eod">NSE Cash Bhavcopy</option>
      <option value="nse_fno_ban">NSE F&amp;O Ban</option>
      <option value="nse_mwpl_percentages">NSE MWPL %</option>
      <option value="nse_equity_universe">NSE Equity Master</option>
      <option value="nse_nifty500_constituents">Nifty 500 Industry</option>
      <option value="nse_large_deals">NSE Deals</option>
      <option value="nse_fii_dii">NSE FII/DII</option>
      <option value="nsdl_fpi_daily">NSDL FPI Trends</option>
      <option value="nse_asm">NSE ASM</option>
      <option value="nse_gsm">NSE GSM</option>
      <option value="nse_pledge_data">NSE Pledge Data</option>
      <option value="nse_participant_oi">Participant OI</option>
      <option value="nse_fo_bhavcopy">NSE F&amp;O Bhavcopy</option>
      <option value="nse_oi_spurts">NSE OI Spurts</option>
      <option value="nse_option_chain">NSE Option Chain</option>
      <option value="nse_slb">NSE SLB</option>
      <option value="amfi_monthly_portfolio">AMFI</option>
      <option value="amfi_nav">AMFI NAV</option>
      <option value="nse_pit_current">NSE Current PIT</option>
      <option value="nse_corporate_filings_actions">NSE Corporate Actions</option>
      <option value="bse_buyback_tender">BSE Buyback</option>
      <option value="bse_takeover_open_offer">BSE Open Offer</option>
      <option value="sebi_pit_sast">SEBI PIT/SAST</option>
      <option value="cftc_cot">CFTC COT</option>
      <option value="mcx_bhavcopy">MCX Bhavcopy</option>
    </select>
    <button type="button" id="parserRefreshButton">Parse</button>
    <button type="button" id="scannerRunButton">Run Scanner</button>
    <div id="parserGrid"></div>
  </div>
  <span id="institutionalState">WAIT</span>
  <strong id="institutionalSourceCount">-</strong>
  <strong id="institutionalModelCount">-</strong>
  <strong id="institutionalAccount">-</strong>
  <strong id="institutionalAuditCount">-</strong>
  <form id="institutionalForm">
    <input data-factor="smartMoney" type="number" />
    <button type="submit" id="institutionalEvaluateButton">Evaluate Evidence</button>
  </form>
  <span id="institutionalMarker"></span>
  <strong id="institutionalClassification">WAIT_DATA</strong>
  <span id="institutionalScore">Evidence strength - not win probability</span>
  <p id="institutionalReason">No normalized factor evidence evaluated.</p>
  <span id="generalAlertCount">0</span>
  <button type="button" id="refreshAlertsButton">Refresh alerts</button>
  <div id="generalAlertList"></div>
  <span id="journalCount">0</span>
  <p>Manual annotation only. Journal labels never train, calibrate, rank, confirm, size, or execute a candidate.</p>
  <form id="journalCreateForm">
    <input id="journalSymbol" name="symbol" required />
    <input id="journalSetup" name="setup" required />
    <select id="journalMode"><option>INTRADAY</option><option>SWING</option></select>
    <select id="journalDirection"><option>LONG</option><option>SHORT</option></select>
    <input id="journalDecisionState" name="decisionState" value="WAIT" required />
    <input id="journalQuantity" name="quantity" type="number" min="0" max="0" value="0" readonly />
    <input id="journalEntryPrice" name="entryPrice" type="number" />
    <input id="journalStopPrice" name="stopPrice" type="number" />
    <input id="journalOpenedAt" name="openedAt" type="datetime-local" required />
    <textarea id="journalNotes"></textarea>
    <button type="submit">Add Record</button>
  </form>
  <form id="journalOutcomeForm">
    <select id="journalRecordSelect" required></select>
    <select id="journalOutcomeState"><option>WIN</option><option>LOSS</option><option>BREAKEVEN</option><option>EXPIRED</option><option>CANCELLED</option></select>
    <input id="journalExitPrice" type="number" required />
    <input id="journalPnl" type="number" />
    <input id="journalRMultiple" type="number" />
    <input id="journalClosedAt" type="datetime-local" required />
    <textarea id="journalOutcomeNotes"></textarea>
    <button type="submit">Update Outcome</button>
  </form>
  <p id="journalStatus"></p>
  <div id="journalList"></div>
  <span id="researchCount">0</span>
  <textarea id="researchNote"></textarea>
  <input id="researchTags" />
  <button type="button" id="saveResearchButton">Save Snapshot</button>
  <p id="researchStatus"></p>
  <strong id="mlRunCount">0</strong>
  <strong id="mlCandidateCount">0</strong>
  <p id="mlCaptureStatus">Full radar scans are saved automatically for future ML training.</p>
  <div id="researchList"></div>
</section>
'''

if "<p class=\"footer\">" in body:
    body = body.replace("<p class=\"footer\">", live_ops + "<p class=\"footer\">", 1)
else:
    body += live_ops

page = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>TrendForge Research Terminal</title>
    <link rel="stylesheet" href="./styles.css?v=20260814-exact1" />
    <link rel="stylesheet" href="./theme-final.css?v=20260814-exact1" />
    <script src="./q5-contract.js?v=20260720-r6" defer></script>
    <script src="./product-fixture.js?v=20260814-exact1" defer></script>
    <script src="./app.js?v=20260814-exact1" defer></script>
  </head>
  <body class="final-shell">
{body}
    <dialog id="recoveryDialog" class="recovery-dialog" aria-labelledby="recoveryTitle">
      <form id="recoveryForm" method="dialog">
        <h2 id="recoveryTitle">Recovery Checklist</h2>
        <button id="recoveryClose" type="button">X</button>
        <label class="recovery-check"><input type="checkbox" name="recovery" /> I know why research was locked.</label>
        <label class="recovery-check"><input type="checkbox" name="recovery" /> I accept this unlock is research-only, not a trade resume.</label>
        <label class="recovery-check"><input type="checkbox" name="recovery" /> I will not treat unlock as size or order permission.</label>
        <label class="recovery-check"><input type="checkbox" name="recovery" /> I will review only a fresh closed-bar setup.</label>
        <label class="recovery-check"><input type="checkbox" name="recovery" /> I accept the next invalidation is research geometry, not a broker stop.</label>
        <textarea id="recoveryReason" required></textarea>
        <p id="recoveryStatus">Cooldown and checklist are both required.</p>
        <button id="recoverySubmit" type="submit" disabled>Request Unlock</button>
      </form>
    </dialog>
  </body>
</html>
"""
(root / "index.html").write_text(page, encoding="utf-8")
print("wrote index.html", len(page))
