const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..");
const index = fs.readFileSync(path.join(root, "index.html"), "utf8");
const source = fs.readFileSync(path.join(root, "openalgo-shadow.js"), "utf8");
const adapter = fs.readFileSync(path.join(root, "selection-live-adapter.js"), "utf8");

assert(index.includes('id="openAlgoShadowPanel"'), "Live Ops must contain the R17 shadow panel");
assert(index.indexOf("openalgo-shadow.js") < index.indexOf("selection-live-adapter.js"),
  "R17 renderer must load before the live adapter");
assert(adapter.includes("openalgoShadow"),
  "live adapter must load the read-only R17 endpoint");

const nodes = new Map([
  ["openAlgoShadowPanel", { hidden: false }],
  ["openAlgoShadowMeta", { textContent: "", className: "" }],
  ["openAlgoShadowRows", { innerHTML: "" }],
  ["openAlgoShadowInspector", { innerHTML: "" }]
]);
const sandbox = {
  window: {},
  document: { getElementById(id) { return nodes.get(id) || null; } }
};
vm.createContext(sandbox);
vm.runInContext(source, sandbox);

sandbox.window.TrendForgeOpenAlgoShadow.apply({
  schemaVersion: "trendforge.openalgo-shadow.v1",
  activation: { stage: "REST_SHADOW_OBSERVED", blockerCodes: ["WAIT_STREAM_OBSERVATION"] },
  baseRunHash: "base-1",
  baseOutputUnchanged: true,
  confirmedCount: 0,
  executable: false,
  rows: [{
    symbol: "RELIANCE",
    basePublicState: "WATCH",
    publicState: "WATCH",
    openalgoProfileState: "WATCH",
    evidenceDirection: "BULLISH",
    restQualityState: "VALID_POPULATED",
    restAgeSeconds: 12,
    researchEntry: 100,
    researchStop: 95,
    researchT1: 107.5,
    researchT2: 110,
    researchQuantity: 25,
    qtyUnit: "contracts",
    missingOrConflicting: [],
    nextCondition: "Keep evidence fresh.",
    optionConcentration: { voteCount: 7, datasetRootCount: 1, independentConfirmationCount: 0 },
    optionVotes: [{
      voteId: "OPTION_PCR_CROWDING",
      purpose: "put/call OI crowding",
      applicability: "AVAILABLE",
      rawValue: 1.2,
      interpretation: "context only",
      formulaVersion: "v1",
      datasetRootId: "root-1",
      snapshotId: "snap-1",
      rawContentHash: "raw-1",
      canConfirm: false
    }]
  }]
});

assert(nodes.get("openAlgoShadowRows").innerHTML.includes("RELIANCE"));
assert(nodes.get("openAlgoShadowRows").innerHTML.includes("25 contracts"));
assert(nodes.get("openAlgoShadowRows").innerHTML.includes("0 independent confirmations"));
assert(nodes.get("openAlgoShadowInspector").innerHTML.includes("root-1"));
assert(!nodes.get("openAlgoShadowRows").innerHTML.includes("CONFIRMED"));

sandbox.window.TrendForgeOpenAlgoShadow.apply({
  schemaVersion: "trendforge.openalgo-shadow.v1",
  activation: { stage: "DISABLED", blockerCodes: ["OPENALGO_DISABLED"] },
  baseRunHash: "DISABLED_NO_BASE_RUN",
  rows: [],
  executable: false
});
assert(nodes.get("openAlgoShadowRows").innerHTML.includes("No OpenAlgo network"));
console.log("R17 OpenAlgo shadow frontend checks passed.");
