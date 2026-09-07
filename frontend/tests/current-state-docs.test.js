const assert = require('assert');
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '../..');
const read = name => fs.readFileSync(path.join(root, name), 'utf8');
const current = read('docs/CURRENT_STATE.md');
for (const term of ['2026-09-07', 'R18', 'MODEL_NOT_APPROVED', 'historical', 'PIT', 'execution', 'freshness']) {
  assert(current.includes(term), `current summary missing ${term}`);
}
for (const file of ['docs/BUILD_STATUS.md', 'docs/VALIDATION.md', 'TREND_FORGE_ARCHITECTURE.md',
  'docs/ARCHITECTURE.md', 'docs/fable/remaining_build/README.md',
  'docs/fable/remaining_build/REMAINING_PROJECT_BUILD_FILES.md', 'fileindex.md', 'GATES.md',
  'docs/fable/S0_S9_RUN_OVERLAY_MAP_2026-08-24.md']) {
  const text = read(file);
  assert(text.startsWith('<!-- CURRENT_STATE_HISTORY_BOUNDARY'), `${file} lacks explicit history boundary`);
  const link = text.match(/\[([^\]]*CURRENT_STATE\.md)\]\(([^)]+)\)/);
  assert(link && fs.existsSync(path.resolve(root, path.dirname(file), link[2])), `${file}: broken snapshot link`);
}
assert(read('docs/BUILD_STATUS.md').includes('R18 code is not present.'), 'historical evidence must be retained');
assert(read('docs/BUILD_STATUS.md').indexOf('Historical checkpoints (preserved)') <
  read('docs/BUILD_STATUS.md').indexOf('R18 code is not present.'), 'old statement must be under history boundary');
assert(current.includes('r18_governance.py'), 'summary must point to implementation, not an obsolete build task');
assert(read('frontend/index.html').includes('id="history"'));
assert(read('frontend/index.html').includes('id="statusProvenance"'));
assert(!read('frontend/index.html').includes('<span class="chip wait">sourceActivationReady=false</span>'));
console.log('Current-state documentation: navigation links, historical boundaries and preserved observations passed.');