const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const {validate, PANEL_KEYS} = require('../research-snapshot.js');
const {snapshotFixture, unavailable} = require('./snapshot-fixture.js');
const root = path.resolve(__dirname, '..');

assert.equal(PANEL_KEYS.length, 26, 'all original panels and four dependent rooms are retained');
const valid = snapshotFixture();
assert.strictEqual(validate(valid), valid);
for (const mutate of [
  x => delete x.panelStatus.s7State,
  x => { x.snapshotId = 'other'; },
  x => { x.capturedAt = '2026-09-07T12:00:00'; },
  x => { x.panels.s7State.r2RunHash = 'other'; },
  x => { x.panels.s8Latest.lineage.s6RunId = 'other'; },
  x => { x.panels.nativeCore.r5RunHash = 'other'; },
  x => { x.panels.s8Latest.persisted = true; },
  x => { x.panelStatus.s5Enrich.state = 'READY'; },
  x => { x.evaluatedAt = '2026-09-08T12:00:00Z'; },
  x => { delete x.panels.s4Pack.schemaVersion; },
  x => { x.panels.evidence.schemaVersion = 'unsupported'; },
]) {
  const value = snapshotFixture(); mutate(value);
  assert.throws(() => validate(value));
}
const partial = snapshotFixture();
unavailable(partial, 's5Enrich', 'WAIT_OPTIONAL');
assert.strictEqual(validate(partial), partial);

const waiting = [], applied = [], events = [], alerts = [];
const sandbox = {
  console, Date, Promise, AbortController, setTimeout, clearTimeout,
  CustomEvent: function(type, init) {this.type = type; this.detail = init.detail;},
  document: {body: {dataset: {}}, getElementById() {return null;}},
  window: {dispatchEvent(event) {events.push(event);}, TrendForgeProductFixture: {
    applyLiveSelection(a) {applied.push(a.runId); return a.rows.length;},
    setSelectionAdapterStatus(message) {alerts.push(message);}
  }},
  fetch: (url, options) => new Promise(resolve => {
    assert.equal(url, '/api/v1/selection/snapshot');
    assert.equal(options.cache, 'no-store');
    waiting.push({resolve, options});
  })
};
vm.createContext(sandbox);
for (const name of ['research-snapshot.js', 'selection-live-adapter.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, name), 'utf8'), sandbox);
}
const response = payload => ({ok: true, status: 200, json: async () => payload});
const flush = () => new Promise(resolve => setImmediate(resolve));

async function verifyDeferredBootstrap() {
  let onReady = null, requests = 0, renders = 0;
  const boot = {
    console, Promise, Date, setTimeout, clearTimeout,
    CustomEvent: function(type, init) {this.type = type; this.detail = init.detail;},
    document: {readyState: 'loading', body: {dataset: {}}, getElementById() {return null;},
      addEventListener(name, fn, options) {
        assert.equal(name, 'DOMContentLoaded'); assert(options.once); onReady = fn;
      }},
    window: {dispatchEvent() {}},
    fetch: async url => {
      requests++; assert.equal(url, '/api/v1/selection/snapshot');
      return response(snapshotFixture());
    },
  };
  vm.createContext(boot);
  for (const file of ['research-snapshot.js', 'selection-live-adapter.js']) {
    vm.runInContext(fs.readFileSync(path.join(root, file), 'utf8'), boot);
  }
  assert.equal(requests, 0, 'no request before deferred scripts finish');
  boot.window.TrendForgeProductFixture = {applyLiveSelection() {renders++; return 1;}};
  onReady(); await flush(); await flush();
  assert.equal(requests, 1); assert.equal(renders, 1);
}

function verifyLocalContextControls() {
  const elements = Object.fromEntries([
    's4s5With', 's4s5Without', 's4s5Both', 's4s5CompareList',
    's4s5CompareCounts', 's4s5CompareMeta', 's4s5FormulaStrip',
  ].map(id => [id, {id, checked: false, innerHTML: '', textContent: '',
    addEventListener(_name, fn) {this.change = fn;}}]));
  let networkCalls = 0;
  const ui = {console, localStorage: {getItem() {return null;}, setItem() {}},
    document: {readyState: 'complete', getElementById(id) {return elements[id] || null;}},
    window: {TrendForgeResearchSnapshot: {}, addEventListener() {}},
    fetch: async () => {networkCalls++; throw new Error('Independent fetch forbidden');},
  };
  vm.createContext(ui);
  vm.runInContext(fs.readFileSync(path.join(root, 's4s5-compare.js'), 'utf8'), ui);
  const result = {pHat: null, pMin: null, wouldPassPMin: false};
  ui.window.TrendForgeS4S5Compare.apply({rows: [{symbol: 'SYNTHETIC', withS4S5: result, withoutS4S5: result}]});
  assert(elements.s4s5CompareList.innerHTML.includes('WITH original'));
  elements.s4s5With.checked = false;
  elements.s4s5With.change({target: elements.s4s5With});
  assert(!elements.s4s5CompareList.innerHTML.includes('WITH original'));
  assert(elements.s4s5CompareList.innerHTML.includes('WITHOUT split'));
  assert.equal(networkCalls, 0, 'compare filter redraws the pinned bundle locally');
  ui.window.TrendForgeS4S5Compare.apply(null);
  assert.equal(elements.s4s5CompareCounts.textContent, '');
  assert.equal(elements.s4s5CompareList.textContent, 'WAIT_SNAPSHOT_COMPARE');

  let paints = 0;
  const host = {dataset: {}, replaceChildren() {paints++;}};
  const weather = {
    console, setTimeout, CustomEvent: function() {},
    document: {
      createElement() {return {appendChild() {}};},
      getElementById(id) {return id === 'toolContent' ? host : null;},
      querySelector() {return {getAttribute() {return 'index_dashboard';}};},
      addEventListener() {},
    },
    window: {TrendForgeResearchSnapshot: {}, addEventListener() {}, dispatchEvent() {}},
    fetch: ui.fetch,
  };
  vm.createContext(weather);
  vm.runInContext(fs.readFileSync(path.join(root, 's2-market-weather.js'), 'utf8'), weather);
  weather.window.TrendForgeS2MarketWeather.apply({regimeLabel: 'ONE'});
  weather.window.TrendForgeS2MarketWeather.apply({regimeLabel: 'TWO'});
  assert.equal(paints, 2, 'an already open weather room updates to the new bundle');
  weather.window.TrendForgeS2MarketWeather.apply(null);
  assert.equal(paints, 3, 'unavailable weather clears the prior room');
  assert.equal(networkCalls, 0);
}

(async () => {
  await verifyDeferredBootstrap();
  verifyLocalContextControls();
  assert.equal(waiting.length, 1, 'page load must issue one request, not 22');
  const next = sandbox.window.TrendForgeSelectionAdapter.load();
  assert.equal(waiting.length, 2, 'one further request for one explicit refresh');
  assert(waiting[0].options.signal.aborted, 'superseded network request is cancelled');
  const newer = snapshotFixture({generation: 'new'});
  waiting[1].resolve(response(newer));
  await next;
  waiting[0].resolve(response(snapshotFixture({generation: 'old'})));
  await flush(); await flush();
  assert.deepStrictEqual(applied, ['r2-new'], 'late older response cannot overwrite current display');
  assert.equal(sandbox.document.body.dataset.researchSnapshotId, newer.snapshotId);
  assert.equal(events.filter(e => e.type === 'trendforge:selection-ready').length, 1);
  assert.equal(events[0].detail.snapshotId, newer.snapshotId);

  const broken = sandbox.window.TrendForgeSelectionAdapter.load();
  const mixed = snapshotFixture({generation: 'mixed'});
  mixed.panels.s7State.s6RunHash = 'other';
  waiting[2].resolve(response(mixed)); await broken;
  assert.deepStrictEqual(applied, ['r2-new'], 'invalid complete envelope rejected before any core renderer');
  assert.equal(sandbox.document.body.dataset.selectionMode, 'STALE_RETAINED');
  assert(alerts.some(message => message.includes('S7_LINEAGE')));

  const recovery = sandbox.window.TrendForgeSelectionAdapter.load();
  waiting[3].resolve(response(snapshotFixture({generation: 'recovery'}))); await recovery;
  assert.deepStrictEqual(applied, ['r2-new', 'r2-recovery']);
  assert.equal(waiting.length, 4, 'errors never trigger fallback to independent latest endpoints');
  console.log('Atomic snapshot: 11 rejection cases, deferred bootstrap, local context controls, single fetch, cancellation, race, stale handling and recovery passed.');
})().catch(error => {console.error(error); process.exitCode = 1;});