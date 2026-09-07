const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..");
const {snapshotFixture} = require("./snapshot-fixture.js");
const index = fs.readFileSync(path.join(root, "index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "app.js"), "utf8");
const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
const fixture = fs.readFileSync(path.join(root, "product-fixture.js"), "utf8");

const fixtureIndex = index.indexOf("product-fixture.js");
const adapterIndex = index.indexOf("selection-live-adapter.js");
const appIndex = index.indexOf("app.js");
assert(fixtureIndex >= 0 && adapterIndex > fixtureIndex && appIndex > adapterIndex,
  "product renderer, R1/R2 adapter and legacy app must load in ownership order");

assert(adapter.includes("attention"), "adapter must load persisted R2 attention");
assert(adapter.includes("evidence"), "adapter must load persisted R1 evidence");
assert(adapter.includes("structure"), "adapter must optionally load persisted R5 structure");
assert(adapter.includes("identityPin"), "adapter must optionally load persisted R4 identity pin");
assert(adapter.includes("s3Watch"), "adapter must optionally load S3 watch queue");
assert(!adapter.includes("/api/radar"), "adapter must not use the legacy radar");
assert(!adapter.includes("/api/v1/selection/live"), "adapter must not use the legacy live projection");
assert(fixture.includes("trendforge.inventory-source-bundle.v1"), "renderer must validate the R1 schema");
assert(fixture.includes("trendforge.inventory-discovery.v1"), "renderer must validate the R2 schema");
assert(fixture.includes("NOT AVAILABLE UNTIL R5") || fixture.includes("NONE — R5 research, not a trade"), "live UI must not invent trade geometry");
assert(app.includes('productOwnsSelection ? Promise.resolve(null) : fetchJson("/api/radar")'),
  "legacy radar must be disabled when the product renderer owns selection");
assert(app.includes('productOwnsSelection ? Promise.resolve(null) : fetchOptionalJson("/api/v1/selection/live")'),
  "legacy live projection must be disabled when the product renderer owns selection");

async function executeAdapter(responses) {
  const events = [];
  const statuses = [];
  let applied = null;
  const body = { dataset: {} };
  const refresh = { addEventListener() {} };
  const renderer = {
    applyLiveSelection(attention, evidence, structure) {
      applied = { attention, evidence, structure };
      return attention.rows.length;
    },
    setSelectionAdapterStatus(message) { statuses.push(message); }
  };
  const sandbox = {
    console,
    Promise,
    Error,
    CustomEvent: function CustomEvent(type, init) { this.type = type; this.detail = init.detail; },
    document: {
      body,
      getElementById(id) { return id === "previewRefresh" ? refresh : null; }
    },
    window: {
      TrendForgeProductFixture: renderer,
      dispatchEvent(event) { events.push(event); }
    },
    fetch: async (url) => {
      const response = responses[url];
      if (!response) throw new Error(`unexpected URL ${url}`);
      return {
        ok: response.ok,
        status: response.status,
        async json() { return response.payload; }
      };
    },
    setTimeout,
    clearTimeout
  };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(root, "research-snapshot.js"), "utf8"), sandbox);
  vm.runInContext(adapter, sandbox);
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));
  return { events, statuses, applied, body };
}

(async () => {
  const core = snapshotFixture({withStructure: false});
  const success = await executeAdapter({
    '/api/v1/selection/snapshot': {ok: true, status: 200, payload: core}
  });
  assert.strictEqual(success.applied.attention, core.panels.attention);
  assert.strictEqual(success.applied.evidence, core.panels.evidence);
  assert.strictEqual(success.applied.structure, null);
  const complete = snapshotFixture();
  const withR5 = await executeAdapter({
    '/api/v1/selection/snapshot': {ok: true, status: 200, payload: complete}
  });
  assert.strictEqual(withR5.applied.structure, complete.panels.structure);
  assert(success.events.some(event => event.type === 'trendforge:selection-ready'));
  assert.strictEqual(success.body.dataset.researchSnapshotId, core.snapshotId);
  const failure = await executeAdapter({
    '/api/v1/selection/snapshot': {ok: false, status: 503, payload: {detail: {code: 'R2_NOT_AVAILABLE'}}}
  });
  assert.strictEqual(failure.applied, null);
  assert.strictEqual(failure.body.dataset.selectionMode, 'FIXTURE_FALLBACK');
  assert(failure.statuses[0].includes('R2_NOT_AVAILABLE'));
  assert(failure.events.some(event => event.type === 'trendforge:selection-error'));
  console.log('Atomic adapter preserves R1/R2 ownership, optional R5 and fail-closed fallback.');
})().catch(error => {console.error(error); process.exitCode = 1;});