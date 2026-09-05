(() => {
  "use strict";

  const CONTRACT = "trendforge.selection-live-adapter.v1";
  let requestGeneration = 0;

  async function fetchJson(path) {
    const response = await fetch(path, { cache: "no-store", headers: { Accept: "application/json" } });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const payload = await response.json();
        detail = payload?.detail?.code || payload?.detail?.message || detail;
      } catch (_error) {
        // The status remains sufficient; HTML or malformed error bodies are not data.
      }
      throw new Error(`${path}: ${detail}`);
    }
    return response.json();
  }

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

  async function loadLiveSelection() {
    const generation = ++requestGeneration;
    const renderer = window.TrendForgeProductFixture;
    if (!renderer || typeof renderer.applyLiveSelection !== "function") {
      throw new Error("Exclusive final-product renderer is unavailable");
    }
    try {
      const [attention, evidence, structure, identityPin, caJoin, overlay, namedActivation, s3Watch, s4Pack, s5Enrich, s6Resolve, s7State, s8Latest, dataLane, researchQty, r16Status, r16Metrics, nativeCore, pipeDefs, mcxMaster, labBundle, openalgoShadow] = await Promise.all([
        fetchJson("/api/v1/selection/attention"),
        fetchJson("/api/v1/selection/evidence"),
        fetchOptionalJson("/api/v1/selection/structure"),
        fetchOptionalJson("/api/v1/selection/identity-pin"),
        fetchOptionalJson("/api/v1/selection/ca-join").catch(() => null),
        fetchOptionalJson("/api/v1/hybrid-v2/overlay?limit=40").catch(() => null),
        fetchOptionalJson("/api/v1/selection/named-activation").catch(() => null),
        fetchOptionalJson("/api/v1/selection/cheap-discovery/watch?limit=50").catch(() => null),
        fetchOptionalJson("/api/v1/selection/s4-structure").catch(() => null),
        fetchOptionalJson("/api/v1/selection/s5-enrichment").catch(() => null),
        fetchOptionalJson("/api/v1/selection/s6-resolution").catch(() => null),
        fetchOptionalJson("/api/v1/selection/s7-state").catch(() => null),
        fetchOptionalJson("/api/v1/selection/scans/latest").catch(() => null),
        fetchOptionalJson("/api/v1/settings/data-lane").catch(() => null),
        fetchOptionalJson("/api/v1/selection/research-quantity").catch(() => null),
        fetchOptionalJson("/api/v1/selection/pit/status").catch(() => null),
        fetchOptionalJson("/api/v1/selection/pit/metrics").catch(() => null),
        fetchOptionalJson("/api/v1/scanners/native-core").catch(() => null),
        fetchOptionalJson("/api/v1/pipes/definitions").catch(() => null),
        fetchOptionalJson("/api/v1/selection/mcx-master").catch(() => null),
        fetchOptionalJson("/api/v1/scanners/lab-bundle").catch(() => null),
        fetchOptionalJson("/api/v1/integrations/openalgo/shadow").catch(() => null)
      ]);
      if (generation !== requestGeneration) return null;
      const count = renderer.applyLiveSelection(attention, evidence, structure, s4Pack);
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
      return { attention, evidence, structure, identityPin, caJoin, overlay, namedActivation, s3Watch, s4Pack, s5Enrich, s6Resolve, openalgoShadow, count };
    } catch (error) {
      if (generation !== requestGeneration) return null;
      document.body.dataset.selectionMode = "FIXTURE_FALLBACK";
      if (typeof renderer.setSelectionAdapterStatus === "function") {
        renderer.setSelectionAdapterStatus(
          `Live R1/R2 unavailable: ${error.message}. Fixture rows remain explicitly non-live.`
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
