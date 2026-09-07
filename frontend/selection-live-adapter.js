(() => {
  "use strict";

  const CONTRACT = "trendforge.selection-live-adapter.v1";
  let requestGeneration = 0;
  let hasSnapshot = false;

  // Other panels may retain useful old context. Never leave it silently current.
  function markUnavailablePanels(panels) {
    for (const [ids, payload] of panels) {
      for (const id of ids) {
        const panel = document.getElementById(id);
        if (!panel || typeof panel.querySelectorAll !== 'function') continue;
        panel.querySelectorAll('.snapshot-request-status').forEach(node => node.remove());
        if (!payload) panel.insertAdjacentHTML('afterbegin',
          '<p class="snapshot-request-status" role="status">RESPONSE UNAVAILABLE - any retained values below are historical, not revalidated. See refresh failures.</p>');
      }
    }
  }

  const CONTEXT_MOUNTS = [
    ['s4StructurePanel', 's4StructureOps'], ['s5EnrichmentPanel', 's5EnrichmentOps'],
    ['s6InspectorMount', 's6ResolutionOps'], ['nativeCorePanel'], ['mcxMasterPanel'],
    ['researchQtyPanel', 'researchFundsPanel', 'researchPositionCard'], ['openAlgoShadowPanel']
  ];

  async function fetchJson(path) {
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    const timer = controller ? setTimeout(() => controller.abort(), 15000) : null;
    try {
      const response = await fetch(path, {
        cache: "no-store", headers: { Accept: "application/json" },
        ...(controller ? {signal: controller.signal} : {})
      });
      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const payload = await response.json();
          detail = payload?.detail?.code || payload?.detail?.message || detail;
        } catch (_error) {
          // HTML or malformed error bodies are never data.
        }
        throw new Error(`${path}: ${detail}`);
      }
      return await response.json();
    } finally {
      if (timer !== null) clearTimeout(timer);
    }
  }

  async function loadLiveSelection() {
    const generation = ++requestGeneration;
    const errors = {};
    const provenance = window.TrendForgeStatusProvenance;
    if (provenance) provenance.begin();
    const fetchOptionalJson = async (path) => {
      try { return await fetchJson(path); }
      catch (error) { errors[path] = error.message; return null; }
    };
    const renderer = window.TrendForgeProductFixture;
    try {
      if (!renderer || typeof renderer.applyLiveSelection !== "function") {
        throw new Error("Exclusive final-product renderer is unavailable");
      }
      const [attention, evidence, structure, identityPin, caJoin, overlay, namedActivation, s3Watch, s4Pack, s5Enrich, s6Resolve, loadedS7, loadedS8, dataLane, researchQty, r16Status, r16Metrics, nativeCore, pipeDefs, mcxMaster, labBundle, openalgoShadow] = await Promise.all([
        fetchJson("/api/v1/selection/attention"),
        fetchJson("/api/v1/selection/evidence"),
        fetchOptionalJson("/api/v1/selection/structure"),
        fetchOptionalJson("/api/v1/selection/identity-pin"),
        fetchOptionalJson("/api/v1/selection/ca-join"),
        fetchOptionalJson("/api/v1/hybrid-v2/overlay?limit=40"),
        fetchOptionalJson("/api/v1/selection/named-activation"),
        fetchOptionalJson("/api/v1/selection/cheap-discovery/watch?limit=50"),
        fetchOptionalJson("/api/v1/selection/s4-structure"),
        fetchOptionalJson("/api/v1/selection/s5-enrichment"),
        fetchOptionalJson("/api/v1/selection/s6-resolution"),
        fetchOptionalJson("/api/v1/selection/s7-state"),
        fetchOptionalJson("/api/v1/selection/scans/latest"),
        fetchOptionalJson("/api/v1/settings/data-lane"),
        fetchOptionalJson("/api/v1/selection/research-quantity"),
        fetchOptionalJson("/api/v1/selection/pit/status"),
        fetchOptionalJson("/api/v1/selection/pit/metrics"),
        fetchOptionalJson("/api/v1/scanners/native-core"),
        fetchOptionalJson("/api/v1/pipes/definitions"),
        fetchOptionalJson("/api/v1/selection/mcx-master"),
        fetchOptionalJson("/api/v1/scanners/lab-bundle"),
        fetchOptionalJson("/api/v1/integrations/openalgo/shadow")
      ]);
      if (generation !== requestGeneration) return null;
      let s7State = loadedS7;
      let s8Latest = loadedS8;
      if (s7State && (!attention.runHash || s7State.r2RunHash !== attention.runHash)) {
        errors['/api/v1/selection/s7-state'] = 'S7_LINEAGE_MISMATCH_OR_MISSING';
        s7State = null;
      }
      if (s8Latest && (!attention.runHash || s8Latest.lineage?.r2RunHash !== attention.runHash ||
          (structure?.runHash && s8Latest.lineage?.r5RunHash !== structure.runHash))) {
        errors['/api/v1/selection/scans/latest'] = 'S8_LINEAGE_MISMATCH_OR_MISSING';
        s8Latest = null;
      }
      const count = renderer.applyLiveSelection(attention, evidence, structure, s4Pack);
      hasSnapshot = true;
      if (window.TrendForgeS3CheapDiscovery) {
        window.TrendForgeS3CheapDiscovery.apply(s3Watch);
      }
      if (window.TrendForgeS4Structure) {
        window.TrendForgeS4Structure.apply(s4Pack);
      }
      if (window.TrendForgeS5Enrichment) {
        window.TrendForgeS5Enrichment.apply(s5Enrich);
      }
      if (window.TrendForgeS6Resolution) {
        window.TrendForgeS6Resolution.apply(s6Resolve);
      }
      if (window.TrendForgeS7State) {
        window.TrendForgeS7State.apply(s7State);
      }
      if (window.TrendForgeS8Persist) {
        window.TrendForgeS8Persist.apply(s8Latest);
      }
      if (window.TrendForgeDataLane) {
        window.TrendForgeDataLane.apply(dataLane);
      }
      if (window.TrendForgeResearchQty) {
        window.TrendForgeResearchQty.apply(researchQty, s7State);
      }
      if (window.TrendForgeOpenAlgoShadow) {
        window.TrendForgeOpenAlgoShadow.apply(openalgoShadow);
      }
      if (window.TrendForgeR16PitValidation) {
        window.TrendForgeR16PitValidation.apply({ status: r16Status, metrics: r16Metrics });
      }
      if (window.TrendForgeNativeCore) {
        window.TrendForgeNativeCore.apply(nativeCore);
      }
      if (window.TrendForgePipeLab) {
        window.TrendForgePipeLab.applyDefinitions(pipeDefs);
      }
      if (window.TrendForgeMcxMaster) {
        window.TrendForgeMcxMaster.apply(mcxMaster);
      }
      if (window.TrendForgeScannerLab) {
        window.TrendForgeScannerLab.apply({ nativeCore, pipeDefs, bundle: labBundle });
      }
      window.dispatchEvent(new CustomEvent("trendforge:selection-ready", {
        detail: {
          contract: CONTRACT,
          count,
          r1BundleId: evidence.bundleId,
          r2RunId: attention.runId,
          r4RunId: identityPin && identityPin.runId,
          r5RunId: structure && structure.runId,
          r14RunId: caJoin && caJoin.runId,
          r2bRunId: namedActivation && namedActivation.runId,
          s3RunId: s3Watch && s3Watch.sourceRunId,
          s4RunId: s4Pack && s4Pack.runId,
          s5RunId: s5Enrich && s5Enrich.runId,
          s6RunId: s6Resolve && s6Resolve.runId,
          r16DatasetRunId: r16Status && r16Status.latestDatasetRunId,
          r16ValidationStatus: r16Status && r16Status.validationStatus
        }
      }));
      if (window.TrendForgeHybridOverlay) {
        window.TrendForgeHybridOverlay.applyCaJoin(caJoin);
        window.TrendForgeHybridOverlay.applyHybridOverlay(overlay);
      }
      markUnavailablePanels(CONTEXT_MOUNTS.map((ids, index) =>
        [ids, [s4Pack, s5Enrich, s6Resolve, nativeCore, mcxMaster, researchQty, openalgoShadow][index]]));
      if (provenance) provenance.accept({attention, evidence, structure, s7State, s8Latest, r16Status, errors});
      return { attention, evidence, structure, identityPin, caJoin, overlay, namedActivation, s3Watch, s4Pack, s5Enrich, s6Resolve, openalgoShadow, count };
    } catch (error) {
      if (generation !== requestGeneration) return null;
      document.body.dataset.selectionMode = hasSnapshot ? "STALE_RETAINED" : "FIXTURE_FALLBACK";
      if (window.TrendForgeS7State) window.TrendForgeS7State.apply(null);
      if (window.TrendForgeS8Persist) window.TrendForgeS8Persist.apply(null);
      if (window.TrendForgeR16PitValidation) window.TrendForgeR16PitValidation.apply({status: null, metrics: null});
      markUnavailablePanels(CONTEXT_MOUNTS.map(ids => [ids, null]));
      if (provenance) provenance.fail(error.message);
      if (renderer && typeof renderer.setSelectionAdapterStatus === "function") {
        renderer.setSelectionAdapterStatus(
          `R1/R2 refresh unavailable: ${error.message}. ${hasSnapshot ? "Prior snapshot retained with its original time; not current." : "Fixture rows remain explicitly non-live."}`
        );
      }
      window.dispatchEvent(new CustomEvent("trendforge:selection-error", {
        detail: { contract: CONTRACT, message: error.message }
      }));
      return null;
    }
  }

  window.TrendForgeSelectionAdapter = {
    contract: CONTRACT,
    load: loadLiveSelection
  };

  const refresh = document.getElementById("previewRefresh");
  if (refresh) refresh.addEventListener("click", () => { void loadLiveSelection(); });
  void loadLiveSelection();
})();
