const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
const script = fs.readFileSync(path.join(root, "r18-model-governance.js"), "utf8");

function assert(value, message) {
  if (!value) throw new Error(message);
}

assert(html.includes('id="r18ModelGovernancePanel"'), "Paper/ML panel must mount R18 governance");
assert(html.includes("r18-model-governance.js?v=20260901-r18-1"), "R18 script must be mounted with a pinned version");
assert(script.includes("/api/research/ml/governance"), "R18 UI must use the read-only governance API");
assert(script.includes("MODEL_NOT_APPROVED"), "R18 UI must show the locked runtime state");
assert(script.includes("Probability: HIDDEN"), "Probability must remain hidden");
assert(script.includes("Win rate: HIDDEN"), "Win rate must remain hidden");
assert(script.includes("Performance: HIDDEN"), "Performance must remain hidden");
assert(!/placeorder|place_order|winRateVisible\s*:\s*true/i.test(script), "R18 UI must not trade or expose win rate");

console.log("R18 model-governance frontend contract passed");
