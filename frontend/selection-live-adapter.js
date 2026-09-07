(() => {
  "use strict";

  const CONTRACT = "trendforge.selection-live-adapter.v1";
  let requestGeneration = 0;
  let hasSnapshot = false;
  let activeController = null;
  const SNAPSHOT_URL = "/api/v1/selection/snapshot";

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

  async function fetchJson(path, signal) {
    const response = await fetch(path, {
      cache: "no-store", headers: { Accept: "application/json" },
      ...(signal ? {signal} : {})
    });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const payload = await response.json();
        detail = payload?.detail?.code || detail;
      } catch (_) { /* Non-JSON errors are not data. */ }
      throw new Error(`${path}: ${detail}`);
    }
    return response.json();
  }

  async function loadLiveSelection() {
    const generation = ++requestGeneration;
    if (activeController) activeController.abort();
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    activeController = controller;
    const timer = controller ? setTimeout(() => controller.abort(), 45000) : null;
    const errors = {};
    const provenance = window.TrendForgeStatusProvenance;
    if (provenance) provenance.begin();
    const renderer = window.TrendForgeProductFixture;
    try {
      if (!renderer || typeof renderer.applyLiveSelection !== "function") {
        throw new Error("Exclusive final-product renderer is unavailable");
      }
      const raw = await fetchJson(SNAPSHOT_URL, controller?.signal);
      if (generation !== requestGeneration) return null;
      if (!window.TrendForgeResearchSnapshot) throw new Error('SNAPSHOT_CONTRACT_UNAVAILABLE');
      const snapshot = window.TrendForgeResearchSnapshot.validate(raw);
      const {attention, evidence, structure, identityPin, caJoin, overlay, namedActivation,
        s3Watch, s4Pack, s5Enrich, s6Resolve, s7State, s8Latest, dataLane, researchQty,
        r16Status, r16Metrics, nativeCore, pipeDefs, mcxMaster, labBundle, openalgoShadow,
        marketWeather, top10Research, evidenceRadar, s4s5Compare} = snapshot.panels;
      for (const [key, status] of Object.entries(snapshot.panelStatus)) {
        if (status.state !== 'READY') errors[key] = status.code;
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
        for (const entry of labBundle?.pipeRuns || []) {
          if (entry.run) window.TrendForgePipeLab.apply(entry.run);
        }
      }
      if (window.TrendForgeMcxMaster) {
        window.TrendForgeMcxMaster.apply(mcxMaster);
      }
      if (window.TrendForgeScannerLab) {
        window.TrendForgeScannerLab.apply({ nativeCore, pipeDefs, bundle: labBundle });
      }
      window.TrendForgeR2BActivation?.apply(namedActivation);
      window.TrendForgeGuidanceOMS?.apply(s7State);
      window.TrendForgeS2MarketWeather?.apply(marketWeather);
      window.TrendForgeTop10Research?.apply(top10Research);
      window.TrendForgeEvidenceRadar?.apply(evidenceRadar);
      window.TrendForgeS4S5Compare?.apply(s4s5Compare);
      if (window.TrendForgeHybridOverlay) {
        window.TrendForgeHybridOverlay.applyCaJoin(caJoin);
        window.TrendForgeHybridOverlay.applyHybridOverlay(overlay);
      }
      markUnavailablePanels(CONTEXT_MOUNTS.map((ids, index) =>
        [ids, [s4Pack, s5Enrich, s6Resolve, nativeCore, mcxMaster, researchQty, openalgoShadow][index]]));
      document.body.dataset.researchSnapshotId = snapshot.snapshotId;
      if (provenance) provenance.accept({attention, evidence, structure, s7State, s8Latest, r16Status, errors,
        snapshotId: snapshot.snapshotId, capturedAt: snapshot.capturedAt, evaluatedAt: snapshot.evaluatedAt});
      window.dispatchEvent(new CustomEvent("trendforge:selection-ready", {
        detail: {
          contract: CONTRACT,
          snapshotId: snapshot.snapshotId,
          snapshotHash: snapshot.snapshotHash,
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
      return { snapshotId: snapshot.snapshotId, attention, evidence, structure, identityPin, caJoin, overlay, namedActivation, s3Watch, s4Pack, s5Enrich, s6Resolve, openalgoShadow, count };
    } catch (error) {
      if (generation !== requestGeneration) return null;
      document.body.dataset.selectionMode = hasSnapshot ? "STALE_RETAINED" : "FIXTURE_FALLBACK";
      if (window.TrendForgeS7State) window.TrendForgeS7State.apply(null);
      if (window.TrendForgeS8Persist) window.TrendForgeS8Persist.apply(null);
      if (window.TrendForgeR16PitValidation) window.TrendForgeR16PitValidation.apply({status: null, metrics: null});
      markUnavailablePanels(CONTEXT_MOUNTS.map(ids => [ids, null]));
      window.TrendForgeR2BActivation?.apply(null);
      window.TrendForgeGuidanceOMS?.apply(null);
      window.TrendForgeS2MarketWeather?.apply(null);
      window.TrendForgeTop10Research?.apply(null);
      window.TrendForgeEvidenceRadar?.apply(null);
      window.TrendForgeS4S5Compare?.apply(null);
      window.TrendForgeScannerLab?.apply({nativeCore: null, pipeDefs: null, bundle: null});
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
    } finally {
      if (timer !== null) clearTimeout(timer);
      if (activeController === controller) activeController = null;
    }
  }

  window.TrendForgeSelectionAdapter = {
    contract: CONTRACT,
    load: loadLiveSelection
  };

  const refresh = document.getElementById("previewRefresh");
  if (refresh) refresh.addEventListener("click", () => { void loadLiveSelection(); });
  // Defer the first request until every deferred panel renderer is registered.
  // A fast localhost response must not arrive before later scripts execute.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { void loadLiveSelection(); }, {once: true});
  } else {
    void loadLiveSelection();
  }
})();
