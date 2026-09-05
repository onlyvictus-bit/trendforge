const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
const script = fs.readFileSync(path.join(root, "s3-cheap-discovery.js"), "utf8");
const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");

assert(html.includes('id="s3WatchQueue"'), "All Stocks must mount the S3 queue");
assert(html.includes('id="s3WatchQueueOps"'), "Live Ops must mount the S3 queue");
assert(adapter.includes("/api/v1/selection/cheap-discovery/watch?limit=50"),
  "selection adapter must load the bounded S3 watch projection");
assert(!script.includes("deliveryPct"), "S3 UI must not display delivery");
assert(!script.includes("winProbability"), "S3 UI must not display win probability");
assert(!script.includes("entry:"), "S3 UI must not invent entry geometry");

const mounts = {
  s3WatchQueue: { innerHTML: "" },
  s3WatchQueueOps: { innerHTML: "" }
};
const body = { dataset: {} };
const sandbox = {
  console,
  document: {
    body,
    getElementById(id) { return mounts[id] || null; }
  },
  window: {}
};
vm.createContext(sandbox);
vm.runInContext(script, sandbox);

const count = sandbox.window.TrendForgeS3CheapDiscovery.apply({
  schemaVersion: "trendforge.s3-watch-queue.v1",
  totalWatchCount: 1,
  completeness: 1,
  waitPartialScan: false,
  rows: [{
    symbol: "TATASTEEL",
    publicState: "WATCH",
    researchState: "WATCH",
    attentionPriority: 0.82,
    a3Profiles: ["DISC_EOD_MOMENTUM"],
    tags: ["ACTIVITY_LIST", "RVOL_EOD"],
    whyUnknown: ["UNKNOWN_RS_1D_NO_ALIGNED_BENCHMARK"],
    rvolEod: 1.8,
    rs1d: null
  }]
});
assert.strictEqual(count, 1);
assert(mounts.s3WatchQueue.innerHTML.includes("TATASTEEL"));
assert(mounts.s3WatchQueue.innerHTML.includes("ACTIVITY_LIST"));
assert(mounts.s3WatchQueue.innerHTML.includes("WATCH_QUEUE_READY"));
assert.strictEqual(mounts.s3WatchQueue.innerHTML, mounts.s3WatchQueueOps.innerHTML);
assert.strictEqual(body.dataset.s3Mode, "LIVE_WATCH");

sandbox.window.TrendForgeS3CheapDiscovery.apply(null);
assert(mounts.s3WatchQueue.innerHTML.includes("WAIT_S3_NOT_READY"));
assert.strictEqual(body.dataset.s3Mode, "WAIT");

console.log("S3 cheap-discovery frontend checks passed.");
