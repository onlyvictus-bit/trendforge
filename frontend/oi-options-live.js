/* OI/Options live view owner (oi_analysis, oi_tracker, strike_explorer,
   expiry_prediction). Contract:
   docs/fable/remaining_build/OI_OPTIONS_ROOMS_GLM_PROMPT.md.
   Consumes the four GET /api/v1/tools/{tool} BFFs. On 200 it paints the
   live Signals / How validated / Track record / Engines used tabs. On 503
   or network failure it paints the typed WAIT code. It never falls back
   to static fixture cards for these tools, and fixture delegates to this
   module when one of them is active. */
(() => {
  "use strict";

  const CONTRACT = "trendforge.oi-options-live.v1";
  const ACCENT = "#b26a12";
  const TOOLS = {
    oi_analysis: {
      endpoint: "/api/v1/tools/oi_analysis",
      query: () => `symbol=&limit=40`,
      title: "OI Analysis",
      eyebrow: "NEUTRAL OPEN INTEREST - LIVE",
      purpose:
        "Futures price/OI co-movement on the aligned expiry. Observation codes only; never institutional intent."
    },
    oi_tracker: {
      endpoint: "/api/v1/tools/oi_tracker",
      query: () => `underlying=&limit=40`,
      title: "OI Tracker",
      eyebrow: "OI AND PCR PATH - LIVE",
      purpose: "Whether OI (and PCR when a chain exists) persists across observations. Roll-aware windows."
    },
    strike_explorer: {
      endpoint: "/api/v1/tools/strike_explorer",
      query: () => {
        const underlying = state.underlying || state.lastUnderlying || "";
        const expiry = state.expiry || state.lastExpiry || "";
        return `underlying=${encodeURIComponent(underlying)}&expiry=${encodeURIComponent(expiry)}`;
      },
      title: "Strike Explorer",
      eyebrow: "OPTIONS SURFACE - LIVE",
      purpose: "Strike ladder only after the same-expiry chain passes quality checks. Walls are candidates, not orders."
    },
    expiry_prediction: {
      endpoint: "/api/v1/tools/expiry_prediction",
      query: () => {
        const underlying = state.underlying || state.lastUnderlying || "";
        const expiry = state.expiry || state.lastExpiry || "";
        return `underlying=${encodeURIComponent(underlying)}&expiry=${encodeURIComponent(expiry)}`;
      },
      title: "Expiry Range Context",
      eyebrow: "ESTIMATE - NOT FORECAST",
      purpose: "Same-expiry range estimate, max-pain reference and hero-zero research JSON. Max pain is not a destination."
    }
  };
  const TABS = ["signals", "validation", "track", "engines"];

  const state = {
    tool: null,
    underlying: "",
    expiry: "",
    lastUnderlying: "",
    lastExpiry: "",
    batch: null,
    error: null,
    loading: false,
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

  function isActive() {
    const names = Object.keys(TOOLS);
    const fixture = window.TrendForgeProductFixture;
    if (fixture && typeof fixture.activeTool === "function") {
      const t = fixture.activeTool();
      return names.includes(t) ? t : null;
    }
    for (const name of names) {
      const button = document.querySelector(`.nav button[data-view="tool"][data-tool="${name}"]`);
      if (button && button.classList.contains("active")) return name;
    }
    return null;
  }

  async function load(tool) {
    const generation = ++state.requestGeneration;
    state.tool = tool;
    state.loading = true;
    state.error = null;
    render();
    const spec = TOOLS[tool];
    if (
      (tool === "strike_explorer" || tool === "expiry_prediction") &&
      !(state.underlying || state.lastUnderlying) &&
      !(state.expiry || state.lastExpiry)
    ) {
      state.loading = false;
      state.batch = null;
      state.error = {
        code: "WAIT_UNDERLYING",
        message: "Open OI Analysis and click a symbol, or type underlying and expiry here."
      };
      render();
      return;
    }
    let response;
    try {
      response = await fetch(`${spec.endpoint}?${spec.query()}`, {
        cache: "no-store",
        headers: { Accept: "application/json" }
      });
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
      let message = "The OI/options BFF failed closed.";
      try {
        const payload = await response.json();
        code = (payload && payload.detail && payload.detail.code) || code;
        message = (payload && payload.detail && payload.detail.message) || message;
      } catch (_parseError) {
        /* status code alone is enough */
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
      state.error = {
        code: `WAIT_BFF_HTTP_${response.status}`,
        message:
          response.status === 404
            ? "This API process does not serve the OI rooms. Restart TrendForge on :8000 so GET /api/v1/tools/oi_analysis exists."
            : "Unexpected BFF status."
      };
      render();
      return;
    }
    try {
      const batch = await response.json();
      if (generation !== state.requestGeneration) return;
      state.loading = false;
      state.batch = batch;
      state.error = null;
      if (state.tool === "oi_analysis") {
        const firstRow = (batch.rows || [])[0];
        if (!state.selectedSymbol || !((batch.rows || []).some((r) => r.symbol === state.selectedSymbol))) {
          state.selectedSymbol = firstRow ? firstRow.symbol : null;
        }
      }
      const first = (batch.rows && batch.rows[0]) || null;
      if (first && first.symbol) {
        state.lastUnderlying = first.symbol;
        state.lastExpiry = first.expiry || state.lastExpiry;
      }
      if (batch.underlying) state.lastUnderlying = batch.underlying;
      if (batch.expiry) state.lastExpiry = batch.expiry;
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
    const spec = TOOLS[state.tool] || TOOLS.oi_analysis;
    if (byId("toolTitle")) byId("toolTitle").textContent = spec.title;
    if (byId("toolEyebrow")) byId("toolEyebrow").textContent = state.error ? state.error.code : spec.eyebrow;
    if (byId("toolPurpose")) byId("toolPurpose").textContent = spec.purpose;
    const chip = byId("toolState");
    if (chip) {
      chip.textContent = state.error ? state.error.code : batch ? batch.stateCeiling || "WAIT" : "WAIT_BFF_LOADING";
      chip.className = "chip wait";
    }
    const asOfChip = byId("toolAsOfChip");
    if (asOfChip) asOfChip.textContent = batch && batch.dataDate ? `DATA ${batch.dataDate}` : "AS-OF —";
    const runChip = byId("toolRunChip");
    if (runChip) runChip.textContent = "RUN — LIVE BFF";
  }

  function table(head, bodyRows, emptyText) {
    const body = bodyRows.length
      ? bodyRows.join("")
      : `<tr><td colspan="${head.length}">${esc(emptyText)}</td></tr>`;
    return `<div class="panel"><div class="panel-head"><h3>Live output</h3><span class="tag">LIVE BFF</span></div><div class="table-wrap"><table class="tool-table"><thead><tr>${head
      .map((c) => `<th>${esc(c)}</th>`)
      .join("")}</tr></thead><tbody>${body}</tbody></table></div></div>`;
  }

  function tag(text) {
    return `<span class="tag wait">${esc(text)}</span>`;
  }

  function symbolRail(batch) {
    const rows = batch.rows || [];
    const selected = state.underlying || state.lastUnderlying;
    const items = rows
      .map((r) => {
        const symbol = r.symbol || r.underlying || "";
        const expiry = r.expiry || r.lastDataDate || "";
        const active = symbol === selected ? " active" : "";
        return `<button type="button" class="oi-rail-item${active}" data-oi-symbol="${esc(symbol)}" data-oi-expiry="${esc(expiry)}">
          <span><strong>${esc(symbol)}</strong><small>${esc(r.observationCode || r.oiPathLabel || "")}</small></span>
          ${tag(r.publicState)}
        </button>`;
      })
      .join("");
    return `<aside class="panel oi-rail"><div class="panel-head"><h3>Live underlyings</h3><span class="tag">${rows.length}</span></div><div class="oi-rail-list">${
      items || "<p class='cell-note'>No FUTURES_OK rows.</p>"
    }</div></aside>`;
  }

  function signalsHtml(batch) {
    if (state.tool === "oi_analysis") {
      const rowsAll = batch.rows || [];
      const selected =
        rowsAll.find((r) => r.symbol === state.selectedSymbol) || rowsAll[0] || null;
      const rows = rowsAll.map(
        (r) =>
          `<tr class="${selected && r.symbol === selected.symbol ? "selected" : ""}" data-oi-row="${esc(r.symbol)}"><td><strong>${esc(r.symbol)}</strong></td><td>${esc(r.expiry)}</td><td>${esc(r.priceChangePct == null ? "UNKNOWN" : r.priceChangePct + "%")}</td><td>${esc(r.oiChangePct == null ? "UNKNOWN" : r.oiChangePct + "%")}</td><td><strong>${esc(r.observationCode)}</strong></td><td class="cell-note">${esc(r.traderRead || r.interpretation || "")}</td><td>${tag(r.mwpl.officialState)}</td><td>${tag(r.publicState)}</td></tr>`
      );
      const columns = (batch.columnsSpec || [])
        .map((c) => `${esc(c.column)} — ${esc(c.meaning)}. Trap: ${esc(c.trap)}.`)
        .join(" | ");
      let guide = "";
      if (selected) {
        guide =
          `<div class="panel"><div class="panel-head"><h3>What this row means — ${esc(selected.symbol)}</h3><span class="tag">INTERPRETATION, NOT FACT</span></div>` +
          `<div class="body">` +
          `<p><strong>Read:</strong> ${esc(selected.traderRead || selected.interpretation || "—")}</p>` +
          `<p><strong>If your structure is LONG:</strong> ${esc(selected.ifLongBias || "—")}</p>` +
          `<p><strong>If your structure is SHORT:</strong> ${esc(selected.ifShortBias || "—")}</p>` +
          (selected.activityNote ? `<p><strong>Activity:</strong> ${esc(selected.activityNote)}</p>` : "") +
          `<p><strong>Next step:</strong> ${esc(selected.nextStep || "—")}</p>` +
          `<div class="evidence-disclaimer">OI is participation context. Your closed-bar structure owns direction; this room can only agree, fight or stay silent. Never an order.</div>` +
          `</div></div>`;
      }
      return (
        `<div class="tool-layout">` +
        symbolRail(batch) +
        `<div>` +
        guide +
        `<div class="callout">${columns}</div>` +
        table(
          ["Symbol", "Expiry", "Price Δ%", "OI Δ%", "Bucket", "Read (interpretation)", "MWPL", "State"],
          rows,
          "No FUTURES_OK rows in the hash-proven FO lineage."
        ) +
        `</div></div>`
      );
    }
    if (state.tool === "oi_tracker") {
      const rows = (batch.rows || []).map(
        (r) =>
          `<tr><td><strong>${esc(r.underlying)}</strong></td><td>${esc(r.observations)}</td><td>${esc(r.firstDataDate || "-")}</td><td>${esc(r.lastDataDate || "-")}</td><td>${esc(r.oiPathLabel)}</td><td>${esc(r.pcrOpen == null ? "UNKNOWN" : r.pcrOpen)}</td><td>${esc(r.pcrCurrent == null ? "UNKNOWN" : r.pcrCurrent)}</td><td>${tag(r.publicState)}</td></tr>`
      );
      return (
        `<div class="tool-layout">` +
        symbolRail(batch) +
        `<div>` +
        table(
          ["Underlying", "Observations", "First", "Last", "OI path", "PCR open", "PCR current", "State"],
          rows,
          "Fewer than two comparable observations; nothing is invented."
        ) +
        `</div></div>`
      );
    }
    if (state.tool === "strike_explorer") {
      const q = batch.qualityState === "CHAIN_OK" ? "OK" : batch.qualityState;
      const rows = (batch.ladder || []).map((s) => {
        const key = `${s.strike}`;
        const gamma = s.cashGammaProxy;
        return `<tr data-oi-strike="${esc(key)}"><td><strong>${esc(s.strike)}</strong></td><td>${esc(s.right)}</td><td>${esc(s.openInterest)}</td><td>${esc(s.volume)}</td><td>${esc(s.bid == null ? "-" : s.bid)}</td><td>${esc(s.ask == null ? "-" : s.ask)}</td><td>${esc(s.spreadPct == null ? "UNKNOWN" : s.spreadPct + "%")}</td><td>${esc(s.impliedVolatility == null ? "UNKNOWN" : s.impliedVolatility)}</td><td>${esc(gamma == null ? "UNKNOWN" : gamma)}</td></tr>`;
      });
      return (
        `<div class="callout"><strong>Quality ${esc(q)}</strong> completeness ${esc(batch.completeness)} · max spread ${batch.maxSpreadPct == null ? "UNKNOWN" : esc(batch.maxSpreadPct) + "%"}<br>Call wall ${esc(batch.callWall.strike ?? "UNKNOWN")} (${esc(batch.callWall.persistenceSnapshots)} snap) · Put wall ${esc(batch.putWall.strike ?? "UNKNOWN")} · Max pain REF ${esc(batch.maxPainReference ?? "UNKNOWN")}. Gamma label: ${esc(batch.gammaLabel)}.</div>` +
        (batch.blockers || []).map((b) => `<div class="callout bad">${esc(b)}</div>`).join("") +
        table(["Strike", "Right", "OI", "Volume", "Bid", "Ask", "Spread%", "IV%", "CashGamma proxy"], rows, "Chain missing or failed quality.")
      );
    }
    const hz = batch.heroZero;
    const hzHtml = hz
      ? `<pre class="cell-note" style="white-space:pre-wrap">${esc(JSON.stringify(hz, null, 2))}</pre>`
      : `<div class="callout warn">hero-zero card unavailable for this snapshot.</div>`;
    const rows = [
      `<tr><td>DTE</td><td>${esc(batch.dteCalendarDays)}</td></tr>`,
      `<tr><td>Tuesday weekly cycle</td><td>${esc(String(batch.isTuesdayExpiry))}</td></tr>`,
      `<tr><td>Mega-expiry</td><td>${esc(batch.megaStressTag)}</td></tr>`,
      `<tr><td>Physical block from</td><td>${esc(batch.physicalBlockActiveFrom || "n/a (index or non-mega)")}</td></tr>`,
      `<tr><td>Range estimate</td><td>${esc(batch.rangeLow ?? "UNKNOWN")} – ${esc(batch.rangeHigh ?? "UNKNOWN")} (${esc(batch.rangeMethod)})</td></tr>`,
      `<tr><td>Max pain reference</td><td>${esc(batch.maxPainReference ?? "UNKNOWN")}</td></tr>`,
      `<tr><td>Agreement</td><td>${esc(batch.agreementFraction ?? "UNKNOWN")}</td></tr>`,
      `<tr><td>Margin slot</td><td>${esc(batch.marginSlot)}</td></tr>`
    ].join("");
    return (
      (batch.blockers || []).map((b) => `<div class="callout bad">${esc(b)}</div>`).join("") +
      `<div class="panel"><div class="panel-head"><h3>Expiry context</h3><span class="tag">ESTIMATE ONLY</span></div><div class="table-wrap"><table class="tool-table"><tbody>${rows}</tbody></table></div></div>` +
      hzHtml
    );
  }

  function renderValidation(batch) {
    const layers = [
      ["Identity & alignment", "Same underlying, expiry, instrument for price and OI; mismatch is UNKNOWN, never a direction."],
      ["Official MWPL / ban", "BAN (>95% EOD, next day), RESUME (≤80%), ALERT60. Internal colour bands are conventions only."],
      ["Surveillance & safety", "ASM/GSM stage beside ban; safety outranks any derivative observation."],
      ["Chain quality", "Crossed books, spread % and completeness gate Strike/Expiry behind WAIT_CHAIN."],
      ["Roll window", "Weekly→monthly migration suppresses fake ΔOI instead of dressing it as participation."],
      ["Q vs P honesty", "prob_touch_Q is model-implied; prob_touch_P stays null until Brier-gated calibration."]
    ];
    return `<div class="validation-panel">
      <div class="validation-banner"><strong>Validation stack</strong> — deterministic gates; fail-closed to WAIT/REJECT.</div>
      <div class="pattern-grid">${layers
        .map((l) => `<article class="pattern-card"><h4>${esc(l[0])}</h4><div class="pattern-card-body"><p>${esc(l[1])}</p></div></article>`)
        .join("")}</div>
      <div class="verify-strip">
        <div><span>Inputs</span><strong>hash-matched FO lineage ${esc((batch.artifactHash || "").slice(0, 12))}${batch.artifactHash ? "…" : ""}</strong></div>
        <div><span>Data date</span><strong>${esc(batch.dataDate || "—")}</strong></div>
        <div><span>Output ceiling</span><strong>${esc(batch.stateCeiling || "WAIT")}</strong></div>
        <div><span>Failure behavior</span><strong>503 WAIT_* codes; never fixture numbers</strong></div>
      </div>
    </div>`;
  }

  function renderTrack(batch) {
    const track = batch.track || {};
    return `<div class="track-layout">
      <div class="track-canvas"><h3>Outcome series</h3><div class="track-empty"><div><strong>${esc(track.state || "PIT_NOT_VALIDATED")}</strong>Journal-backed outcomes appear only after immutable decisions, realistic costs and closed-bar replay pass (R16).</div></div></div>
      <div class="track-checks">
        <div class="track-check"><strong>Verified journal rows: ${esc(track.sampleCount == null ? 0 : track.sampleCount)}</strong><span>No observed performance is claimed.</span></div>
        <div class="track-check"><strong>Win rate: ${track.winRate == null ? "unavailable" : esc(track.winRate)}</strong><span>Unlock only after out-of-sample validation.</span></div>
        <div class="track-check"><strong>Unlock owner</strong><strong>${esc(track.unlockOwner || "R16")}</strong><span>Point-in-time walk-forward required.</span></div>
        <div class="track-check"><strong>Leakage guard: required</strong><span>available_at, revisions, costs and slippage.</span></div>
      </div>
    </div>`;
  }

  function renderEngines() {
    const engines = [
      ["FO UDiFF normalizer", "Contract futures OI/volume", "OPT_FLOW", "FACT"],
      ["Quadrant engine", "PRICE_*_OI_* observation codes", "OPTIONS_PACKAGE", "OBSERVATION ONLY"],
      ["Official MWPL/ban gate", "BAN / RESUME / ALERT60 + surveillance", "TRADABILITY", "HARD VETO"],
      ["Chain quality gate", "Spread, crossed book, completeness", "HARD_VETO", "STATE CEILING WAIT_CHAIN"],
      ["Pricing / IV", "Black-76 + solver; Q≠P", "OPTIONS_PACKAGE", "DERIVED"],
      ["Walls / max pain", "Concentration candidates and payout reference", "OPTIONS_PACKAGE", "REFERENCE"],
      ["Guidance JSON", "Frozen schema; LLM renders verbatim", "EXPLAIN", "CONTEXT_ONLY"]
    ];
    return `<div class="panel"><div class="panel-head"><h3>Engine ownership and limits</h3><span class="tag info">NO ENGINE VOTES TWICE</span></div>
      <div class="table-wrap"><table class="engine-table"><thead><tr><th>Engine</th><th>Role</th><th>Evidence family</th><th>Authority</th></tr></thead>
      <tbody>${engines.map((e) => `<tr><td>${esc(e[0])}</td><td>${esc(e[1])}</td><td>${esc(e[2])}</td><td><span class="tag">${esc(e[3])}</span></td></tr>`).join("")}</tbody></table></div></div>
      <div class="evidence-disclaimer">Structure (R5) owns direction. OI and options context can SUPPORT, WEAKEN, CONFLICT or stay UNKNOWN — they never confirm, never price an order, and M-Factor remains a separate FUS-009 room.</div>`;
  }

  function renderWaiting(title, detail) {
    return `<div class="tool-wait"><strong>${esc(title)}</strong><p>${esc(detail)}</p>
      <p class="cell-note">This room never falls back to static fixture cards; the live wiring replaces them.</p></div>`;
  }

  function underlyingsInput(disabled) {
    if (!["strike_explorer", "expiry_prediction"].includes(state.tool)) return "";
    return `<div class="toolbar"><strong>Underlying / Expiry</strong>
      <input id="oiUnderlying" placeholder="NIFTY" value="${esc(state.underlying || state.lastUnderlying)}"${disabled ? " disabled" : ""}>
      <input id="oiExpiry" placeholder="2026-08-25" value="${esc(state.expiry || state.lastExpiry)}"${disabled ? " disabled" : ""}>
      <button class="btn" id="oiGo"${disabled ? " disabled" : ""}>Load</button></div>`;
  }

  function bindControls() {
    const go = byId("oiGo");
    if (go) {
      go.onclick = () => {
        const u = byId("oiUnderlying");
        const e = byId("oiExpiry");
        state.underlying = u ? u.value.trim().toUpperCase() : "";
        state.expiry = e ? e.value.trim() : "";
        void load(state.tool);
      };
    }
    document.querySelectorAll("[data-oi-row]").forEach((node) => {
      node.onclick = () => {
        state.selectedSymbol = node.dataset.oiRow;
        render();
      };
    });
    document.querySelectorAll("[data-oi-symbol]").forEach((button) => {
      button.onclick = () => {
        state.underlying = (button.dataset.oiSymbol || "").toUpperCase();
        state.expiry = button.dataset.oiExpiry || "";
        state.lastUnderlying = state.underlying;
        state.lastExpiry = state.expiry;
        document.querySelectorAll("[data-oi-symbol]").forEach((node) => {
          node.classList.toggle("active", node === button);
        });
      };
    });
  }

  function renderTabs() {
    document.querySelectorAll(".tool-tab").forEach((button) => {
      button.classList.toggle("active", button.dataset.evidence === currentTab());
    });
  }

  let tab = "signals";
  function currentTab() {
    return tab;
  }

  function render() {
    renderHero(state.batch);
    renderTabs();
    const content = byId("toolContent");
    if (!content) return;
    let html;
    if (state.loading) {
      html = renderWaiting("WAIT_BFF_LOADING", `Fetching live ${state.tool || "OI"} batch...`);
    } else if (state.error) {
      html = renderWaiting(state.error.code, state.error.message);
    } else if (state.batch) {
      const b = state.batch;
      html =
        underlyingsInput(false) +
        (tab === "validation"
          ? renderValidation(b)
          : tab === "track"
            ? renderTrack(b)
            : tab === "engines"
              ? renderEngines()
              : signalsHtml(b));
    } else {
      html = renderWaiting("WAIT_BFF_NO_BATCH", "No batch and no error recorded.");
    }
    content.innerHTML = html;
    content.setAttribute("data-oi-live", "1");
    bindControls();
    ensureOwnershipWatcher();
  }

  let ownershipWatcher = null;

  function ensureOwnershipWatcher() {
    if (ownershipWatcher) return;
    const content = byId("toolContent");
    if (!content || typeof MutationObserver === "undefined") return;
    ownershipWatcher = new MutationObserver(() => {
      if (!isActive()) return;
      if (content.getAttribute("data-oi-live") === "1") return;
      setTimeout(() => {
        if (isActive() && content.getAttribute("data-oi-live") !== "1") render();
      }, 0);
    });
    ownershipWatcher.observe(content, { childList: true });
  }

  document.querySelectorAll(".tool-tab").forEach((button) => {
    if (!TABS.includes(button.dataset.evidence)) return;
    const original = button.onclick;
    button.onclick = function intercepted(event) {
      if (window.TrendForgeOiOptionsLive && window.TrendForgeOiOptionsLive.ownsActiveTool()) {
        tab = button.dataset.evidence;
        render();
        return;
      }
      if (typeof original === "function") original.call(this, event);
    };
  });

  window.TrendForgeOiOptionsLive = {
    contract: CONTRACT,
    ownsActiveTool() {
      return Boolean(isActive());
    },
    activeTool() {
      return isActive();
    },
    render,
    reload: () => {
      const tool = isActive() || state.tool || "oi_analysis";
      void load(tool);
    }
  };

  document.querySelectorAll('.nav button[data-view="tool"]').forEach((button) => {
    const name = button.dataset.tool;
    if (!TOOLS[name]) return;
    const original = button.onclick;
    button.onclick = function intercepted(event) {
      if (typeof original === "function") original.call(this, event);
      void load(name);
    };
  });

  const bootTool = isActive();
  if (bootTool) void load(bootTool);
})();
