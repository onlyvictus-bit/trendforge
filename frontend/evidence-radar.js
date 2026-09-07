(() => {
  "use strict";

  const CONTRACT = "trendforge.evidence-radar.v1";
  let requestGeneration = 0;
  let currentHorizon = "ALL";
  let snapshotPayload = null;

  async function fetchOptionalJson(path) {
    const response = await fetch(path, { cache: "no-store", headers: { Accept: "application/json" } });
    if (response.status === 503) return null;
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const payload = await response.json();
        detail = payload?.detail?.code || payload?.detail?.message || detail;
      } catch (_error) {
        // Status is enough when the body is not JSON.
      }
      throw new Error(`${path}: ${detail}`);
    }
    return response.json();
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function entryCard(entry) {
    const card = el("article", "radar-entry");
    const head = el("div", "radar-entry-head");
    head.appendChild(el("span", "radar-rank", `#${entry.displayRank}`));
    head.appendChild(el("strong", "radar-symbol", entry.symbol));
    head.appendChild(el("span", `state-chip ${entry.researchBoard === "BUY" ? "good" : "bad"}`, entry.researchBoard));
    head.appendChild(el("span", "radar-state", entry.publicState));
    card.appendChild(head);

    const lines = el("ul", "radar-lines");
    [
      ["HOW", entry.how || "UNKNOWN"],
      ["WHAT", entry.what || "UNKNOWN"],
      ["WHERE", entry.where || "UNKNOWN"],
      ["WHEN", entry.when || "UNKNOWN"],
    ].forEach(([label, value]) => {
      const item = el("li", "radar-line");
      item.appendChild(el("strong", null, label));
      item.appendChild(document.createTextNode(` ${value}`));
      lines.appendChild(item);
    });
    card.appendChild(lines);

    if ((entry.whyUnknown || []).length > 0) {
      const unknownBox = el("div", "radar-unknown");
      unknownBox.appendChild(el("strong", null, `UNKNOWN (${entry.whyUnknown.length})`));
      unknownBox.appendChild(el("span", null, entry.whyUnknown.join(" | ")));
      card.appendChild(unknownBox);
    }
    return card;
  }

  function renderCoverage(coverage) {
    const strip = document.getElementById("evidenceRadarCoverage");
    if (!strip) return;
    strip.replaceChildren();
    strip.appendChild(
      el("span", "radar-coverage-count",
        `${coverage.represented}/${coverage.totalJobs} slots represented · skipped ${coverage.skippedCount} · unknown ${coverage.unknownCount}`)
    );
    const pending = coverage.notNormalizedKeys || [];
    if (pending.length > 0) {
      strip.appendChild(el("span", "radar-coverage-pending", `NOT_NORMALIZED: ${pending.join(", ")}`));
    }
  }

  function renderBoards(board) {
    const wrap = el("div", "radar-board");
    [["BUY", board.buy], ["SELL", board.sell]].forEach(([label, entries]) => {
      const column = el("div", "radar-column");
      column.appendChild(el("h4", `radar-title radar-${label.toLowerCase()}`,
        `${label} (${(entries || []).length})`));
      if (!entries || !entries.length) {
        column.appendChild(el("p", "radar-empty",
          `No honest ${label} seat for this horizon yet. Fewer than 10 is normal.`));
        return;
      }
      entries.forEach((entry) => column.appendChild(entryCard(entry)));
      wrap.appendChild(column);
    });
    return wrap;
  }

  function render(radar) {
    const panel = document.getElementById("evidenceRadarPanel");
    if (!panel) return;
    renderCoverage(radar.coverage);

    const tabsHost = document.getElementById("evidenceRadarTabs");
    if (tabsHost && !tabsHost.childElementCount) {
      ["ALL", "INTRADAY", "SWING", "POSITION", "COMMODITY"].forEach((name) => {
        const tab = el("button", `filter${name === currentHorizon ? " active" : ""}`, name);
        tab.type = "button";
        tab.addEventListener("click", () => {
          currentHorizon = name;
          [...tabsHost.children].forEach((child) => child.classList.remove("active"));
          tab.classList.add("active");
          void load();
        });
        tabsHost.appendChild(tab);
      });
    }

    const content = document.getElementById("evidenceRadarContent");
    if (!content) return;
    content.replaceChildren();

    const chip = radar.marketFiiChip;
    const chipLine = el("p", "radar-market-chip");
    chipLine.appendChild(el("span", "chip wait", radar.calibration));
    chipLine.appendChild(document.createTextNode(
      chip && chip.ok
        ? ` Market FII net ${chip.value} cr - whole market, never per-stock.`
        : " Market FII net UNKNOWN - whole-market tape missing."
    ));
    content.appendChild(chipLine);

    const horizons = currentHorizon === "ALL"
      ? Object.keys(radar.boards)
      : [currentHorizon];
    horizons.forEach((horizon) => {
      const board = radar.boards[horizon];
      if (!board) return;
      const section = el("section", "radar-horizon");
      section.appendChild(el("h3", "radar-horizon-title", `${horizon} · ${board.horizon === "COMMODITY" ? "local MCX required" : "WAIT ceiling"}`));
      section.appendChild(renderBoards(board));
      content.appendChild(section);
    });
  }

  function renderWait(message) {
    const content = document.getElementById("evidenceRadarContent");
    if (content) content.replaceChildren(el("p", "radar-wait-copy", message));
  }

  async function load() {
    if (window.TrendForgeResearchSnapshot) {
      if (snapshotPayload) render(snapshotPayload);
      return snapshotPayload;
    }
    const generation = ++requestGeneration;
    try {
      const query = currentHorizon === "ALL" ? "" : `?horizon=${currentHorizon}`;
      const radar = await fetchOptionalJson(`/api/v1/selection/evidence-radar${query}`);
      if (generation !== requestGeneration) return null;
      if (!radar) {
        renderWait("WAIT_RADAR_SPINE_NOT_READY - the radar needs the R1/R2/R14 spine before it can speak.");
        return null;
      }
      render(radar);
      return radar;
    } catch (error) {
      if (generation !== requestGeneration) return null;
      renderWait(`Evidence radar unavailable: ${error.message}`);
      return null;
    }
  }

  window.TrendForgeEvidenceRadar = { contract: CONTRACT, load, apply(payload) { snapshotPayload = payload; if (!payload) { renderWait('WAIT_SNAPSHOT_RADAR'); return; } render(payload); } };

  void load();
  const refresh = document.getElementById("previewRefresh");
  if (refresh) refresh.addEventListener("click", () => { void load(); });
  window.addEventListener("trendforge:selection-ready", () => { void load(); });
})();
