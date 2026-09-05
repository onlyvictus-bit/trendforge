const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..");
const index = fs.readFileSync(path.join(root, "index.html"), "utf8");
const app = fs.readFileSync(path.join(root, "app.js"), "utf8");
const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");
const fixture = fs.readFileSync(path.join(root, "product-fixture.js"), "utf8");

const fixtureIndex = index.indexOf("product-fixture.js");
const adapterIndex = index.indexOf("selection-live-adapter.js");
const appIndex = index.indexOf("app.js");
assert(fixtureIndex >= 0 && adapterIndex > fixtureIndex && appIndex > adapterIndex,
  "product renderer, R1/R2 adapter and legacy app must load in ownership order");

assert(adapter.includes("/api/v1/selection/attention"), "adapter must load persisted R2 attention");
assert(adapter.includes("/api/v1/selection/evidence"), "adapter must load persisted R1 evidence");
assert(adapter.includes("/api/v1/selection/structure"), "adapter must optionally load persisted R5 structure");
assert(adapter.includes("/api/v1/selection/identity-pin"), "adapter must optionally load persisted R4 identity pin");
assert(adapter.includes("/api/v1/selection/cheap-discovery/watch?limit=50"), "adapter must optionally load S3 watch queue");
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
  vm.runInContext(adapter, sandbox);
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));
  return { events, statuses, applied, body };
}

(async () => {
  const attention = {
    schemaVersion: "trendforge.inventory-discovery.v1",
    runId: "r2-1",
    rows: [{ symbol: "TATASTEEL", publicState: "WATCH" }]
  };
  const evidence = {
    schemaVersion: "trendforge.inventory-source-bundle.v1",
    bundleId: "r1-1",
    stockRecords: []
  };
  const success = await executeAdapter({
    "/api/v1/selection/attention": { ok: true, status: 200, payload: attention },
    "/api/v1/selection/evidence": { ok: true, status: 200, payload: evidence },
    "/api/v1/selection/structure": { ok: false, status: 503, payload: { detail: { code: "R5_STRUCTURE_NOT_READY" } } },
    "/api/v1/selection/identity-pin": { ok: false, status: 503, payload: { detail: { code: "R4_IDENTITY_PIN_NOT_READY" } } }
  });
  assert.strictEqual(success.applied.attention, attention);
  assert.strictEqual(success.applied.evidence, evidence);
  assert.strictEqual(success.applied.structure, null);

  const structure = {
    schemaVersion: "trendforge.structure-batch.v1",
    runId: "r5-1",
    waitCount: 1,
    rejectCount: 0,
    rows: [{ symbol: "TATASTEEL", structureState: "WAIT", whyWait: ["WAIT_INDEX_CONTEXT_MISSING"] }]
  };
  const withR5 = await executeAdapter({
    "/api/v1/selection/attention": { ok: true, status: 200, payload: attention },
    "/api/v1/selection/evidence": { ok: true, status: 200, payload: evidence },
    "/api/v1/selection/structure": { ok: true, status: 200, payload: structure },
    "/api/v1/selection/identity-pin": { ok: false, status: 503, payload: { detail: { code: "R4_IDENTITY_PIN_NOT_READY" } } }
  });
  assert.strictEqual(withR5.applied.structure, structure);
  assert(success.events.some((event) => event.type === "trendforge:selection-ready"));
  assert.strictEqual(success.body.dataset.selectionMode, undefined);

  const failure = await executeAdapter({
    "/api/v1/selection/attention": { ok: false, status: 503, payload: { detail: { code: "R2_NOT_AVAILABLE" } } },
    "/api/v1/selection/evidence": { ok: false, status: 503, payload: { detail: { code: "R1_NOT_AVAILABLE" } } },
    "/api/v1/selection/structure": { ok: false, status: 503, payload: { detail: { code: "R5_STRUCTURE_NOT_READY" } } },
    "/api/v1/selection/identity-pin": { ok: false, status: 503, payload: { detail: { code: "R4_IDENTITY_PIN_NOT_READY" } } }
  });
  assert.strictEqual(failure.applied, null);
  assert.strictEqual(failure.body.dataset.selectionMode, "FIXTURE_FALLBACK");
  assert(failure.statuses[0].includes("R2_NOT_AVAILABLE"));
  assert(failure.events.some((event) => event.type === "trendforge:selection-error"));
  console.log("R1/R2 exclusive live adapter checks passed.");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});