(() => {
  "use strict";

  function $(id) {
    return document.getElementById(id);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function render(batch) {
    const list = $("r2bActivationList");
    const counts = $("r2bActivationCounts");
    const meta = $("r2bActivationMeta");
    if (!list) return;
    if (counts) {
      counts.textContent =
        `named ${batch.namedSourceCount} · authorized ${batch.authorizedCount} · ` +
        `mayConfirm ${batch.mayConfirmCount} · gateAuthorized ${batch.compilerGateAuthorizedCount} · ` +
        `sourceActivationReady=${batch.sourceActivationReady} · ${batch.acceptanceCeiling}`;
    }
    if (meta && batch.warnings && batch.warnings.length) {
      meta.textContent = batch.warnings.join(" ");
    }
    list.innerHTML = (batch.rows || [])
      .map(
        (row) => `<article class="r2b-row">
          <strong>${escapeHtml(row.sourceKey)}</strong>
          <span>${escapeHtml(row.activationStatus)} · mayConfirm ${row.maySupportConfirmed}</span>
          <div>${escapeHtml((row.whyWait || []).join(" · "))}</div>
        </article>`
      )
      .join("");
  }

  async function load() {
    const list = $("r2bActivationList");
    if (!list) return;
    try {
      const response = await fetch("/api/v1/selection/named-activation", {
        cache: "no-store",
        headers: { Accept: "application/json" }
      });
      if (response.status === 503) {
        list.textContent = "R2-B named activation WAIT until R1/R2 hashes match. sourceActivationReady stays false.";
        return;
      }
      if (!response.ok) {
        list.textContent = `R2-B named activation HTTP ${response.status}`;
        return;
      }
      render(await response.json());
    } catch (error) {
      list.textContent = `R2-B named activation failed: ${error.message}`;
    }
  }

  function bind() {
    if (!$("r2bActivationPanel")) return;
    void load();
    window.addEventListener("trendforge:selection-ready", () => {
      void load();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
