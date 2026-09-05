/* M-Factor live view owner (m_factor tool only).
   Contract: docs/fable/remaining_build/M_FACTOR_LIVE_UI_OPENCODE_PROMPT.md.
   Consumes GET /api/v1/tools/m_factor. On 200 it paints the live Signals /
   How validated / Track record / Engines used tabs from the BFF DTO. On 503
   or network failure it paints the typed WAIT code. It never falls back to
   the static fixture cards for this tool. */
(() => {
  "use strict";

  const CONTRACT = "trendforge.m-factor-live.v1";
  const ACCENT = "#0d756c";
  const HORIZONS = [
    { key: "intra", label: "intra", eyebrow: "INTRADAY F&O PRIORITY - NOT ACTIVATED" },
    { key: "swing", label: "swing", eyebrow: "SWING EOD RESEARCH - LIVE R3 FUS-009" },
    { key: "position", label: "position", eyebrow: "POSITIONAL RESEARCH - NOT WIRED" },
    { key: "commodity", label: "commodity", eyebrow: "MCX COMMODITY - LOCAL ONLY, NOT WIRED" }
  ];
  const SIDES = ["both", "buy", "sell"];
  const TABS = ["signals", "validation", "track", "engines"];

  const state = {
    horizon: "swing",
    side: "both",
    tab: "signals",
    batch: null,
    error: null,
    loading: true,
    selectedSymbol: null,
    requestGeneration: 0
  };

  function esc(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[ch]));
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function allRows() {
    const batch = state.batch;
    if (!batch) return [];
    return (batch.buyRows || []).concat(batch.sellRows || []).concat(batch.waitRows || []);
  }

  function selectedRow() {
    const rows = allRows();
    return rows.find((row) => row.symbol === state.selectedSymbol) || rows[0] || null;
  }

  async function load() {
    const generation = ++state.requestGeneration;
    state.loading = true;
    state.error = null;
    render();
    let response;
    try {
      response = await fetch(
        `/api/v1/tools/m_factor?horizon=${encodeURIComponent(state.horizon)}` +
          `&side=${encodeURIComponent(state.side)}&limit=40&debug=1`,
        { cache: "no-store", headers: { Accept: "application/json" } }
      );
    } catch (loadError) {
      if (generation !== state.requestGeneration) return;
      state.loading = false;
      state.batch = null;
      state.error = { code: "WAIT_BFF_UNREACHABLE", message: String(loadError.message || loadError) };
      render();
      return;
    }
    if (generation !== state.requestGeneration) return;
    if (response.status === 503) {
      let code = "WAIT_BFF_503";
      let message = "The M-Factor BFF failed closed.";
      try {
        const payload = await response.json();
        code = (payload && payload.detail && payload.detail.code) || code;
        message = (payload && payload.detail && payload.detail.message) || message;
      } catch (_parseError) {
        /* the status code alone is enough */
      }
      state.loading = false;
      state.batch = null;
      state.error = { code, message };
      render();
      return;
    }
    if (!response.ok) {
      state.loading = false;
      state.batch = null;
      state.error = { code: `WAIT_BFF_HTTP_${response.status}`, message: "Unexpected BFF status." };
      render();
      return;
    }
    try {
      const batch = await response.json();
      if (generation !== state.requestGeneration) return;
      state.loading = false;
      state.batch = batch;
      state.error = null;
      const first = (batch.buyRows || [])[0] || (batch.sellRows || [])[0] || (batch.waitRows || [])[0];
      state.selectedSymbol = first ? first.symbol : null;
    } catch (parseError) {
      state.loading = false;
      state.batch = null;
      state.error = { code: "WAIT_BFF_MALFORMED", message: String(parseError.message || parseError) };
    }
    render();
  }

  function renderHero(batch) {
    const hero = byId("toolHero");
    if (hero) hero.style.setProperty("--tool-accent", ACCENT);
    const spec = HORIZONS.find((item) => item.key === state.horizon) || HORIZONS[1];
    if (byId("toolEyebrow")) byId("toolEyebrow").textContent = spec.eyebrow;
    if (byId("toolTitle")) byId("toolTitle").textContent = "M-Factor";
    if (byId("toolPurpose")) {
      byId("toolPurpose").textContent =
        "Two canonical FUS-009 directional hypotheses per name. No second score, no win probability, no order.";
    }
    const chip = byId("toolState");
    if (chip) {
      const ceiling = state.error
        ? state.error.code
        : batch
          ? batch.horizonWaitCode || batch.stateCeiling || "WAIT"
          : "WAIT_BFF_LOADING";
      chip.textContent = ceiling;
      chip.className = "chip wait";
    }
    const runChip = byId("toolRunChip");
    if (runChip) runChip.textContent = batch ? `RUN ${batch.runId}` : "RUN — LIVE BFF";
    const asOfChip = byId("toolAsOfChip");
    if (asOfChip) {
      asOfChip.textContent = batch ? `AS-OF ${batch.cutoffIst || batch.availableAt}` : "AS-OF —";
    }
  }

  function horizonSwitcher(disabled) {
    const buttons = HORIZONS.map((item) =>
      `<button class="seg${item.key === state.horizon ? " active" : ""}" data-mf-horizon="${esc(item.key)}"${disabled ? " disabled" : ""}>${esc(item.label)}</button>`
    ).join("");
    const sides = SIDES.map((side) =>
      `<button class="seg${side === state.side ? " active" : ""}" data-mf-side="${esc(side)}"${disabled ? " disabled" : ""}>${esc(side.toUpperCase())}</button>`
    ).join("");
    return `<div class="toolbar"><strong>Horizon (one snapshot per board)</strong><div class="seg-row">${buttons}</div><strong>Side</strong><div class="seg-row">${sides}</div><button class="btn" id="mfReload"${disabled ? " disabled" : ""}>Reload</button></div>`;
  }

  function marketStrip(batch) {
    const strip = batch.marketStrip || {};
    const cells = [
      ["Market condition", strip.condition || "UNKNOWN"],
      ["Advancers / decliners", `${strip.advancers == null ? "UNKNOWN" : strip.advancers} / ${strip.decliners == null ? "UNKNOWN" : strip.decliners}`],
      ["Average move", strip.averageMove == null ? "UNKNOWN" : `${strip.averageMove}`],
      ["Universe", String(strip.universeSize == null ? "UNKNOWN" : strip.universeSize)],
      ["Data mode / ceiling", `${esc(batch.dataMode || "")} / ${esc(batch.stateCeiling || "")}`],
      ["Calibration", esc(batch.calibration || "")]
    ];
    return `<div class="tool-market">${cells.map((cell) => `<div class="tool-metric"><span>${esc(cell[0])}</span><strong>${cell[1]}</strong></div>`).join("")}</div>`;
  }

  function barsHtml(row) {
    const items = row
      ? [
          ["Long hypothesis", row.longStrength, ""],
          ["Short hypothesis", row.shortStrength, "opposing"],
          ["Completeness", Math.round((row.completeness || 0) * 100), "blue"]
        ]
      : [["Evidence", 0, "amber"]];
    return `<div class="signal-viz" style="--tool-accent:${ACCENT}"><h3>Evidence contribution view</h3>${items
      .map(
        (item) =>
          `<div class="signal-bar"><span>${esc(item[0])}</span><div class="signal-track"><div class="signal-fill ${esc(item[2])}" style="width:${Math.max(0, Math.min(100, Number(item[1]) || 0))}%"></div></div><strong>${esc(item[1])}</strong></div>`
      )
      .join("")}<div class="tool-note">Evidence points (0-100), not win probability. Bands ${esc(state.batch.classVersion || "M_FACTOR_CLASS_V0")} are uncalibrated.</div></div>`;
  }

  function rankTable(batch) {
    const rows = allRows();
    const head = ["Symbol", "Directional class", "Long / short", "M-balance", "Readiness", "Public state", "Next proof"];
    const body = rows.length
      ? rows
          .map((row) => {
            const selected = row.symbol === (selectedRow() || {}).symbol ? ' class="selected"' : "";
            return `<tr${selected} data-mf-row="${esc(row.symbol)}"><td><strong>${esc(row.symbol)}</strong></td><td>${esc(row.directionalClass)}</td><td>${esc(row.longStrength)} / ${esc(row.shortStrength)}</td><td>${esc(row.mBalance)}</td><td>${esc(row.readinessTag)}</td><td><span class="tag wait">${esc(row.publicState)}</span></td><td><div class="cell-note">${esc(row.nextProof)}</div></td></tr>`;
          })
          .join("")
      : `<tr><td colspan="7">No rows for this horizon / side. Missing evidence is not converted into a result.</td></tr>`;
    return `<div class="panel"><div class="panel-head"><h3>M-Factor rank table</h3><span class="tag">LIVE BFF ${esc(batch.runId || "")}</span></div><div class="table-wrap"><table class="tool-table"><thead><tr>${head
      .map((column) => `<th>${esc(column)}</th>`)
      .join("")}</tr></thead><tbody>${body}</tbody></table></div><p class="cell-note">Sort: rank_strength desc, completeness desc, freshness desc, symbol asc. Strong class cannot override a WAIT gate.</p></div>`;
  }

  function layerStatus(row, layer) {
    if (!row) return "waiting";
    const gates = row.gateCodes || [];
    switch (layer) {
      case "Structure":
        return row.readinessTag === "SETUP_READY" ? "ok" : row.readinessTag === "INVALIDATED" ? "fail" : "partial";
      case "Volume":
        return row.rankStrength > 0 ? "ok" : "waiting";
      case "Breakout":
        return "waiting";
      case "Market":
        return gates.some((code) => String(code).includes("INDEX")) ? "partial" : "waiting";
      case "MTF":
        return "waiting";
      case "Safety":
        return gates.some((code) => String(code).startsWith("REJECT")) ? "fail" : "waiting";
      default:
        return "waiting";
    }
  }

  function familiesHtml(row, isSelected) {
    const families = (row && row.families) || [];
    if (!isSelected || !families.length) return "";
    const rows = families
      .filter((family) => family.weight > 0)
      .map(
        (family) =>
          `<div class="signal-bar"><span>${esc(family.family)} w${esc(family.weight)}</span><div class="signal-track"><div class="signal-fill${family.supportStrength >= family.oppositionStrength ? "" : " opposing"}" style="width:${Math.round(Math.min(1, family.supportStrength) * 100)}%"></div></div><strong>S ${Math.round(family.supportStrength * 100)} / O ${Math.round(family.oppositionStrength * 100)}</strong></div>`
      )
      .join("");
    return `<div class="signal-viz" style="--tool-accent:${ACCENT}"><h3>Selected row FUS-009 families (S_f / O_f, 0-100)</h3>${rows}<div class="tool-note">Missing families stay 0; weights are never renormalized. R3 cheap diagnostic: ${esc(row.r3EvidenceStrength == null ? "n/a" : row.r3EvidenceStrength)}.</div></div>`;
  }

  function cardHtml(row) {
    const side = (function boardOf(item) {
      if ((state.batch.buyRows || []).some((entry) => entry.symbol === item.symbol)) return "buy";
      if ((state.batch.sellRows || []).some((entry) => entry.symbol === item.symbol)) return "sell";
      return "";
    })(row);
    const direction = side === "buy" ? "BUY" : side === "sell" ? "SELL" : "UNRESOLVED";
    const checks = [["Structure", "Structure"], ["Volume", "Volume"], ["Breakout", "Breakout"], ["Market", "Market"], ["MTF", "MTF"], ["Safety", "Safety"]]
      .map((pair) => {
        const status = layerStatus(row, pair[1]);
        return `<span class="candidate-check${status === "partial" ? " partial" : ""}">${esc(pair[0])} ${status.toUpperCase()}</span>`;
      })
      .join("");
    const tags = [row.directionalClass, row.readinessTag, (row.whyWait || [])[0] || "NO_BLOCKER_NAMED"].filter(Boolean);
    const selected = selectedRow();
    return `<article class="candidate-card ${side || "wait"}" data-mf-card="${esc(row.symbol)}">
      <div class="candidate-head"><div><h3 class="candidate-symbol">${esc(row.symbol)}</h3><p class="candidate-sub">${esc(row.horizon)} | state <strong>${esc(row.publicState)}</strong></p></div><span class="direction-chip">${direction}</span></div>
      <div class="candidate-tags">${tags.map((tag, index) => `<span class="candidate-tag${index === 0 ? " primary" : ""}">${esc(tag)}</span>`).join("")}</div>
      <div class="candidate-bars">
        <div class="candidate-bar"><span>Long hypothesis</span><div class="candidate-track"><div class="candidate-fill" style="width:${Math.min(100, row.longStrength)}%"></div></div><strong>${esc(row.longStrength)}</strong></div>
        <div class="candidate-bar"><span>Short hypothesis</span><div class="candidate-track"><div class="candidate-fill opposing" style="width:${Math.min(100, row.shortStrength)}%"></div></div><strong>${esc(row.shortStrength)}</strong></div>
        <div class="candidate-bar"><span>Completeness</span><div class="candidate-track"><div class="candidate-fill blue" style="width:${Math.round((row.completeness || 0) * 100)}%"></div></div><strong>${Math.round((row.completeness || 0) * 100)}</strong></div>
      </div>
      ${familiesHtml(row, Boolean(selected && selected.symbol === row.symbol))}
      <div class="candidate-levels">
        <div class="candidate-level"><span>Entry</span><strong>PENDING</strong></div>
        <div class="candidate-level"><span>Target</span><strong>UNKNOWN</strong></div>
        <div class="candidate-level"><span>Stop</span><strong>PENDING</strong></div>
        <div class="candidate-level"><span>R:R</span><strong>UNKNOWN</strong></div>
      </div>
      <div class="candidate-why"><strong>HOW:</strong> ${esc(row.how)}<br><strong>WHAT:</strong> ${esc(row.what)}<br><strong>WHERE:</strong> ${esc(row.where)}<br><strong>WHEN:</strong> ${esc(row.when)}<br><strong>Next proof:</strong> ${esc(row.nextProof)}</div>
      <div class="candidate-checks">${checks}</div>
      <div class="candidate-foot"><span>Why wait: ${esc((row.whyWait || []).join("; ") || "none named")}</span><span>Research direction only - not an order</span></div>
    </article>`;
  }

  function cardsHtml() {
    const rows = allRows().slice(0, 6);
    if (!rows.length) {
      return `<div class="toolbar"><strong>Stock decision panels</strong><span class="tag">NO LEGAL ROWS</span></div><div class="callout warn">No stock decision panels for this horizon. Geometry stays PENDING; nothing is minted from missing data.</div>`;
    }
    return `<div class="toolbar"><strong>Stock decision panels</strong><span class="tag">LIVE BFF</span></div><div class="candidate-grid">${rows.map(cardHtml).join("")}</div>`;
  }

  function renderSignals(batch) {
    const row = selectedRow();
    return (
      marketStrip(batch) +
      (batch.horizonWaitCode
        ? `<div class="callout bad"><strong>${esc(batch.horizonWaitCode)}</strong><br>This horizon is not activated. Boards stay empty rather than dressing EOD data as intraday or commodity evidence.</div>`
        : "") +
      `<div class="candidate-stage">${barsHtml(row)}${cardsHtml()}</div>` +
      rankTable(batch) +
      (batch.warnings || []).map((warning) => `<div class="callout">${esc(warning)}</div>`).join("")
    );
  }

  function renderValidation(batch) {
    const row = selectedRow();
    const layers = [
      ["1. Chart structure", "Closed-bar shape from R5 structure. Direction owner.", "Structure"],
      ["2. Volume / participation", "One cash activity root; delivery is EOD swing context only.", "Volume"],
      ["3. Breakout strength", "Closed-bar breakout/breakdown rule. Not wired for live rows yet.", "Breakout"],
      ["4. Market context", "Sector/index agreement; INDEX_CONFLICT forces WAIT when required.", "Market"],
      ["5. Multi-timeframe", "Horizon conflict -> WAIT. Single-horizon snapshot only.", "MTF"],
      ["6. Safety / gates", "Activation, surveillance, freshness, CA. Hard veto wins.", "Safety"]
    ];
    const status = (value) => (value === "ok" ? "PASS" : value === "partial" ? "PARTIAL" : value === "fail" ? "FAIL" : "WAIT");
    return `<div class="validation-panel">
      <div class="validation-banner"><strong>Validation stack</strong> - filled from live gate codes for ${esc(row ? row.symbol : "no row")}. Fail-closed: any hard fail -> WAIT/REJECT.</div>
      <div class="pattern-grid">${layers
        .map((layer) => `<article class="pattern-card"><h4>${esc(layer[0])}</h4><div class="pattern-card-body"><p>${esc(layer[1])}</p><span class="pattern-check ${layerStatus(row, layer[2])}">${esc(layer[2])} - ${status(layerStatus(row, layer[2]))}</span></div></article>`)
        .join("")}</div>
      <div class="verify-strip">
        <div><span>Inputs</span><strong>hash-matched R1/R2/R3 lineage (${esc(batch.r3RunHash ? batch.r3RunHash.slice(0, 12) : "")}...)</strong></div>
        <div><span>Calculation</span><strong>${esc(batch.longFormula || "")}; ${esc(batch.shortFormula || "")}</strong></div>
        <div><span>Output ceiling</span><strong>${esc(batch.stateCeiling || "WAIT")}</strong></div>
        <div><span>Failure behavior</span><strong>503 WAIT_* codes; never fixture numbers</strong></div>
      </div>
      <div class="evidence-disclaimer">Gate codes for this row: ${esc(row && (row.gateCodes || []).join(", ") || "none recorded")}.</div>
    </div>`;
  }

  function renderTrack(batch) {
    const track = batch.track || {};
    return `<div class="track-layout">
      <div class="track-canvas"><h3>M-Factor outcome series</h3><div class="track-empty"><div><strong>${esc(track.state || "PIT_NOT_VALIDATED")}</strong>Journal-backed outcomes appear only after immutable decisions, realistic costs and closed-bar replay pass (R16).</div></div></div>
      <div class="track-checks">
        <div class="track-check"><strong>Verified journal rows: ${esc(track.sampleCount == null ? 0 : track.sampleCount)}</strong><span>Live BFF claims no observed performance.</span></div>
        <div class="track-check"><strong>Win rate: ${track.winRate == null ? "unavailable" : esc(track.winRate)}</strong><span>Unlock only after out-of-sample validation and minimum sample rules.</span></div>
        <div class="track-check"><strong>Benchmark delta: ${track.benchmarkDelta == null ? "unavailable" : esc(track.benchmarkDelta)}</strong><span>Compare against a simple source/volume baseline before promotion.</span></div>
        <div class="track-check"><strong>Leakage guard: required</strong><span>available_at, delisted symbols, revisions, fees and slippage.</span></div>
      </div>
    </div>`;
  }

  function renderEngines() {
    const engines = [
      ["Canonical resolver", "Selected and suppressed claims", "FUS-009", "ONLY RANK OWNER"],
      ["Structure", "Closed-bar direction (R5)", "STRUCTURE", "DIRECTION OWNER"],
      ["Participation", "One activity root + EOD delivery", "PARTICIPATION", "ATTENTION"],
      ["Context", "Sector / index agreement", "MARKET_AND_SECTOR", "WEAKEN / WAIT"],
      ["Safety gate", "Activation, surveillance, freshness, CA", "TRADABILITY", "HARD VETO / STATE CEILING"],
      ["PK shadow", "Pipe tags (FUS-010: zero votes)", "EXPERIMENTAL", "NO VOTE"],
      ["Options / OI", "At most one package", "OPTIONS_CONTEXT", "SUPPORT / OBSTACLE / UNKNOWN"],
      ["Hybrid overlay p-hat", "Paper overlay only", "-", "NOT AN M-FACTOR INPUT"]
    ];
    return `<div class="panel"><div class="panel-head"><h3>Engine ownership and limits</h3><span class="tag info">NO ENGINE VOTES TWICE</span></div>
      <div class="table-wrap"><table class="engine-table"><thead><tr><th>Engine</th><th>Role</th><th>Evidence family</th><th>Authority</th></tr></thead>
      <tbody>${engines.map((engine) => `<tr><td>${esc(engine[0])}</td><td>${esc(engine[1])}</td><td>${esc(engine[2])}</td><td><span class="tag">${esc(engine[3])}</span></td></tr>`).join("")}</tbody></table></div></div>
      <div class="evidence-disclaimer">The FUS-009 resolver is the only rank owner. PK pipes and options context cannot vote twice; Hybrid V2 overlay never enters this rank.</div>`;
  }

  function renderTabs() {
    document.querySelectorAll(".tool-tab").forEach((button) => {
      button.classList.toggle("active", button.dataset.evidence === state.tab);
    });
  }

  function renderWaiting(title, detail) {
    return `<div class="tool-wait"><strong>${esc(title)}</strong><p>${esc(detail)}</p>
      <p class="cell-note">This tool never falls back to static fixture demo cards; the live wiring replaces them.</p></div>`;
  }

  function bindControls() {
    document.querySelectorAll("[data-mf-horizon]").forEach((button) => {
      button.onclick = () => {
        if (state.horizon === button.dataset.mfHorizon) return;
        state.horizon = button.dataset.mfHorizon;
        void load();
      };
    });
    document.querySelectorAll("[data-mf-side]").forEach((button) => {
      button.onclick = () => {
        if (state.side === button.dataset.mfSide) return;
        state.side = button.dataset.mfSide;
        void load();
      };
    });
    const reload = byId("mfReload");
    if (reload) reload.onclick = () => void load();
    document.querySelectorAll("[data-mf-row], [data-mf-card]").forEach((node) => {
      node.onclick = () => {
        state.selectedSymbol = node.dataset.mfRow || node.dataset.mfCard;
        render();
      };
    });
  }

  function render() {
    renderHero(state.batch);
    renderTabs();
    const content = byId("toolContent");
    if (!content) return;
    let html;
    if (state.loading) {
      html = horizonSwitcher(true) + renderWaiting("WAIT_BFF_LOADING", "Fetching the live M-Factor batch from /api/v1/tools/m_factor...");
    } else if (state.error) {
      html = horizonSwitcher(true) + renderWaiting(state.error.code, state.error.message);
    } else if (state.batch) {
      const batch = state.batch;
      const body = state.tab === "validation"
        ? renderValidation(batch)
        : state.tab === "track"
          ? renderTrack(batch)
          : state.tab === "engines"
            ? renderEngines()
            : renderSignals(batch);
      html = (state.tab === "signals" ? horizonSwitcher(false) : "") + body;
    } else {
      html = renderWaiting("WAIT_BFF_NO_BATCH", "No batch and no error recorded.");
    }
    content.innerHTML = html;
    content.setAttribute("data-mf-live", "1");
    bindControls();
    ensureOwnershipWatcher();
  }

  /* A stale cached product-fixture.js can still repaint #toolContent with
     fixture cards after we painted live data. Mark our output and reclaim
     the panel whenever another painter overwrites it while m_factor is the
     active tool. */
  let ownershipWatcher = null;

  function toolIsActive() {
    const fixture = window.TrendForgeProductFixture;
    if (fixture && typeof fixture.activeTool === "function") {
      return fixture.activeTool() === "m_factor";
    }
    const navButton = document.querySelector('.nav button[data-view="tool"][data-tool="m_factor"]');
    if (navButton && navButton.classList.contains("active")) return true;
    const section = document.getElementById("tool");
    return Boolean(section && section.classList.contains("active"));
  }

  function ensureOwnershipWatcher() {
    if (ownershipWatcher) return;
    const content = byId("toolContent");
    if (!content || typeof MutationObserver === "undefined") return;
    ownershipWatcher = new MutationObserver(() => {
      if (!toolIsActive()) return;
      if (content.getAttribute("data-mf-live") === "1") return;
      setTimeout(() => {
        if (toolIsActive() && content.getAttribute("data-mf-live") !== "1") render();
      }, 0);
    });
    ownershipWatcher.observe(content, { childList: true });
  }

  document.querySelectorAll(".tool-tab").forEach((button) => {
    if (!TABS.includes(button.dataset.evidence)) return;
    const original = button.onclick;
    button.onclick = function intercepted(event) {
      if (window.TrendForgeMFactorLive && window.TrendForgeMFactorLive.ownsActiveTool()) {
        state.tab = button.dataset.evidence;
        render();
        return;
      }
      if (typeof original === "function") original.call(this, event);
    };
  });

  window.TrendForgeMFactorLive = {
    contract: CONTRACT,
    ownsActiveTool() {
      const fixture = window.TrendForgeProductFixture;
      return Boolean(fixture && typeof fixture.activeTool === "function" && fixture.activeTool() === "m_factor");
    },
    render,
    reload: load
  };

  void load();
})();
