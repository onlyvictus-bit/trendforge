// consensus_plugins.js — Extra / future inventory voters for ConsensusEngine v4
// ─────────────────────────────────────────────────────────────────────────────
// Docs: ARCHITECTURE.md §5 · INDEX.md (consensus boards)
//
// HOW TO ADD A NEW STOCK VOTER (no scorer formula rewrite):
//
//   1. Source must be in links_105.json with active_source_keys + records_sample
//   2. Row must expose a **stock symbol** (not market-wide category totals)
//   3. Register board via factory or registerConsensusBoard (family avoids double-count)
//   4. Prefer existing metrics/factories: dealPair, momentum, volumeSpike, preopenGap,
//      deliverySplit, shortInterest, oiSpurt, fnoBan, pitPair, surveillance
//
// NOT stock voters (do not add as symbol boards):
//   - nse_fii_dii, nsdl_fpi_*  → market/category aggregates only
//   - amfi_nav                 → scheme NAVs, not stock symbols
//   - news / calendar / macro  → catalyst context only
// ─────────────────────────────────────────────────────────────────────────────
'use strict';

(function registerFutureConsensusPlugins() {
  if (typeof registerConsensusBoards !== 'function' || typeof ConsensusBoards === 'undefined') {
    console.warn('[Consensus plugins] Engine not loaded — skip plugin registration');
    return;
  }

  // Core expanded stock voters are registered in consensus.js loadDefaultBoards()
  // (bulk CSV, preopen cash, delivery, short, OI spurts, F&O ban, most-active, EOD bhav).
  // Keep this file for experimental / low-weight plugins only.

  // Placeholder keeps file load-safe.
  registerConsensusBoards([
    {
      id: 'plugin_template_disabled',
      sourceKey: '__none__',
      side: 'BUY',
      family: 'plugin',
      weight: 1.0,
      label: 'Plugin Template (disabled)',
      symbolFields: ['symbol'],
      metric: 'value',
      enabled: false
    }
  ]);
})();
