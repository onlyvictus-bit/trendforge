(() => {
  "use strict";

  const CONTRACT = "trendforge.hybrid-v2-overlay.v1";
  let overlayBatch = null;
  let caJoinBatch = null;
  let waitCode = null;

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function selectedSymbol() {
    const el = $("selectedSymbol");
    const raw = el ? String(el.textContent || "").trim().toUpperCase() : "";
    if (raw && raw !== "WAIT" && overlayBatch) {
      const hit = (overlayBatch.rows || []).find((row) => row.symbol === raw);
      if (hit) return hit.symbol;
    }
    const first = overlayBatch && overlayBatch.rows && overlayBatch.rows[0];
    return first ? first.symbol : null;
  }

  function rowFor(symbol) {
    if (!overlayBatch || !symbol) return null;
    return (overlayBatch.rows || []).find((row) => row.symbol === symbol) || null;
  }

  function chainCell(label, value, tone) {
    return `<div class="hybrid-v2-step ${tone}"><b>${label}</b><span>${escapeHtml(value)}</span></div>`;
  }

  // S6 is always UNKNOWN_NEEDS_R12 in this milestone; the value comes from the
  // overlay DTO (row.s6VehicleStatus) and must never be upgraded client-side.
  function renderChain() {
    const mount = $("hybridV2Chain");
    if (!mount) return;
    if (!overlayBatch) {
      mount.innerHTML =
        `<p class="hybrid-v2-wait">${escapeHtml(waitCode || "WAIT_HYBRID_OVERLAY_NOT_READY")} — paper overlay computes only when R1/R2/R14 lineage matches.</p>`;
      return;
    }
    const symbol = selectedSymbol();
    const row = rowFor(symbol);
    if (!row) {
      mount.innerHTML =
        '<p class="hybrid-v2-wait">WAIT_HYBRID_SYMBOL_NOT_IN_OVERLAY.</p>';
      return;
    }
    const s0Tone = row.asStatus === "STALE" ? "warn" : "ok";
    const s1Tone = row.r2PublicState === "REJECT" ? "bad" : "ok";
    const s5Label =
      row.s5LabelState === "LABEL_ONLY" ? "LABEL_ONLY" : "WAIT_WIDTH";
    mount.innerHTML =
      `<p class="hybrid-v2-meta">Hybrid V2/V3 S0–S9 (paper overlay — not File A) · ${escapeHtml(row.symbol)} · RESEARCH_PROXY_NOT_CALIBRATED</p>` +
      `<div class="hybrid-v2-strip">` +
      chainCell("S0", row.asStatus === "STALE" ? "WAIT_STALE" : "OK", s0Tone) +
      chainCell("S1", `${row.r2PublicState} / CA ${escapeHtml(row.r14CaState)}`, s1Tone) +
      chainCell("S2", "SKIP B1/B2 UNKNOWN", "warn") +
      chainCell("S3", `#${row.displayOrder}`, "ok") +
      chainCell(
        "S4",
        `WITHOUT p̂ ${row.withoutS4S5.pHat} / WITH ${row.withS4S5.pHat}`,
        "info"
      ) +
      chainCell("S5", s5Label, row.s5LabelState === "LABEL_ONLY" ? "info" : "warn") +
      chainCell("S6", escapeHtml(row.s6VehicleStatus), "warn") +
      chainCell("S7", `Kelly ill. ${row.kellyIllustration} (not size)`, "info") +
      chainCell("S8", "next-day VWAP rule", "info") +
      chainCell("S9", "labels not persisted", "warn") +
      `</div>`;
  }

  function renderPanel() {
    const mount = $("hybridV2OverlayList");
    if (!mount) return;
    if (!overlayBatch) {
      mount.textContent = `${waitCode || "WAIT_HYBRID_OVERLAY_NOT_READY"}.`;
      return;
    }
    const counts = $("hybridV2OverlayCounts");
    if (counts) {
      counts.textContent = `rows ${overlayBatch.rowCount} · calibration ${overlayBatch.calibration}`;
    }
    mount.innerHTML = (overlayBatch.rows || [])
      .map(
        (row) => `<section class="hybrid-v2-row">
        <header>${escapeHtml(row.symbol)} · ${escapeHtml(row.r2PublicState)} · CA ${escapeHtml(row.r14CaState)}</header>
        <div>AS ${escapeHtml(row.asStatus)}${row.asStatus === "USABLE" && row.asDeliveryZ != null ? ` z ${row.asDeliveryZ}` : ""} · B4 package ${escapeHtml(row.b4Package)}</div>
        <div>WITHOUT p̂ ${row.withoutS4S5.pHat} · WITH p̂ ${row.withS4S5.pHat} · Kelly illustration ${row.kellyIllustration} (not size)</div>
        <div class="hybrid-v2-why">${escapeHtml((row.whyWait || []).join(" · "))}</div>
      </section>`
      )
      .join("");
  }

  function render() {
    renderChain();
    renderPanel();
  }

  function applyHybridOverlay(batch) {
    overlayBatch = batch || null;
    render();
    return Boolean(overlayBatch);
  }

  function applyCaJoin(batch) {
    caJoinBatch = batch || null;
  }

  window.TrendForgeHybridOverlay = {
    contract: CONTRACT,
    applyHybridOverlay,
    applyCaJoin,
    rowFor,
    get loaded() {
      return Boolean(overlayBatch);
    },
    get caJoin() {
      return caJoinBatch;
    }
  };

  window.addEventListener("trendforge:selection-ready", () => {
    void (async () => {
      try {
        const response = await fetch("/api/v1/hybrid-v2/overlay?limit=40", {
          cache: "no-store",
          headers: { Accept: "application/json" }
        });
        if (!response.ok) {
          overlayBatch = null;
          waitCode = null;
          try {
            const payload = await response.json();
            waitCode = payload && payload.detail && payload.detail.code
              ? String(payload.detail.code)
              : null;
          } catch (_error) {
            // Body is not JSON; keep the generic wait code.
          }
          render();
          return;
        }
        waitCode = null;
        applyHybridOverlay(await response.json());
      } catch (_error) {
        overlayBatch = null;
        waitCode = null;
        render();
      }
    })();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render);
  } else {
    render();
  }
})();
