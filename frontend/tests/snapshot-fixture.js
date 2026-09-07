// Synthetic protocol fixture. Never loaded by the product application.
const {PANEL_KEYS} = require('../research-snapshot.js');
const {createHash} = require('crypto');

function snapshotFixture({generation = 'one', symbol = 'ABC', withStructure = true} = {}) {
  const hash = name => createHash('sha256').update(generation + name).digest('hex');
  const time = '2026-09-04T10:00:00Z', evaluated = '2026-09-07T12:00:00Z';
  const l = {r1BundleId: 'r1-' + generation, r1BundleHash: hash('r1'), r2RunId: 'r2-' + generation,
    r2RunHash: hash('r2'), r4RunHash: hash('r4'), r14RunHash: hash('r14'), r5RunHash: hash('r5')};
  const parents = {r1BundleId: l.r1BundleId, r1BundleHash: l.r1BundleHash,
    r2RunId: l.r2RunId, r2RunHash: l.r2RunHash, r14RunHash: l.r14RunHash};
  const panels = Object.fromEntries(PANEL_KEYS.map(key => [key, null]));
  panels.attention = {schemaVersion: 'trendforge.inventory-discovery.v1', ...parents,
    runId: l.r2RunId, runHash: l.r2RunHash, builtAt: '2026-09-04T12:00:00Z', tradingDate: '2026-09-04',
    universeCount: 1, rows: [{symbol, publicState: 'WATCH', evidenceDirection: 'BULLISH',
      freshness: 'CURRENT', attentionBand: 'WATCH', attentionPriority: 0.4}]};
  panels.evidence = {schemaVersion: 'trendforge.inventory-source-bundle.v1',
    bundleId: l.r1BundleId, bundleHash: l.r1BundleHash, stockRecords: [], sourceRecords: []};
  if (withStructure) {
    panels.identityPin = {...parents, runHash: l.r4RunHash};
    panels.caJoin = {...parents, runHash: l.r14RunHash, r4RunHash: l.r4RunHash, rows: []};
    panels.structure = {schemaVersion: 'trendforge.structure-batch.v2', ...parents,
      runId: 'r5-' + generation, runHash: l.r5RunHash, decisionAt: time, rows: [], waitCount: 1, rejectCount: 0};
    panels.s3Watch = {sourceRunId: 's3-' + generation, rows: []};
    panels.s4Pack = {schemaVersion: 'trendforge.s4-structure-pack.v1', ...parents,
      runId: 's4-' + generation, runHash: hash('s4'), rows: []};
    panels.s6Resolve = {...parents, runId: 's6-' + generation, runHash: hash('s6'), rows: []};
    panels.s7State = {...parents, runId: 's7-' + generation, runHash: hash('s7'),
      s6RunHash: hash('s6'), tradabilityRunHash: hash('tradability'), rows: [], sourceActivationReady: false};
    panels.nativeCore = {runHash: hash('native'), r5RunHash: l.r5RunHash, r14RunHash: l.r14RunHash, rows: []};
    panels.s8Latest = {schemaVersion: 'trendforge.s8-scan.v1', runId: 's8-' + generation,
      asOf: evaluated, builtAt: evaluated, persisted: false, rows: [], lineage: {
        r1RunHash: l.r1BundleHash, r2RunHash: l.r2RunHash, r14RunHash: l.r14RunHash, r5RunHash: l.r5RunHash,
        s3RunId: panels.s3Watch.sourceRunId, s4PackId: panels.s4Pack.runId, s6RunId: panels.s6Resolve.runId,
        s7RunId: panels.s7State.runId, nativeGuidanceRunHash: panels.nativeCore.runHash,
        tradabilityRunHash: panels.s7State.tradabilityRunHash,
      }};
  }
  return {schemaVersion: 'trendforge.research-snapshot.v1', snapshotHash: hash('envelope'),
    snapshotId: 'rs-' + hash('envelope'), coherence: 'SQLITE_READ_TRANSACTION',
    capturedAt: evaluated, evaluatedAt: evaluated, decisionAt: time, executable: false,
    assemblyCount: withStructure ? 1 : 0, lineage: l, panels,
    panelStatus: Object.fromEntries(PANEL_KEYS.map(key => [key, panels[key] ?
      {state: 'READY', code: null, scope: 'RESEARCH'} :
      {state: 'UNAVAILABLE', code: 'WAIT_SYNTHETIC_OPTIONAL', scope: 'RESEARCH'}]))};
}

function unavailable(bundle, key, code = 'WAIT_INPUT') {
  bundle.panels[key] = null;
  bundle.panelStatus[key] = {state: 'UNAVAILABLE', code, scope: 'RESEARCH'};
}
module.exports = {snapshotFixture, unavailable};
