(() => {
  "use strict";

  const CONTRACT = "trendforge.data-lane.v1";

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function apply(dto) {
    if (!dto) return;
    const meta = document.getElementById("dataLaneMeta");
    const sw = document.getElementById("dataLaneSwitch");
    const effective = dto.effectiveLane || dto.effective_lane || "FREE_OFFICIAL";
    const mode = dto.intradayMode || dto.intraday_mode || "OFF";
    const blocker = dto.blocker || "";
    if (sw) {
      sw.checked = effective === "OPENALGO_RO";
      sw.dataset.effective = effective;
    }
    if (meta) {
      meta.textContent = `${effective} · intraday ${mode}${blocker ? " · " + blocker : ""}`;
    }
  }

  async function persistPreference(lane) {
    const response = await fetch("/api/v1/settings/data-lane", {
      method: "POST",
      cache: "no-store",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ lane })
    });
    if (!response.ok) return;
    apply(await response.json());
  }

  function bind() {
    const sw = document.getElementById("dataLaneSwitch");
    if (!sw || sw.dataset.bound === "1") return;
    sw.dataset.bound = "1";
    sw.addEventListener("change", () => {
      persistPreference(sw.checked ? "OPENALGO_RO" : "FREE_OFFICIAL");
    });
  }

  document.addEventListener("DOMContentLoaded", bind);
  window.TrendForgeDataLane = { apply, CONTRACT };
})();
