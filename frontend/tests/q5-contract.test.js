const assert = require("assert");
const q5 = require("../q5-contract.js");

assert.equal(q5.canonicalState("WATCH"), "WATCH");
assert.equal(q5.canonicalState("WAIT_BAR_CLOSE"), "WAIT");
assert.equal(q5.canonicalState("READY"), "WATCH");
assert.equal(q5.canonicalState("malformed"), "WAIT");
assert.equal(q5.statusGroup("WATCH"), "watch");
assert.equal(q5.statusGroup("WAIT_SOURCE"), "wait");

const row = {
  state: "REJECT",
  whyAppeared: "a",
  whatChanged: "b",
  topSupport: "c",
  strongestContradiction: "d",
  missingProof: "e",
  freshness: "f",
  confirmationCondition: "g",
  invalidationCondition: "h"
};
const fixture = {
  milestone: "Q5-R6",
  fixtureOnly: true,
  productionAuthorized: false,
  radar: [row],
  inspector: {
    validationStatus: "PIT_APPROVED",
    performanceUiVisible: true,
    sections: []
  }
};
assert.equal(q5.validatePayload(fixture), fixture);
assert.equal(q5.answers(row).length, 8);
assert.equal(q5.canShowPerformance(fixture), false);
assert.equal(q5.canShowPerformance({ ...fixture, fixtureOnly: false, productionAuthorized: true }), true);
assert.throws(() => q5.validatePayload({ ...fixture, radar: [] }), /radar is empty/);
assert.throws(() => q5.validatePayload({ ...fixture, productionAuthorized: "yes" }), /authorization flags/);
assert.throws(() => q5.validatePayload({ ...fixture, radar: [{ ...row, freshness: "" }] }), /freshness/);

console.log("Q5 contract behavior checks passed.");