/* Research envelope validation only; never a strategy or activation owner. */
((root) => {
  'use strict';
  const SCHEMA = 'trendforge.research-snapshot.v1';
  const PANEL_KEYS = Object.freeze([
    'attention', 'evidence', 'structure', 'identityPin', 'caJoin', 'overlay',
    'namedActivation', 's3Watch', 's4Pack', 's5Enrich', 's6Resolve', 's7State',
    's8Latest', 'dataLane', 'researchQty', 'r16Status', 'r16Metrics',
    'nativeCore', 'pipeDefs', 'mcxMaster', 'labBundle', 'openalgoShadow',
    'marketWeather', 'top10Research', 'evidenceRadar', 's4s5Compare'
  ]);
  const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  const sameKeys = value => object(value) && Object.keys(value).length === PANEL_KEYS.length &&
    PANEL_KEYS.every(key => Object.prototype.hasOwnProperty.call(value, key));
  const timestamp = value => typeof value === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value));

  function validate(bundle) {
    if (!object(bundle) || bundle.schemaVersion !== SCHEMA ||
        bundle.coherence !== 'SQLITE_READ_TRANSACTION' || bundle.executable !== false ||
        !/^[a-f0-9]{64}$/.test(bundle.snapshotHash || '') || bundle.snapshotId !== 'rs-' + bundle.snapshotHash ||
        !timestamp(bundle.capturedAt) || !timestamp(bundle.decisionAt) || !timestamp(bundle.evaluatedAt) ||
        Date.parse(bundle.capturedAt) !== Date.parse(bundle.evaluatedAt) ||
        ![0, 1].includes(bundle.assemblyCount) || !object(bundle.lineage) ||
        !sameKeys(bundle.panels) || !sameKeys(bundle.panelStatus)) {
      throw new Error('SNAPSHOT_ENVELOPE_INVALID');
    }
    const p = bundle.panels, l = bundle.lineage;
    // Validate the schemas consumed by the primary renderer before it can
    // replace any current rows. A malformed S4 must not leave a partial paint.
    for (const [key, schemas] of Object.entries({
      attention: ['trendforge.inventory-discovery.v1'],
      evidence: ['trendforge.inventory-source-bundle.v1'],
      structure: ['trendforge.structure-batch.v1', 'trendforge.structure-batch.v2'],
      s4Pack: ['trendforge.s4-structure-pack.v1'],
    })) {
      if (p[key] !== null && !schemas.includes(p[key]?.schemaVersion)) {
        throw new Error('SNAPSHOT_PANEL_SCHEMA_INVALID: ' + key);
      }
    }
    for (const key of PANEL_KEYS) {
      const status = bundle.panelStatus[key];
      if (!object(status) || !['RESEARCH', 'CONTEXT', 'CONTROL_OBSERVATION', 'VALIDATION'].includes(status.scope) ||
          (status.state === 'READY' ? !object(p[key]) :
            status.state !== 'UNAVAILABLE' || p[key] !== null || typeof status.code !== 'string' || !status.code)) {
        throw new Error('SNAPSHOT_PANEL_STATUS_INVALID: ' + key);
      }
    }
    function match(value, expected, code = 'SNAPSHOT_PANEL_LINEAGE_MISMATCH') {
      if (!object(value) || Object.entries(expected).some(([key, other]) => other == null || value[key] !== other)) {
        throw new Error(code);
      }
    }
    match(p.evidence, {bundleId: l.r1BundleId, bundleHash: l.r1BundleHash});
    match(p.attention, {runId: l.r2RunId, runHash: l.r2RunHash, r1BundleId: l.r1BundleId, r1BundleHash: l.r1BundleHash});
    const parents = {r1BundleHash: l.r1BundleHash, r2RunHash: l.r2RunHash};
    for (const [key, own] of [['identityPin', 'r4RunHash'], ['caJoin', 'r14RunHash'], ['structure', 'r5RunHash']]) {
      if (p[key]) match(p[key], {...parents, runHash: l[own]});
    }
    if (p.caJoin) match(p.caJoin, {r4RunHash: l.r4RunHash});
    for (const key of ['structure', 's4Pack', 's5Enrich', 's6Resolve']) {
      if (p[key]) match(p[key], {...parents, r14RunHash: l.r14RunHash});
    }
    if (p.s7State) match(p.s7State, {r2RunHash: l.r2RunHash, r14RunHash: l.r14RunHash,
      s6RunHash: p.s6Resolve?.runHash}, 'S7_LINEAGE_MISMATCH_OR_MISSING');
    if (p.nativeCore) match(p.nativeCore, {r5RunHash: l.r5RunHash, r14RunHash: l.r14RunHash});
    if (p.s8Latest) {
      match(p.s8Latest.lineage, {
        r1RunHash: l.r1BundleHash, r2RunHash: l.r2RunHash, r14RunHash: l.r14RunHash, r5RunHash: l.r5RunHash,
        s3RunId: p.s3Watch?.sourceRunId, s4PackId: p.s4Pack?.runId, s6RunId: p.s6Resolve?.runId,
        s7RunId: p.s7State?.runId, nativeGuidanceRunHash: p.nativeCore?.runHash,
        tradabilityRunHash: p.s7State?.tradabilityRunHash,
      }, 'S8_LINEAGE_MISMATCH_OR_MISSING');
      if (p.s8Latest.persisted !== false) throw new Error('SNAPSHOT_MUST_NOT_CLAIM_S8_PERSISTED');
    }
    if (p.namedActivation) match(p.namedActivation, parents);
    if (p.labBundle?.nativeCore) {
      match(p.labBundle.nativeCore, {runHash: p.nativeCore?.runHash});
      for (const entry of p.labBundle.pipeRuns || []) {
        if (entry.run) match(entry.run, {nativeCoreRunHash: p.nativeCore?.runHash, s7RunHash: p.s7State?.runHash});
      }
    }
    // The server verifies its checksum. This client validates identity and
    // cross-panel references; it does not claim to recompute Python JSON hashes.
    return bundle;
  }
  const api = Object.freeze({SCHEMA, PANEL_KEYS, validate, ownsSelection: true});
  root.TrendForgeResearchSnapshot = api;
  if (typeof module === 'object' && module.exports) module.exports = api;
})(typeof window === 'object' ? window : globalThis);
