(() => {
  "use strict";

  const CONTRACT = "trendforge.top10-research.v1";
  let requestGeneration = 0;

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
    const card = el("article", "top10-entry");
    const head = el("div", "top10-entry-head");
    head.appendChild(el("span", "top10-rank", `#${entry.displayRank}`));
    head.appendChild(el("strong", "top10-symbol", entry.symbol));
    head.appendChild(el("span", `state-chip ${entry.evidenceDirection === "BULLISH" ? "good" : "bad"}`, entry.board));
    if (entry.displayScore !== null && entry.displayScore !== undefined) {
      head.appendChild(el("span", "top10-score", `score ${entry.displayScore.toFixed(2)} (display only)`));
    }
    card.appendChild(head);

    const whyList = el("ul", "top10-why");
    (entry.why || []).forEach((reason) => whyList.appendChild(el("li", "top10-why-item", reason)));
    (entry.tags || []).forEach((tag) => whyList.appendChild(el("li", "top10-tag", tag)));
    if ((entry.dealSummary || "").length > 0) {
      whyList.appendChild(el("li", "top10-fact", `Large deal: ${entry.dealSummary}`));
    }
    if (entry.gapPct !== null && entry.gapPct !== undefined) {
      whyList.appendChild(el("li", "top10-fact", `Gap ${entry.gapPct > 0 ? "+" : ""}${entry.gapPct}% (CA-safe)`));
    }
    card.appendChild(whyList);

    const unknowns = entry.whyUnknown || [];
    if (unknowns.length > 0) {
      const unknownBox = el("div", "top10-unknown");
      unknownBox.appendChild(el("strong", null, "UNKNOWN"));
      const list = el("ul");
      unknowns.forEach((code) => list.appendChild(el("li", null, code)));
      unknownBox.appendChild(list);
      card.appendChild(unknownBox);
    }
    return card;
  }

  function boardColumn(title, entries, emptyCopy) {
    const column = el("div", "top10-column");
    column.appendChild(el("h4", `top10-title top10-${title.toLowerCase()}`, `${title} research (${entries.length})`));
    if (!entries.length) {
      column.appendChild(el("p", "top10-empty", emptyCopy));
      return column;
    }
    entries.forEach((entry) => column.appendChild(entryCard(entry)));
    return column;
  }

  function renderWait(message) {
    const panel = document.getElementById("top10ResearchPanel");
    if (!panel) return;
    panel.replaceChildren(
      el("p", "top10-wait-copy", message || "WAIT_R6_NOT_READY - top-10 research board needs the R1/R2/R14 spine. Nothing is invented while it waits.")
    );
  }

  function render(board) {
    const panel = document.getElementById("top10ResearchPanel");
    if (!panel) return;
    panel.replaceChildren();
    const calibration = el("p", "top10-calibration");
    calibration.appendChild(el("span", "chip wait", board.calibration || "RESEARCH_SHORTLIST_NOT_CONFIRMED"));
    calibration.appendChild(document.createTextNode(" Ranked research attention with stickers. Not trade advice, not confirmation, not probability."));
    panel.appendChild(calibration);

    if (board.marketFii) {
      const fii = board.marketFii;
      const chipText = fii.netCrore !== undefined && fii.netCrore !== null
        ? `Market FII net ${fii.netCrore} cr (${fii.dataDate || "?"}) - whole market, never per-stock`
        : `Market FII net UNKNOWN - ${fii.status || "no daily tape"}`;
      panel.appendChild(el("p", "top10-market-chip", chipText));
    }

    const grid = el("div", "top10-grid");
    grid.appendChild(boardColumn("BUY", board.buy || [], "No bullish WATCH rows passed the R2 queue and vetoes yet."));
    grid.appendChild(boardColumn("SELL", board.sell || [], "No bearish WATCH rows passed the R2 queue and vetoes yet."));
    panel.appendChild(grid);
  }

  async function load() {
    const generation = ++requestGeneration;
    try {
      const board = await fetchOptionalJson("/api/v1/selection/top10");
      if (generation !== requestGeneration) return null;
      if (!board) {
        renderWait("WAIT_R6_SPINE_NOT_READY - no hash-matched R1/R2/R14 spine is persisted for this run.");
        return null;
      }
      render(board);
      return board;
    } catch (error) {
      if (generation !== requestGeneration) return null;
      renderWait(`Top-10 research unavailable: ${error.message}`);
      return null;
    }
  }

  window.TrendForgeTop10Research = { contract: CONTRACT, load };

  void load();
  const refresh = document.getElementById("previewRefresh");
  if (refresh) refresh.addEventListener("click", () => { void load(); });
  window.addEventListener("trendforge:selection-ready", () => { void load(); });
})();
