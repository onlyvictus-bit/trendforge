#!/usr/bin/env node
// GD.1 checker: verifies S4/S5/S6 doc patches exist with observed-only content.
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(new URL("..", import.meta.url).pathname.replace(/^\/(?=[A-Za-z]:)/, ""));
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const assert = (cond, msg) => {
  if (!cond) throw new Error(msg);
};

const fileindex = read("fileindex.md");
assert(fileindex.includes("s4_structure_pack.py"), "fileindex must list s4 module");
assert(fileindex.includes("s5_shortlist_enrichment.py"), "fileindex must list s5 module");
assert(fileindex.includes("s6_family_resolution.py"), "fileindex must list s6 module");
assert(fileindex.includes("/api/v1/selection/s4-structure"), "fileindex must list s4 route");
assert(fileindex.includes("/api/v1/selection/s5-enrichment"), "fileindex must list s5 route");
assert(fileindex.includes("/api/v1/selection/s6-resolution"), "fileindex must list s6 route");
assert(fileindex.includes("#s4StructurePanel") && fileindex.includes("#s5EnrichmentPanel") && fileindex.includes("#s6InspectorMount"), "fileindex must list frontend mounts");

const status = read("docs/BUILD_STATUS.md");
assert(status.includes("LIVE_S4_WAIT_REJECT_ONLY"), "BUILD_STATUS must record S4 ceiling");
assert(status.includes("UNKNOWN_NEEDS_R12"), "BUILD_STATUS must record options stub");
assert(status.includes("Evidence strength - not win probability"), "BUILD_STATUS must record S6 label");
assert(!status.includes("S7 profile gates done"), "S7 must not be marked done");

const decisions = read("docs/DECISIONS.md");
for (const id of ["D-047", "D-048", "D-049", "D-050"]) {
  assert(decisions.includes(`## ${id}`), `DECISIONS missing ${id}`);
}
assert(decisions.includes("not Hybrid S4 p-hat"), "D-047 wording");
assert(decisions.includes("Options Detail Plan package not R12 complete"), "D-048 wording");
assert(decisions.includes("not Combined_Score"), "D-049 wording");
assert(decisions.includes("merged_feed"), "D-050 wording: merged feed board");

const validation = read("docs/VALIDATION.md");
assert(validation.includes("47 passed"), "VALIDATION must show 47 passed for S4 suite");
assert(validation.includes("46 passed"), "VALIDATION must show 46 passed for S5 suite");
assert(validation.includes("66 passed"), "VALIDATION must show 66 passed for S6 suite");
assert(validation.includes("193/193 checks passed"), "VALIDATION must show acceptance count");
assert(validation.includes("1162 passed / 6 failed"), "VALIDATION must record audit-round full-suite counts");
assert(validation.includes("merged feed") || validation.includes("merged_feed"), "VALIDATION must describe the merged-feed observation");

const readme = read("docs/fable/remaining_build/README.md");
assert(readme.includes("S4 coded at WAIT ceiling"), "README must have S4 status row");
assert(readme.includes("S5 WAIT enrich observed"), "README must have S5 status row");
assert(readme.includes("S6 WAIT fuse over S4+S5 claims"), "README must have S6 status row");
assert(readme.includes("NOT done:"), "README must keep out-of-scope items open");

const arch = read("docs/ARCHITECTURE.md");
assert(arch.includes("hash-matched R5/R14 lineage"), "ARCHITECTURE must say S4 consumes R5/R14");
assert(arch.includes("reuses R6 loaders and evidence-radar recipes"), "ARCHITECTURE must say S5 consumes R6");
assert(arch.includes("consumes R3's canonical"), "ARCHITECTURE must say S6 consumes R3 resolver");

console.log("docs verification passed: S4/S5/S6 patches present, out-of-scope items still open.");
