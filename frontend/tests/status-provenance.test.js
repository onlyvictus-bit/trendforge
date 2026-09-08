const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const root = path.resolve(__dirname, '..');
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    textContent: '', innerHTML: '', value: '', dataset: {},
    setAttribute() {}, classList: { add() {}, remove() {} }
  });
  return elements.get(id);
}
const sandbox = {
  window: {}, Date, console,
  document: { getElementById: element, body: { dataset: {} } }
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(root, 'status-provenance.js'), 'utf8'), sandbox);
const status = sandbox.window.TrendForgeStatusProvenance;
const batch = {
  attention: {
    schemaVersion: 'trendforge.inventory-discovery.v1', runId: 'r2-a', runHash: 'a',
    r1BundleHash: 'b', tradingDate: '2026-09-04', builtAt: '2026-09-04T12:00:00Z',
    rows: [{symbol: 'ABC', freshness: 'CURRENT', evidenceDirection: 'BULLISH'}]
  },
  evidence: {bundleHash: 'b'},
  structure: {decisionAt: '2026-09-04T10:00:00Z'},
  s7State: {r2RunHash: 'a', sourceActivationReady: false},
  r16Status: {validationStatus: 'PIT_NOT_APPROVED'}, errors: {}
};
assert.equal(status.inspect().mode, 'FIXTURE');
status.begin();
assert.equal(status.inspect().mode, 'LOADING');
status.accept(batch, '2026-09-07T12:00:00Z');
assert.equal(status.inspect().mode, 'SNAPSHOT');
assert.equal(element('snapshotReceivedAt').textContent, '2026-09-07T12:00:00Z');
assert.equal(element('snapshotAsOf').textContent, '2026-09-04T10:00:00Z');
assert(element('snapshotFreshness').textContent.includes('at snapshot creation'));
assert(element('capabilityStatusBody').innerHTML.includes('NOT MEASURED BY THIS PAGE'));
assert(element('capabilityStatusBody').innerHTML.includes('SEPARATE CONTROLS'));
assert.equal(element('sourceActivationStatus').textContent, 'Activation: LOCKED (snapshot)');
status.setView('history');
assert(element('viewProvenance').textContent.includes('HISTORICAL'));
status.setView('tool', 'm_factor_history');
assert(element('viewProvenance').textContent.includes('FIXTURE HISTORY'));
status.setView('all-stocks');
assert(element('viewProvenance').textContent.includes('STORED RESEARCH SNAPSHOT'));
assert.equal(status.inspect().runId, 'r2-a');
status.begin();
assert.equal(status.inspect().mode, 'LOADING');
status.fail('HTTP 503');
assert.equal(status.inspect().mode, 'STALE');
assert.equal(element('snapshotAsOf').textContent, '2026-09-04T10:00:00Z');
assert.equal(element('sourceActivationStatus').textContent, 'Activation: UNKNOWN');
assert(element('capabilityStatusBody').innerHTML.includes('UNKNOWN'));
status.accept({...batch, s7State: null, errors: {'/s7': 'HTTP 503'}});
assert.equal(element('sourceActivationStatus').textContent, 'Activation: UNKNOWN');
assert(element('snapshotFailures').innerHTML.includes('HTTP 503'));
status.accept({...batch, s7State: {r2RunHash: 'other', sourceActivationReady: true}});
assert.equal(element('sourceActivationStatus').textContent, 'Activation: UNKNOWN');
assert(element('snapshotFailures').innerHTML.includes('LINEAGE_MISMATCH'));
status.governance(null);
assert(element('capabilityStatusBody').innerHTML.includes('UNKNOWN'));
status.governance({modelState: 'MODEL_NOT_APPROVED'});
assert(element('capabilityStatusBody').innerHTML.includes('MODEL_NOT_APPROVED'));
status.accept({...batch, errors: {'/unsafe': '<img onerror=alert(1)>'}});
assert(!element('snapshotFailures').innerHTML.includes('<img'));
assert(element('snapshotFailures').innerHTML.includes('&lt;img'));
assert.equal(JSON.stringify(batch.attention.rows), JSON.stringify([
  {symbol: 'ABC', freshness: 'CURRENT', evidenceDirection: 'BULLISH'}
]));
const fixture = fs.readFileSync(path.join(root, 'product-fixture.js'), 'utf8');
assert(fixture.includes('trendforge.structure-batch.v2'), 'current R5 v2 must not force fixture fallback');
assert(fixture.includes("go('history')"), 'header history must open saved scans, not examples');
console.log('Status provenance: snapshot, history, stale, lineage, unknown and escaping checks passed.');