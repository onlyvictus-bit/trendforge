(() => {
  "use strict";

  const CONTRACT = "trendforge.scanner-lab.v1";
  const BUNDLE_ENDPOINT = "/api/v1/scanners/lab-bundle";
  const SUBTABS = ["Definitions", "Pipe flow", "Symbol", "PK shadow"];

  const state = {
    nativeCore: null,
    pipeDefs: null,
    bundle: null,
    tab: "Pipe flow",
    symbol: "",
  };

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function shortHash(hash) {
    return escapeHtml(String(hash || "").slice(0, 12));
  }

  // --------------------------------------------------- inspector tab wiring

  function ensureInspectorTab() {
    const tabs = $("q5InspectorTabs");
    const panel = $("scannerLabPanel");
    if (!tabs || !panel || tabs.querySelector("[data-scanner-lab]")) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "q5-inspector-tab";
    button.setAttribute("data-scanner-lab", "1");
    button.setAttribute("role", "tab");
    button.textContent = "Scanner Lab";
    button.addEventListener("click", () => openLab());
    tabs.appendChild(button);
  }

  function openLab() {
    const tabs = $("q5InspectorTabs");
    const panel = $("scannerLabPanel");
    const q5Panel = $("q5InspectorPanel");
    if (!tabs || !panel) return;
    panel.hidden = false;
    if (q5Panel) q5Panel.style.display = "none";
    tabs
      .querySelectorAll("[data-q5-section]")
      .forEach((b) => b.classList.remove("active"));
    tabs
      .querySelector("[data-scanner-lab]")
      ?.classList.add("active");
    void refresh();
  }

  function closeLab() {
    const tabs = $("q5InspectorTabs");
    const panel = $("scannerLabPanel");
    const q5Panel = $("q5InspectorPanel");
    if (!tabs || !panel) return;
    panel.hidden = true;
    if (q5Panel) q5Panel.style.display = "";
    tabs.querySelector("[data-scanner-lab]")?.classList.remove("active");
  }

  function watchInspectorTabs() {
    const tabs = $("q5InspectorTabs");
    if (!tabs) return;
    ensureInspectorTab();
    new MutationObserver(() => {
      ensureInspectorTab();
      const panel = $("scannerLabPanel");
      if (panel && panel.hidden === false) {
        // Lab open: survive q5 tab re-renders.
        const q5Panel = $("q5InspectorPanel");
        if (q5Panel) q5Panel.style.display = "none";
        tabs
          .querySelectorAll("[data-q5-section]")
          .forEach((b) => b.classList.remove("active"));
        tabs
          .querySelector("[data-scanner-lab]")
          ?.classList.add("active");
      }
    }).observe(tabs, { childList: true });
    tabs.querySelectorAll("[data-q5-section]").forEach((button) => {
      button.addEventListener("click", () => closeLab());
    });
  }

  // ----------------------------------------------------------------- views

  function renderSubtabs() {
    const tabs = $("scannerLabTabs");
    if (!tabs) return;
    tabs.innerHTML = SUBTABS.map(
      (name) =>
        '<button type="button" class="q5-inspector-tab ' +
        (state.tab === name ? "active" : "") +
        '" data-subtab="' +
        escapeHtml(name) +
        '">' +
        escapeHtml(name) +
        "</button>"
    ).join("");
    tabs.querySelectorAll("[data-subtab]").forEach((button) => {
      button.addEventListener("click", () => {
        state.tab = button.dataset.subtab;
        render();
      });
    });
  }

  function viewDefinitions() {
    const natives = state.nativeCore?.definitions || state.bundle?.nativeDefinitions || [];
    const pipes = state.pipeDefs?.definitions || [];
    const natRows = natives
      .map(
        (d) =>
          "<tr><td>" + escapeHtml(d.scannerId) + "</td><td>v" + escapeHtml(d.version) +
          "</td><td>" + shortHash(d.parameterHash) + "...</td><td>" + escapeHtml(d.family) +
          "</td><td>" + escapeHtml(d.group) + "</td></tr>"
      )
      .join("");
    const pipeRows = pipes
      .map(
        (d) =>
          "<tr><td>" + escapeHtml(d.pipeId) + "</td><td>v" + escapeHtml(d.version) +
          "</td><td>" + shortHash(d.parameterHash) + "...</td><td colspan=\"2\">emitsClaims " +
          String(d.emitsClaims) + "</td></tr>"
      )
      .join("");
    return (
      "<h4>Native cores (R8)</h4><table class=\"sl-table\"><tbody>" + natRows + "</tbody></table>" +
      "<h4>Pipe recipes (R10)</h4><table class=\"sl-table\"><tbody>" + pipeRows + "</tbody></table>"
    );
  }

  function stageChips(run) {
    return (run.stages || [])
      .map(
        (s) =>
          '<span class="pl-stage" title="' + escapeHtml((s.reasons || []).join(" | ")) + '">' +
          escapeHtml(s.op) + " " + Number(s.inCount ?? 0) + "&rarr;" + Number(s.outCount ?? 0) +
          (s.survivorsUnchanged ? " =" : "") + "</span>"
      )
      .join('<span class="pl-arrow">&rarr;</span>');
  }

  function viewPipeFlow() {
    const entries = state.bundle?.pipeRuns || [];
    if (!entries.length) return "<p>No seeded pipe runs available.</p>";
    return entries
      .map((entry) => {
        if (!entry.run) {
          return (
            '<div class="sl-run"><strong>' + escapeHtml(entry.pipeId) + "</strong> " +
            '<span class="nc-none">WAIT ' + escapeHtml(entry.code || "") + "</span></div>"
          );
        }
        const survivors = (entry.run.rows || [])
          .map((r) => '<span class="pl-sym">' + escapeHtml(r.symbol) + "</span>")
          .join(" ");
        return (
          '<div class="sl-run"><strong>' + escapeHtml(entry.pipeId) + "</strong>" +
          '<div class="pl-stages">' + stageChips(entry.run) + "</div>" +
          '<div class="pl-survivors">' + (survivors || '<span class="nc-none">no survivors</span>') + "</div></div>"
        );
      })
      .join("");
  }

  function nativeMatchesFor(symbol) {
    const row = (state.nativeCore?.rows || []).find((r) => r.symbol === symbol);
    if (!row) return null;
    return (row.matches || []).map((m) => ({
      id: m.scannerId,
      matched: m.matched === true,
      twin: m.correlatedPossible === true,
      label: m.guidanceLabel || "",
      relationship: m.candidateRelationship || "UNKNOWN",
      inputStatus: m.inputStatus || "INPUT_INCOMPLETE",
      scannerState: m.scannerState || "UNAVAILABLE",
      formulaVersion: m.formulaVersion || "",
      parameterHash: m.parameterHash || "",
      lineageHash: m.lineageHash || "",
      adjustmentVersion: m.adjustmentVersion || "",
      asOf: m.asOf || "",
      barCount: m.barCount || 0,
      metrics: m.metrics || {},
      representative: m.isRepresentative === true,
      suppressedBy: m.suppressedBy || "",
      reason: m.reasonCode || "",
    }));
  }

  function viewSymbol() {
    const symbols = new Set();
    (state.bundle?.pipeRuns || []).forEach((entry) => {
      (entry.run?.rows || []).forEach((r) => symbols.add(r.symbol));
    });
    (state.nativeCore?.rows || []).forEach((r) => symbols.add(r.symbol));
    const list = Array.from(symbols).sort();
    if (!list.length) return "<p>No native-core symbols on the current spine.</p>";
    if (!state.symbol || !list.includes(state.symbol)) state.symbol = list[0];
    const options = list
      .map(
        (s) =>
          '<option value="' + escapeHtml(s) + '"' + (s === state.symbol ? " selected" : "") + ">" +
          escapeHtml(s) + "</option>"
      )
      .join("");
    const matches = nativeMatchesFor(state.symbol) || [];
    const matched = matches.filter((m) => m.matched);
    const failed = matches.filter((m) => !m.matched);
    const chips = matched
      .map(
        (m) =>
          '<div class="sl-run"><span class="nc-chip">' + escapeHtml(m.id.replace(/^native\./, "").replace(/\.v1$/, "")) + "</span> " +
          '<strong>' + escapeHtml(m.relationship.toLowerCase()) + '</strong> ' +
          (m.representative ? '<span class="chip">representative</span> ' : '') +
          (m.suppressedBy ? '<span class="nc-twin">suppressed by ' + escapeHtml(m.suppressedBy) + '</span> ' : '') +
          (m.twin ? ' <span class="nc-twin">correlated_possible</span>' : "") +
          '<div class="mm-copy">state ' + escapeHtml(m.scannerState) +
          ' · input ' + escapeHtml(m.inputStatus) +
          ' · bars ' + Number(m.barCount) +
          ' · as-of ' + escapeHtml(m.asOf || 'n/a') +
          ' · formula ' + escapeHtml(m.formulaVersion || 'n/a') +
          ' · params ' + shortHash(m.parameterHash) +
          ' · adjustment ' + escapeHtml(m.adjustmentVersion || 'n/a') +
          ' · lineage ' + shortHash(m.lineageHash) +
          ' · metrics ' + escapeHtml(JSON.stringify(m.metrics)) + '</div></div>'
      )
      .join(" ");
    const fails = failed
      .map((m) => '<div class="mm-copy">' +
        escapeHtml(m.id.replace(/^native\./, "").replace(/\.v1$/, "")) +
        ': ' + escapeHtml(m.reason || m.inputStatus) + '</div>')
      .join("");
    return (
      '<div class="sl-symbol"><label>Symbol <select id="scannerLabSymbol">' + options + "</select></label></div>" +
      '<div class="sl-matches"><strong>matched</strong> ' + (chips || "<em>none</em>") + "</div>" +
      '<div class="sl-fails"><strong>failed</strong> ' + (fails || "<em>none</em>") + "</div>" +
      '<div class="mm-copy">matched - trade guidance, not an order. No probability or trade geometry is produced here.</div>'
    );
  }

  function viewPkShadow() {
    const pk = state.bundle?.pkShadow || { state: "PK_SHADOW", parity: "PARITY_UNKNOWN" };
    return (
      '<div class="sl-pk"><span class="chip">' + escapeHtml(pk.state) + "</span> " +
      '<span class="chip">' + escapeHtml(pk.parity) + "</span>" +
      '<p class="mm-copy">PK shadow parity is descriptive. It cannot change S7 publicState.</p></div>'
    );
  }

  function render() {
    const body = $("scannerLabBody");
    if (!body) return;
    renderSubtabs();
    if (state.tab === "Definitions") body.innerHTML = viewDefinitions();
    else if (state.tab === "Symbol") body.innerHTML = viewSymbol();
    else if (state.tab === "PK shadow") body.innerHTML = viewPkShadow();
    else body.innerHTML = viewPipeFlow();
    const select = $("scannerLabSymbol");
    if (select) {
      select.addEventListener("change", () => {
        state.symbol = select.value;
        render();
      });
    }
  }

  function apply(parts) {
    if (!parts) return;
    if (window.TrendForgeResearchSnapshot) {
      state.nativeCore = parts.nativeCore || null;
      state.pipeDefs = parts.pipeDefs || null;
      state.bundle = parts.bundle || null;
    } else {
      if (parts.nativeCore) state.nativeCore = parts.nativeCore;
      if (parts.pipeDefs) state.pipeDefs = parts.pipeDefs;
      if (parts.bundle) state.bundle = parts.bundle;
    }
    render();
  }

  async function refresh() {
    if (window.TrendForgeResearchSnapshot) return window.TrendForgeSelectionAdapter?.load();
    try {
      const response = await fetch(BUNDLE_ENDPOINT, { cache: "no-store" });
      if (!response.ok) {
        const body = $("scannerLabBody");
        if (body) body.innerHTML = "<p>WAIT_R10_PIPE - lab bundle HTTP " + response.status + "</p>";
        return;
      }
      state.bundle = await response.json();
      state.nativeCore = state.bundle.nativeCore || state.nativeCore;
      render();
    } catch (_) {
      /* keep last good lab */
    }
  }

  window.TrendForgeScannerLab = { apply, refresh, CONTRACT };

  function bindRunButton() {
    const button = $("scannerRunButton");
    if (!button || button.dataset.labWired === "1") return;
    button.dataset.labWired = "1";
    button.textContent = "Refresh lab (GET)";
    button.addEventListener("click", () => void refresh());
  }

  function bind() {
    if (!$("scannerLabPanel")) return;
    watchInspectorTabs();
    bindRunButton();
    if (!window.TrendForgeResearchSnapshot) void refresh();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
