const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const script = fs.readFileSync(path.join(__dirname, '../scan-history.js'), 'utf8');
const elements = new Map();
const node = id => {
  if (!elements.has(id)) elements.set(id, {innerHTML: '', disabled: false, value: '', addEventListener() {}});
  return elements.get(id);
};
let responder;
const requests = [];
const context = {
  window: {TrendForgeProductFixture: {applyLiveSelection() {throw Error('History changed current selection');}}},
  document: {getElementById: node}, console, AbortController, setTimeout, clearTimeout,
  fetch: async (url, options) => {
    requests.push({url, options});
    return responder(url, options);
  }
};
vm.createContext(context);
vm.runInContext(script, context);
const history = context.window.TrendForgeScanHistory;
const ok = payload => ({ok: true, json: async () => payload});
const batch = id => ({schemaVersion: 'trendforge.s8-scan.v1', runId: id,
  asOf: '2026-09-04T10:00:00Z', tradingDate: '2026-09-04', builtAt: '2026-09-04T11:00:00Z',
  rows: [{symbol: '<script>bad</script>', publicState: 'WAIT', evidenceDirection: 'BULLISH'}], lineage: {r2RunHash: 'prior'}});

(async () => {
  responder = () => ok({runs: []});
  await history.load();
  assert(node('historyRunSelect').disabled);
  assert(node('historySnapshot').innerHTML.includes('No saved S8 scans'));
  responder = () => ok({runs: [{runId: 'saved/a', asOf: '2026-09-04T10:00:00Z'}]});
  await history.load();
  assert(!node('historyRunSelect').disabled);
  responder = () => ok(batch('saved/a'));
  await history.select('saved/a');
  assert(requests.at(-1).url.endsWith('saved%2Fa'));
  assert(node('historySnapshot').innerHTML.includes('HISTORICAL SNAPSHOT - NOT CURRENT'));
  assert(!node('historySnapshot').innerHTML.includes('<script>'));
  assert(node('historySnapshot').innerHTML.includes('&lt;script&gt;'));
  responder = () => ok(batch('wrong-id'));
  await history.select('saved/a');
  assert(node('historySnapshot').innerHTML.includes('HISTORY_SCHEMA_OR_ID_MISMATCH'));
  responder = () => ({ok: false, status: 404});
  await history.select('deleted');
  assert(node('historySnapshot').innerHTML.includes('HTTP 404'));
  responder = () => ok({runs: 'not-an-array'});
  await history.load();
  assert(node('historySnapshot').innerHTML.includes('HISTORY_LIST_SCHEMA_MISMATCH'));
  let finishOld;
  responder = url => url.endsWith('/old') ? new Promise(resolve => {finishOld = resolve;}) : ok(batch('new'));
  const oldRequest = history.select('old');
  await history.select('new');
  finishOld(ok(batch('old')));
  await oldRequest;
  assert(node('historySnapshot').innerHTML.includes('<code>new</code>'));
  assert(!node('historySnapshot').innerHTML.includes('<code>old</code>'));
  for (const request of requests) {
    assert(!request.options.method || request.options.method === 'GET');
    assert(!request.url.includes('/latest'), 'history must not call the build-on-read latest endpoint');
    assert(request.url.startsWith('/api/v1/selection/scans'));
  }
  console.log('Saved history: read-only, empty, error, schema, identity, XSS and race checks passed.');
})().catch(error => {console.error(error); process.exitCode = 1;});