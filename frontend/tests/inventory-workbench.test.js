const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const frontendRoot = path.resolve(__dirname, "..");
const snapshotRoot = path.join(frontendRoot, "inventory-workbench");
const manifestPath = path.join(snapshotRoot, "inventory-workbench.manifest.json");
const hostHtmlPath = path.join(frontendRoot, "index.html");
const hostFixturePath = path.join(frontendRoot, "product-fixture.js");
const hostThemePath = path.join(frontendRoot, "theme-final.css");

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function read(file) {
  return fs.readFileSync(file, "utf8");
}

function sha256(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex").toUpperCase();
}

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}

assert(fs.existsSync(manifestPath), "Snapshot manifest is missing");
const manifest = JSON.parse(read(manifestPath).replace(/^﻿/, ""));
assert(manifest.contract === "trendforge.inventoryWorkbenchSnapshot.v1", "Unexpected manifest contract");
assert(manifest.overlay_mode === "declared", "Workbench snapshot must declare overlay mode");
assert(manifest.source_app_edited === true, "Overlay snapshot must admit source-app glass edits");
assert(manifest.serving_path === "/inventory-workbench/", "Unexpected serving path");
assert(manifest.state_authority === "NONE", "Inventory snapshot must have no state authority");
assert(Array.isArray(manifest.files) && manifest.files.length === 24, "Expected 24 allow-listed snapshot files");

const overlayFiles = new Set(manifest.overlay_files || []);
const frozenScoring = new Set(["screener.js", "consensus.js", "consensus_plugins.js", "schemas.js"]);

for (const entry of manifest.files) {
  const copied = path.join(snapshotRoot, entry.path);
  assert(fs.existsSync(copied), "Copied file missing: " + entry.path);
  assert(fs.statSync(copied).size === entry.bytes, "Size mismatch: " + entry.path);
  assert(sha256(copied) === entry.copied_sha256, "Copied hash mismatch: " + entry.path);
  if (frozenScoring.has(entry.path)) {
    assert(entry.source_sha256 === entry.copied_sha256, "Scoring engine drifted from frozen source: " + entry.path);
    assert(entry.overlay !== true, "Scoring engine cannot be an overlay file: " + entry.path);
  } else if (entry.overlay === true) {
    assert(overlayFiles.has(entry.path), "Overlay file missing from overlay_files: " + entry.path);
  } else {
    assert(entry.source_sha256 === entry.copied_sha256, "Non-overlay snapshot is not source-identical: " + entry.path);
  }
}

const copiedNames = walk(snapshotRoot).map((file) => path.relative(snapshotRoot, file));
assert(!copiedNames.some((name) => /(^|[\/])node_modules([\/]|$)/i.test(name)), "node_modules must not be copied");
assert(!copiedNames.some((name) => /.bak($|.)|.pytest_|(^|[\/])temp|(^|[\/])cache/i.test(name)), "Backup/cache/temp files must not be copied");

const index = read(path.join(snapshotRoot, "index.html"));
const expectedScriptOrder = [
  "schemas.js",
  "consensus.js",
  "consensus_plugins.js",
  "screener.js",
  "sector_screener.js",
  "live_panels.js",
  "fii_stock_signals_panel.js",
  "app.js",
  "header_collapse.js",
  "sidebar_collapse.js"
];
let cursor = -1;
for (const script of expectedScriptOrder) {
  const next = index.indexOf(script, cursor + 1);
  assert(next > cursor, "Script order broken at " + script);
  cursor = next;
}
assert(!index.includes('fetch("links_105.json", { cache: "no-store" })'), "Data fetch belongs in app.js, not index.html");
assert(read(path.join(snapshotRoot, "app.js")).includes('fetch("links_105.json", { cache: "no-store" })'), "Catalog no-store fetch is missing");
assert(read(path.join(snapshotRoot, "consensus.js")).includes("TrendForge"), "Consensus runtime was not copied");
assert(read(path.join(snapshotRoot, "screener.js")).includes("registerScreenerExtractor"), "Screener extension contract was not copied");

const hostHtml = read(hostHtmlPath);
const hostFixture = read(hostFixturePath);
assert(hostHtml.includes('href="/inventory-workbench/"'), "Host full-page link must use the bundled route");
assert(hostHtml.includes("<code>/inventory-workbench/</code>"), "Host status must show the bundled route");
assert(
  /var inventoryPath='\/inventory-workbench\/(\?embed=terminal[^']*)?'/.test(hostFixture),
  "Host drawer must target the bundled route, optionally with embed=terminal"
);
assert(hostFixture.includes("if(!response.ok)throw new Error('HTTP '+response.status)"), "Drawer probe must validate HTTP status");
assert(!hostHtml.includes("127.0.0.1:8080"), "Legacy :8080 dependency remains in host HTML");
assert(!hostFixture.includes("127.0.0.1:8080"), "Legacy :8080 dependency remains in drawer code");

const hostTheme = read(hostThemePath);
const desktopMaximized = hostTheme.lastIndexOf(".inventory-drawer{top:2vh;width:95vw;max-width:none;height:96vh");
const mobileOverride = hostTheme.lastIndexOf(".inventory-drawer{top:0;width:100vw;max-width:none;height:100dvh}");
const baseDrawer = hostTheme.lastIndexOf(".inventory-drawer{position:fixed");
assert(desktopMaximized > baseDrawer, "Maximized desktop drawer override must follow the base drawer rule");
assert(mobileOverride > baseDrawer, "Final mobile drawer override must follow the base drawer rule");

console.log("inventory-workbench.test.js: " + manifest.files.length + " copied files verified");