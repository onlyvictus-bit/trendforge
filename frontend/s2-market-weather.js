(() => {
  "use strict";

  const CONTRACT = "trendforge.s2-market-weather.v1";
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

  function pctText(value) {
    if (value === null || value === undefined) return "UNKNOWN";
    return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
  }

  function renderStrip(weather) {
    const strip = document.getElementById("s2WeatherStrip");
    if (!strip) return;
    strip.replaceChildren();
    strip.appendChild(el("span", "chip", `WEATHER · ${weather.regimeLabel}`));

    const nifty = weather.nifty50 || {};
    const niftyPct = el("span", `s2-pill ${nifty.changePercent >= 0 ? "good" : "bad"}`,
      `NIFTY ${pctText(nifty.changePercent)}${nifty.close ? ` @ ${nifty.close}` : ""}`);
    niftyPct.title = `source: ${nifty.changePercentStatus || "UNKNOWN"} — points are never shown as percent`;
    strip.appendChild(niftyPct);

    const vix = weather.indiaVix || {};
    strip.appendChild(el("span", "s2-pill",
      `VIX ${vix.close ?? "UNKNOWN"} (${vix.band || "UNKNOWN"})`));

    const breadth = weather.breadth || {};
    const breadthText = breadth.status && !breadth.status.startsWith("UNKNOWN")
      ? `A/D ${breadth.advances}/${breadth.declines}`
      : `Breadth UNKNOWN`;
    strip.appendChild(el("span", "s2-pill", breadthText));

    const sectors = weather.sectors || [];
    if (sectors.length) {
      const leader = sectors[0];
      const laggard = sectors[sectors.length - 1];
      strip.appendChild(el("span", "s2-pill good",
        `Top: ${leader.name} ${pctText(leader.changePercent)}`));
      strip.appendChild(el("span", "s2-pill bad",
        `Lag: ${laggard.name} ${pctText(laggard.changePercent)}`));
    }

    const local = (weather.commodityLocal || []).find((c) => c.changePercent !== null);
    strip.appendChild(el("span", "s2-pill",
      local ? `MCX ${local.symbol} ${pctText(local.changePercent)} (local)` : "MCX UNKNOWN_NO_LOCAL_BAR"));

    strip.appendChild(el("span", "chip wait", "CONTEXT — never a stock vote"));
  }

  function quoteBlock(title, quote) {
    const box = el("div", "s2-quote");
    box.appendChild(el("h4", null, title));
    const pct = quote?.changePercent;
    box.appendChild(el("p", null,
      `${quote?.close ?? "UNKNOWN"} (${pct === null || pct === undefined ? "UNKNOWN" : pctText(pct)})`));
    box.appendChild(el("small", null,
      `points ${quote?.pointsChange ?? "UNKNOWN"} · prevClose ${quote?.previousClose ?? "UNKNOWN"} · source ${quote?.changePercentStatus || "UNKNOWN"}`));
    return box;
  }

  function renderIndexRoom(weather) {
    const content = el("div", "s2-room s2-index-room");
    const grid = el("div", "s2-quote-grid");
    grid.appendChild(quoteBlock("NIFTY 50", weather.nifty50));
    if (weather.bankNifty) grid.appendChild(quoteBlock("NIFTY BANK", weather.bankNifty));
    const vixBox = el("div", "s2-quote");
    vixBox.appendChild(el("h4", null, "INDIA VIX"));
    vixBox.appendChild(el("p", null, `${weather.indiaVix?.close ?? "UNKNOWN"} · band ${weather.indiaVix?.band || "UNKNOWN"}`));
    grid.appendChild(vixBox);
    const regimeBox = el("div", "s2-quote");
    regimeBox.appendChild(el("h4", null, "Regime (research only)"));
    regimeBox.appendChild(el("p", null, weather.regimeLabel || "UNKNOWN"));
    regimeBox.appendChild(el("small", null, "Weather never changes a stock's four-state."));
    grid.appendChild(regimeBox);
    content.appendChild(grid);

    const commodity = el("div", "s2-commodity");
    commodity.appendChild(el("h4", null, "Commodity weather"));
    const locals = weather.commodityLocal || [];
    if (!locals.length) {
      commodity.appendChild(el("small", null, "UNKNOWN_NO_LOCAL_MCX_BAR - global CFTC/WGC stays grey and cannot direct contracts."));
    } else {
      locals.forEach((c) => {
        commodity.appendChild(el("span", "s2-pill",
          `${c.symbol} ${pctText(c.changePercent)}${c.dte !== null && c.dte !== undefined ? ` · ${c.dte}d` : ""}`));
      });
    }
    content.appendChild(commodity);

    if ((weather.whyUnknown || []).length) {
      content.appendChild(el("p", "s2-unknowns",
        `UNKNOWN: ${weather.whyUnknown.join(" | ")}`));
    }
    return content;
  }

  function renderSectorRoom(weather) {
    const content = el("div", "s2-room s2-sector-room");
    const sectors = weather.sectors || [];
    if (!sectors.length) {
      content.appendChild(el("p", "s2-wait-copy", "UNKNOWN_SECTOR_ROWS_MISSING - official nse_all_indices last-good has no sector rows."));
      return content;
    }
    const table = el("table", "s2-sector-table");
    const head = el("tr");
    ["#", "Sector index", "Close", "Change %"].forEach((label) => head.appendChild(el("th", null, label)));
    table.appendChild(head);
    sectors.forEach((sector) => {
      const row = el("tr");
      row.appendChild(el("td", null, String(sector.rank ?? "-")));
      row.appendChild(el("td", null, sector.name));
      row.appendChild(el("td", null, sector.close !== null && sector.close !== undefined ? String(sector.close) : "UNKNOWN"));
      const pctCell = el("td", `s2-pct ${sector.changePercent >= 0 ? "good" : "bad"}`, pctText(sector.changePercent));
      row.appendChild(pctCell);
      table.appendChild(row);
    });
    content.appendChild(table);
    content.appendChild(el("p", "s2-note",
      "Official NSE sector indices ranked by honest percent. Context ranks - not stock votes, no yfinance."));
    return content;
  }

  const ROOM_RENDERERS = { index_dashboard: renderIndexRoom, sector_scope: renderSectorRoom };
  let latestPayload = null;

  function paintOpenRoom() {
    const activeButton = document.querySelector('.nav button[data-view="tool"].active[data-tool]');
    const tool = activeButton?.getAttribute("data-tool");
    const renderer = tool && ROOM_RENDERERS[tool];
    const host = document.getElementById("toolContent");
    if (!renderer || !host || !latestPayload) return;
    if (host.dataset.s2Room === tool) return;
    host.replaceChildren(renderer(latestPayload));
    host.dataset.s2Room = tool;
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest?.('button[data-tool]');
    if (!button || !ROOM_RENDERERS[button.getAttribute("data-tool")]) return;
    // Let app.js paint its WAIT copy first, then replace it with real weather.
    [50, 200, 600].forEach((delay) => setTimeout(() => {
      if (latestPayload) { paintOpenRoom(); }
    }, delay));
  });

  window.TrendForgeS2MarketWeatherRenderRoom = paintOpenRoom;

  function renderRooms(weather) {
    latestPayload = weather;
    window.TrendForgeS2WeatherPayload = weather;
    window.dispatchEvent(new CustomEvent("trendforge:s2-weather-ready", { detail: { contract: CONTRACT } }));
    paintOpenRoom();
  }

  function renderWait(message) {
    const strip = document.getElementById("s2WeatherStrip");
    if (strip) strip.replaceChildren(el("span", "chip wait", message));
  }

  async function load() {
    const generation = ++requestGeneration;
    try {
      const weather = await fetchOptionalJson("/api/v1/selection/market-weather");
      if (generation !== requestGeneration) return null;
      if (!weather) {
        renderWait("WAIT_S2_LAST_GOOD_MISSING");
        return null;
      }
      renderStrip(weather);
      renderRooms(weather);
      return weather;    } catch (error) {
      if (generation !== requestGeneration) return null;
      renderWait(`Weather unavailable: ${error.message}`);
      return null;
    }
  }

  window.TrendForgeS2MarketWeather = { contract: CONTRACT, load };

  void load();
  const refresh = document.getElementById("previewRefresh");
  if (refresh) refresh.addEventListener("click", () => { void load(); });
  window.addEventListener("trendforge:selection-ready", () => { void load(); });
})();
