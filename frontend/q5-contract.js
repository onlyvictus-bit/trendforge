(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.TrendForgeQ5 = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const PUBLIC_STATES = new Set(["WATCH", "WAIT", "CONFIRMED", "REJECT"]);
  const ANSWER_FIELDS = [
    ["Why it appeared", "whyAppeared"],
    ["What changed", "whatChanged"],
    ["Strongest support", "topSupport"],
    ["Strongest conflict", "strongestContradiction"],
    ["Missing proof", "missingProof"],
    ["Freshness", "freshness"],
    ["Next confirmation", "confirmationCondition"],
    ["Invalidation", "invalidationCondition"]
  ];

  function canonicalState(value) {
    const state = String(value || "").trim().toUpperCase();
    if (state.startsWith("READY")) return "WATCH";
    for (const candidate of PUBLIC_STATES) {
      if (state === candidate || state.startsWith(`${candidate}_`)) return candidate;
    }
    return "WAIT";
  }

  function statusGroup(value) {
    return canonicalState(value).toLowerCase();
  }

  function validatePayload(payload) {
    if (!payload || typeof payload !== "object") throw new Error("Q5 payload is missing");
    if (payload.milestone !== "Q5-R6") throw new Error("Q5 milestone contract mismatch");
    if (typeof payload.fixtureOnly !== "boolean" || typeof payload.productionAuthorized !== "boolean") {
      throw new Error("Q5 authorization flags are malformed");
    }
    if (!Array.isArray(payload.radar) || payload.radar.length === 0) throw new Error("Q5 radar is empty");
    if (!payload.inspector || !Array.isArray(payload.inspector.sections)) throw new Error("Q5 inspector is malformed");
    const row = payload.radar[0];
    if (!row || typeof row !== "object") throw new Error("Q5 radar row is malformed");
    if (!PUBLIC_STATES.has(canonicalState(row.state))) throw new Error("Q5 state is malformed");
    for (const [, field] of ANSWER_FIELDS) {
      if (typeof row[field] !== "string" || !row[field].trim()) throw new Error(`Q5 field is missing: ${field}`);
    }
    return payload;
  }

  function answers(row) {
    return ANSWER_FIELDS.map(([label, field]) => [label, row[field]]);
  }

  function canShowPerformance(payload) {
    return Boolean(
      payload &&
      payload.fixtureOnly === false &&
      payload.productionAuthorized === true &&
      payload.inspector &&
      payload.inspector.validationStatus === "PIT_APPROVED" &&
      payload.inspector.performanceUiVisible === true
    );
  }

  return { canonicalState, statusGroup, validatePayload, answers, canShowPerformance };
});