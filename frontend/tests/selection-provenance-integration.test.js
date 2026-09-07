const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.resolve(__dirname, '..');
const elements = new Map();
const node = id => {
  if (!elements.has(id)) elements.set(id, {textContent: '', innerHTML: '', dataset: {},
    addEventListener() {}, classList: {add() {}, remove() {}}});
  return elements.get(id);
};
let failCore = false;
let failS7 = false;
let mismatch = false;
const {snapshotFixture, unavailable} = require('./snapshot-fixture.js');
const base = snapshotFixture();
const a = base.panels.attention;
const sandbox = {
  console, Date, Promise, setTimeout, clearTimeout,
  CustomEvent: function(type, init) {this.type = type; this.detail = init.detail;},
  document: {getElementById: node, body: {dataset: {}}},
  window: {dispatchEvent() {}, TrendForgeProductFixture: {
    applyLiveSelection() {return 0;}, setSelectionAdapterStatus() {}
  }},
  fetch: async url => {
    assert.equal(url, '/api/v1/selection/snapshot');
    if (failCore) return {ok: false, status: 503, json: async () => ({detail: {code: 'WAIT_INPUT'}})};
    const payload = snapshotFixture();
    if (failS7) { unavailable(payload, 's7State'); unavailable(payload, 's8Latest'); }
    if (mismatch) payload.panels.s7State.r2RunHash = 'other';
    return {ok: true, json: async () => payload};
  }
};
vm.createContext(sandbox);
for (const file of ['research-snapshot.js', 'status-provenance.js', 's7-state.js', 's8-persist.js', 'r16-pit-validation.js', 'selection-live-adapter.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), sandbox);
}
(async () => {
  await new Promise(resolve => setImmediate(resolve));
  await new Promise(resolve => setImmediate(resolve));
  const adapter = sandbox.window.TrendForgeSelectionAdapter;
  const provenance = sandbox.window.TrendForgeStatusProvenance;
  assert.equal(provenance.inspect().mode, 'SNAPSHOT');
  failS7 = true;
  await adapter.load();
  assert(node('s7StatePanel').innerHTML.includes('S7 UNAVAILABLE'));
  assert.equal(node('confirmedModeChip').textContent, 'CONFIRMED STATUS UNAVAILABLE');
  assert(node('snapshotFailures').innerHTML.includes('WAIT_INPUT'));
  failS7 = false; mismatch = true;
  await adapter.load();
  assert(node('s7StatePanel').innerHTML.includes('S7 UNAVAILABLE'));
  assert(node('snapshotFailures').innerHTML.includes('S7_LINEAGE_MISMATCH_OR_MISSING'));
  sandbox.window.TrendForgeR16PitValidation.apply({status: {validationStatus: "PIT_APPROVED", datasetStatus: "READY"}});
  failCore = true;
  await adapter.load();
  assert.equal(sandbox.document.body.dataset.selectionMode, 'STALE_RETAINED');
  assert.equal(provenance.inspect().mode, 'STALE');
  assert(node('q5ValidationLock').textContent.includes('PIT STATUS UNKNOWN'));
  assert(node('s8HistoryPanel').innerHTML.includes('previous metadata cleared'));
  assert.equal(node('snapshotAsOf').textContent, base.panels.structure.decisionAt);
  failCore = false; mismatch = false;
  await adapter.load();
  assert.equal(provenance.inspect().mode, 'SNAPSHOT');
  console.log('Adapter integration: failed optional responses, lineage mismatch, stale retention and recovery passed.');
})().catch(error => {console.error(error); process.exitCode = 1;});