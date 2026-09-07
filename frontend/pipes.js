(() => {
  "use strict";

  const DEFS_ENDPOINT = "/api/v1/pipes/definitions";

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

  function stageChips(stages) {
    return (stages || [])
      .map(
        (s) =>
          `<span class="pl-stage" title="${escapeHtml((s.reasons || []).join(" · "))}">` +
          `${escapeHtml(s.op)} ${Number(s.in_count ?? s.inCount ?? 0)}&rarr;${Number(s.out_count ?? s.outCount ?? 0)}` +
          `</span>`
      )
      .join('<span class="pl-arrow">&rarr;</span>');
  }

  function runMarkup(run) {
    const survivors = (run.rows || [])
      .map((r) => `<span class="pl-sym">${escapeHtml(r.symbol || "")}</span>`)
      .join(" ");
    return `
      <div class="pl-run" data-pipe="${escapeHtml(run.pipeId || "")}">
        <strong>${escapeHtml(run.pipeId || "")}</strong>
        <div class="pl-stages">${stageChips(run.stages)}</div>
        <div class="pl-survivors">${survivors || '<span class="nc-none">no survivors</span>'}</div>
      </div>`;
  }

  function renderDefinitions(payload) {
    const ops = $("pipeLabOps");
    if (!ops || !payload) return;
    const defs = payload.definitions || [];
    ops.innerHTML =
      defs
        .map(
          (d) => `
      <section class="pl-pipe" data-pipe="${escapeHtml(d.pipeId)}">
        <strong>${escapeHtml(d.pipeId)}</strong>
        <span class="nc-none">hash ${escapeHtml(String(d.parameterHash || "").slice(0, 12))}…</span>
        <div class="pl-runbox"><em>WAIT_R10_LOADING</em></div>
      </section>`
        )
        .join("") +
      '<div class="pl-copy">Pipes &mdash; guidance lens, zero claims.</div>';
    if (!window.TrendForgeResearchSnapshot) defs.forEach((d) => void loadRun(d.pipeId));
    else ops.querySelectorAll('.pl-runbox').forEach(box => { box.textContent = 'WAIT_SNAPSHOT_PIPE'; });
  }

  async function loadRun(pipeId) {
    const box = document.querySelector(
      `.pl-pipe[data-pipe="${CSS.escape(pipeId)}"] .pl-runbox`
    );
    if (!box) return;
    try {
      const response = await fetch(`/api/v1/pipes/${encodeURIComponent(pipeId)}/run`, {
        cache: "no-store",
      });
      if (!response.ok) {
        let code = "";
        try {
          code = (await response.json()).detail?.code || "";
        } catch (_) {}
        box.textContent = `WAIT — HTTP ${response.status}${code ? " " + code : ""}`;
        return;
      }
      box.innerHTML = runMarkup(await response.json());
    } catch (error) {
      box.textContent = `failed: ${error.message}`;
    }
  }

  function applyDefinitions(payload) {
    renderDefinitions(payload);
  }

  function apply(batch) {
    // Direct run injection (adapter alternative): batch is one PipeRunV1.
    if (!batch) return;
    const box = document.querySelector(
      `.pl-pipe[data-pipe="${CSS.escape(batch.pipeId || "")}"] .pl-runbox`
    );
    if (box) box.innerHTML = runMarkup(batch);
  }

  async function load() {
    const ops = $("pipeLabOps");
    if (!ops) return;
    try {
      const response = await fetch(DEFS_ENDPOINT, { cache: "no-store" });
      if (!response.ok) {
        ops.textContent = `Pipe Lab WAIT — HTTP ${response.status}. Recipes compose the last hash-matched R8 native-core run.`;
        return;
      }
      renderDefinitions(await response.json());
    } catch (error) {
      ops.textContent = `Pipe Lab failed: ${error.message}`;
    }
  }

  window.TrendForgePipeLab = {
    apply,
    applyDefinitions,
    CONTRACT: "trendforge.pipe-run.v1",
  };

  function bind() {
    if (window.TrendForgeResearchSnapshot) return;
    if (!$("pipeLabPanel")) return;
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
