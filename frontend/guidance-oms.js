(() => {
  "use strict";

  const S7_URL = "/api/v1/selection/s7-state";
  const PREVIEW_URL = "/api/v1/selection/guidance-oms/preview";
  const PLACE_URL = "/api/v1/selection/guidance-oms/place";
  const ARM_URL = "/api/v1/settings/live-orders-arm";

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

  function armSwitch() {
    return $("armLiveOrders");
  }

  function ticketRow(row) {
    const symbol = escapeHtml(row.symbol || "");
    const state = escapeHtml(row.publicState || "");
    return `
      <div class="goms-row" data-symbol="${symbol}" data-state="${state}">
        <strong>${symbol}</strong>
        <span class="s7-chip" data-state="${state}">${state}</span>
        <button class="filter goms-preview" type="button" data-symbol="${symbol}">Preview ticket</button>
        <button class="filter goms-place" type="button" data-symbol="${symbol}" disabled>Place (armed only)</button>
        <pre class="goms-json" hidden></pre>
      </div>`;
  }

  async function render() {
    const list = $("guidanceOmsList");
    if (!list) return;
    let batch;
    try {
      const response = await fetch(S7_URL, { cache: "no-store" });
      if (!response.ok) {
        list.innerHTML = `<p class="radar-wait-copy">Guidance OMS WAIT — s7-state HTTP ${response.status}. Paper tickets appear when the selection spine is ready.</p>`;
        return;
      }
      batch = await response.json();
    } catch (error) {
      list.textContent = `Guidance OMS failed: ${error.message}`;
      return;
    }
    apply(batch);
  }

  function apply(batch) {
    const list = $("guidanceOmsList");
    if (!list) return;
    if (!batch) {
      list.textContent = 'Guidance unavailable for this snapshot. No retained ticket is current.';
      return;
    }
    const rows = (batch.rows || []).filter(
      (row) =>
        row.publicState === "CONFIRMED" ||
        row.draftConfirmedEligible === true ||
        Number(row.researchQuantity || 0) > 0
    );
    if (!rows.length) {
      list.innerHTML =
        '<p class="radar-wait-copy">No rows at the confirmation point yet. Guidance OMS stays preview-only.</p>';
      return;
    }
    list.innerHTML = rows.map(ticketRow).join("");
  }

  async function preview(symbol, holder) {
    holder.hidden = false;
    holder.textContent = "building paper ticket…";
    try {
      const response = await fetch(PREVIEW_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol }),
      });
      const payload = await response.json();
      if (!response.ok) {
        holder.textContent = `Preview failed HTTP ${response.status}: ${JSON.stringify(payload.detail ?? payload)}`;
        return null;
      }
      holder.textContent = JSON.stringify(payload, null, 2);
      return payload;
    } catch (error) {
      holder.textContent = `Preview failed: ${error.message}`;
      return null;
    }
  }

  async function place(symbol, holder, button) {
    holder.hidden = false;
    button.disabled = true;
    holder.textContent = "placing…";
    try {
      const response = await fetch(PLACE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol }),
      });
      const payload = await response.json();
      if (response.status === 409 && payload?.detail?.code === "LIVE_ORDERS_ARMED_OFF") {
        holder.textContent =
          "409 LIVE_ORDERS_ARMED_OFF — live orders are OFF by default. Arm requires env + OPENALGO_RO lane + switch.";
        return;
      }
      holder.textContent = `HTTP ${response.status}: ${JSON.stringify(payload, null, 2)}`;
    } catch (error) {
      holder.textContent = `Place failed: ${error.message}`;
    } finally {
      button.disabled = !armSwitch()?.checked;
    }
  }

  async function pushArm(armed) {
    const meta = $("guidanceOmsMeta");
    try {
      const response = await fetch(ARM_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ armed }),
      });
      const payload = await response.json();
      if (meta) {
        meta.textContent = payload.liveOrdersAllowed
          ? "ARMED (env+lane+switch all on)"
          : "preview only";
      }
    } catch (error) {
      if (meta) meta.textContent = `arm failed: ${error.message}`;
    }
    document.querySelectorAll(".goms-place").forEach((button) => {
      button.disabled = !armed;
    });
  }

  window.TrendForgeGuidanceOMS = {apply};

  function bind() {
    const panel = $("guidanceOmsPanel");
    if (!panel) return;
    if (!window.TrendForgeResearchSnapshot) {
      void render();
      window.addEventListener("trendforge:selection-ready", () => { void render(); });
    }
    panel.addEventListener("click", (event) => {
      const target = event.target.closest("button");
      if (!target) return;
      const row = target.closest(".goms-row");
      if (!row) return;
      const symbol = target.dataset.symbol || row.dataset.symbol;
      const holder = row.querySelector(".goms-json");
      if (target.classList.contains("goms-preview")) {
        void preview(symbol, holder);
      } else if (target.classList.contains("goms-place")) {
        void place(symbol, holder, target);
      }
    });
    armSwitch()?.addEventListener("change", (event) => {
      void pushArm(event.target.checked === true);
    });
    void fetch(ARM_URL)
      .then((r) => r.json())
      .then((state) => {
        if ($("guidanceOmsMeta")) {
          $("guidanceOmsMeta").textContent = state.liveOrdersAllowed
            ? "ARMED (env+lane+switch all on)"
            : "preview only";
        }
      })
      .catch(() => {});
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
