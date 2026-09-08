const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const root = path.resolve(__dirname, '..');
const elements = new Map();
function node(id) {
  if (!elements.has(id)) elements.set(id, {innerHTML: '', textContent: '', open: false,
    addEventListener() {}, insertAdjacentHTML(_position, html) {this.innerHTML += html;}});
  return elements.get(id);
}
const sandbox = {window: {}, console, setTimeout, clearTimeout,
  document: {getElementById: node}, fetch: async () => ({ok: false, status: 503})};
vm.createContext(sandbox);
for (const file of ['r16-pit-validation.js', 'r18-model-governance.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), sandbox);
}
const pit = sandbox.window.TrendForgeR16PitValidation;
pit.apply({status: null, metrics: null});
assert(node('q5ValidationLock').textContent.includes('UNKNOWN'), 'an unreadable PIT status is UNKNOWN');
assert(!node('q5ValidationLock').textContent.includes('PIT_NOT_APPROVED'), 'do not fabricate a rejection');
pit.apply({status: {validationStatus: 'PIT_NOT_APPROVED', datasetStatus: 'BUILDING'}, metrics: {
  metrics: [{direction: 'BULLISH', horizonSessions: 5, averageNetR: null, censorRate: null}]
}});
assert(node('q5ValidationLock').innerHTML.includes('PIT_NOT_APPROVED'), 'preserve observed backend result');
assert(node('s9PitHomeworkPanel').innerHTML.includes('Average net R<strong>UNAVAILABLE'));
assert(node('s9PitHomeworkPanel').innerHTML.includes('Censored<strong>UNAVAILABLE'));
pit.apply({status: {validationStatus: 'PIT_NOT_APPROVED', datasetStatus: 'BUILDING'}, metrics: {
  metrics: [{direction: 'BULLISH', averageNetR: 0, censorRate: 0}]
}});
assert(node('s9PitHomeworkPanel').innerHTML.includes('Average net R<strong>0.00'));
assert(node('s9PitHomeworkPanel').innerHTML.includes('Censored<strong>0.0%'));
sandbox.window.TrendForgeR18ModelGovernance.render({});
assert(node('r18ModelGovernancePanel').innerHTML.includes('Drift events <strong>UNKNOWN'));
assert(node('r18ModelGovernancePanel').innerHTML.includes('Rollbacks <strong>UNKNOWN'));
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
assert(html.includes('<strong>Fixture examples</strong>'), 'old lightning examples must not look live');
assert(html.includes('R1/R2 attention ceiling: WATCH / WAIT / REJECT'), 'R2 ceiling must not masquerade as the S7 state');
console.log('Readiness fallback: absent approval, null historical metrics and fixture-header labelling passed.');