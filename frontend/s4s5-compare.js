(() => {
  "use strict";

  const STORAGE_KEY = "trendforge.s4s5.view";

  function $(id) {
    return document.getElementById(id);
  }

  function applyView(view) {
    const withBox = $("s4s5With");
    const withoutBox = $("s4s5Without");
    const bothBox = $("s4s5Both");
    if (!withBox || !withoutBox || !bothBox) return;
    if (view === "with") {
      withBox.checked = true;
      withoutBox.checked = false;
      bothBox.checked = false;
    } else if (view === "without") {
      withBox.checked = false;
      withoutBox.checked = true;
      bothBox.checked = false;
    } else {
      withBox.checked = true;
      withoutBox.checked = true;
      bothBox.checked = true;
    }
    try {
      localStorage.setItem(STORAGE_KEY, view);
    } catch (_error) {
      // Preference is optional.
    }
  }

  // The last-changed checkbox decides the view. BOTH is a derived shortcut,
  // never a trap that snaps a single selection back to both.
  function viewFromEvent(id) {
    const withChecked = $("s4s5With").checked;
    const withoutChecked = $("s4s5Without").checked;
    if (id === "s4s5With") {
      if (!withChecked) return withoutChecked ? "without" : "both";
      return withoutChecked ? "both" : "with";
    }
    if (id === "s4s5Without") {
      if (!withoutChecked) return withChecked ? "with" : "both";
      return withChecked ? "both" : "without";
    }
    return $("s4s5Both").checked ? "both" : "both";
  }

  function readView() {
    const withBox = $("s4s5With");
    const withoutBox = $("s4s5Without");
    if (!withBox || !withoutBox) return "both";
    if (withBox.checked && withoutBox.checked) return "both";
    if (withBox.checked) return "with";
    if (withoutBox.checked) return "without";
    return "both";
  }

  function card(title, result, extra) {
    if (!result) return "";
    const pass = result.wouldPassPMin ? "PASS p_min" : "FAIL p_min";
    const pack = result.package ? `<div>package ${result.package}</div>` : "";
    const formula = result.formula ? `<div class="s4s5-formula">${result.formula}</div>` : "";
    return `<article class="s4s5-card"><h4>${title}</h4>
      ${formula}
      <div>p̂ ${result.pHat} vs p_min ${result.pMin} → ${pass}</div>
      <div>Kelly illustration ${result.kellyIllustration} (not size)</div>
      <div>entry ${result.entryLabel}${result.entryLevel != null ? ` @ ${result.entryLevel}` : ""}</div>
      <div>${result.t1Label} · ${result.t2Label}</div>
      ${pack}
      <div>logit ${result.logit}</div>
      ${extra || ""}
    </article>`;
  }

  function render(batch) {
    const list = $("s4s5CompareList");
    const counts = $("s4s5CompareCounts");
    const meta = $("s4s5CompareMeta");
    if (!list || !counts) return;
    const view = readView();
    counts.textContent =
      `rows ${batch.rowCount} · WITH pass ${batch.withPassCount} · WITHOUT pass ${batch.withoutPassCount} · p_min ${batch.pMin} · ${batch.calibration}`;
    const strip = $("s4s5FormulaStrip");
    if (strip && batch.withFormula && batch.withoutFormula) {
      strip.textContent =
        `WITH: ${batch.withFormula}\nWITHOUT: ${batch.withoutFormula}\n${batch.pMinFormula || ""} · Kelly illustration only, not size`;
    }
    if (meta && batch.warnings && batch.warnings.length) {
      meta.textContent = batch.warnings.join(" ");
    }
    list.innerHTML = (batch.rows || [])
      .map((row) => {
        const withCol =
          view === "with" || view === "both"
            ? card("WITH original S4/S5", row.withS4S5)
            : "";
        const withoutCol =
          view === "without" || view === "both"
            ? card("WITHOUT split", row.withoutS4S5)
            : "";
        return `<section class="s4s5-row">
          <header>${row.symbol} · ${row.r2PublicState} · ${row.direction} · z_side ${row.sideZ} · z_book ${row.bookZ} · inflation ${row.pHatInflation}</header>
          <div class="s4s5-grid">${withCol}${withoutCol}</div>
        </section>`;
      })
      .join("");
  }

  async function load() {
    const list = $("s4s5CompareList");
    if (!list) return;
    try {
      const response = await fetch("/api/v1/selection/s4s5-compare?limit=40", {
        cache: "no-store",
        headers: { Accept: "application/json" }
      });
      if (response.status === 503) {
        list.textContent = "S4/S5 compare WAIT until R2/R5 hashes match.";
        return;
      }
      if (!response.ok) {
        list.textContent = `S4/S5 compare HTTP ${response.status}`;
        return;
      }
      render(await response.json());
    } catch (error) {
      list.textContent = `S4/S5 compare failed: ${error.message}`;
    }
  }

  function bind() {
    const withBox = $("s4s5With");
    if (!withBox) return;
    let stored = "both";
    try {
      stored = localStorage.getItem(STORAGE_KEY) || "both";
    } catch (_error) {
      stored = "both";
    }
    applyView(stored);
    const onChange = (event) => {
      applyView(viewFromEvent(event.target.id));
      void load();
    };
    withBox.addEventListener("change", onChange);
    $("s4s5Without").addEventListener("change", onChange);
    $("s4s5Both").addEventListener("change", onChange);
    void load();
    window.addEventListener("trendforge:selection-ready", () => { void load(); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
