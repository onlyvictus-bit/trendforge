// TrendForge Market Source Inventory App Logic (row counts are data-driven)

let inventory = [];
let activeTopic = "All Topics";
let activeStatus = "ALL";
let activeTag = null;
let searchQuery = "";
let sortBy = "usable_rows_desc";
let viewMode = "grid"; // "grid" or "table"
/** When false (default): show one strong primary per feed; twins as hints (inventory data kept). */
let collapseDuplicates = true;
/** Primary-card rows minimized by the user; retained across filter/search rerenders. */
const collapsedCardRows = new Set();
/** Built after load: primaryKey → { champion, twins, verifiedSame, members } */
let sourceGroups = new Map();

document.addEventListener("DOMContentLoaded", () => {
  applyInventoryEmbedMode();
  fetchData();
  setupEventListeners();
  initSourceOperationsPanel();
});


function applyInventoryEmbedMode() {
  const embedded = new URLSearchParams(window.location.search).get("embed") === "terminal";
  document.body.classList.toggle("inventory-embedded", embedded);
  if (embedded) {
    document.documentElement.dataset.host = "trendforge-terminal";
  }
}
async function fetchData() {
  try {
    // The collector can refresh catalog samples while this static SPA is open.
    // Revalidate the legacy snapshot name so a normal reload shows fresh cards.
    const res = await fetch("links_105.json", { cache: "no-store" });
    inventory = await res.json();
    initApp();
  } catch (err) {
    console.error("Failed to load links_105.json:", err);
    document.getElementById("main-container").innerHTML = `
      <div style="padding: 2rem; color: #ef4444;">
        <h2>Error Loading Data</h2>
        <p>Could not fetch <code>links_105.json</code>. Ensure the file is in the same directory as index.html.</p>
      </div>`;
  }
}

function initApp() {
  // Expose for screener modal / think-engine hooks (read-only consumers)
  window.inventory = inventory;

  applyDynamicCatalogLabels();
  buildSourceGroups(inventory);
  renderKPIs();
  renderSidebarTopics();
  renderFieldTagCloud();
  applyFiltersAndRender();
  // One immutable catalog + one isolated live overlay feeds all three panels.
  // The controller fails closed: cached price/vote samples never silently leak.
  if (window.LivePanelsController && typeof window.LivePanelsController.start === 'function') {
    window.LivePanelsController.start(inventory);
  } else {
    console.error('[LivePanels] controller unavailable; panel calculations blocked');
    ['sector-screener-panel', 'consensus-strip', 'screener-panel'].forEach(id => {
      const host = document.getElementById(id);
      if (host) host.innerHTML = `<div style="padding:0.8rem;color:#fb7185;font-size:0.75rem;">
        WAIT · live panel controller unavailable · cached calculations blocked</div>`;
    });
  }
  if (window.FIIStockSignalsPanel && typeof window.FIIStockSignalsPanel.start === 'function') {
    window.FIIStockSignalsPanel.start();
  } else {
    const host = document.getElementById('fii-stock-signals-panel');
    if (host) host.innerHTML = '<div class="fii-signals-message fii-signals-error">WAIT · FII-related stock-name panel unavailable</div>';
  }
}

function getUniqueSourceKeyCount() {
  const keys = new Set();
  inventory.forEach(item => String(item.active_source_keys || "").split("|")
    .map(key => key.trim()).filter(Boolean).forEach(key => keys.add(key)));
  return keys.size;
}

function applyDynamicCatalogLabels() {
  const total = inventory.length;
  const uniqueKeys = getUniqueSourceKeyCount();
  document.title = `TrendForge | Market Source Inventory Catalog (${total} Links)`;
  const subtitle = document.getElementById("brand-subtitle");
  if (subtitle) subtitle.textContent = `${total} Linked Sources • ${uniqueKeys} Unique Keys • Screener & Provenance Catalog`;
  const rowSort = document.getElementById("sort-row-number");
  if (rowSort) rowSort.textContent = `Row Number (#1 to #${total})`;
  const aboutTotal = document.getElementById("about-total");
  if (aboutTotal) aboutTotal.textContent = String(total);
  const aboutTotalCopy = document.getElementById("about-total-copy");
  if (aboutTotalCopy) aboutTotalCopy.textContent = String(total);
  const aboutUnique = document.getElementById("about-unique");
  if (aboutUnique) aboutUnique.textContent = String(uniqueKeys);
  const aboutUseful = document.getElementById("about-useful");
  if (aboutUseful) aboutUseful.textContent = String(
    inventory.filter(item => !["PROVENANCE", "VALID_EMPTY", "SOFT_EMPTY", "BLOCKED"].includes(item.status)).length
  );
}

// ======================================================================
// DUPLICATE LINK COLLAPSE (display-only — never deletes inventory rows)
// Groups by primary active_source_keys; keeps strongest/fastest as champion.
// Twins become hints/commands under the champion after same-output verify.
// ======================================================================

function primarySourceKey(item) {
  return String(item.active_source_keys || "").split("|")[0].trim() || ("row_" + item.row_no);
}

function sampleFingerprint(item) {
  const rs = item.records_sample || [];
  if (!rs.length) return { n: 0, head: "", tail: "" };
  try {
    return {
      n: rs.length,
      head: JSON.stringify(rs[0]),
      tail: JSON.stringify(rs[rs.length - 1])
    };
  } catch (_) {
    return { n: rs.length, head: "", tail: "" };
  }
}

function isApiLikeUrl(url) {
  const u = String(url || "").toLowerCase();
  return /\/api\/|api\.|\.csv|\.json|\.zip|\.txt|fredgraph|archives\.|fsapi\.|bulkdeal|corporatesast|share-holdings|liveequity|raw\?/.test(u);
}

function isSlowNavUrl(url) {
  const u = String(url || "").toLowerCase();
  if (isApiLikeUrl(u)) return false;
  return /\.html|\.aspx|\/ann|corporates\/|goldhub|\/markets\/|index\.htm|series\/|resources\//.test(u);
}

/** Higher = stronger / more efficient primary for display + screening. */
function sourceEfficiencyScore(item) {
  const statusPts = {
    STRONG: 1000,
    SUPPORTING: 850,
    THIRD_PARTY: 600,
    CONTEXT_NEWS: 700,
    COMPANION: 550,
    PROVENANCE: 250,
    VALID_EMPTY: 100,
    SOFT_EMPTY: 80,
    BLOCKED: 40
  }[item.status] || 150;

  const sampleN = (item.records_sample || []).length;
  const usable = Number(item.usable_rows) || 0;
  const apiPts = isApiLikeUrl(item.canonical_url) ? 120 : 0;
  const slowPenalty = isSlowNavUrl(item.canonical_url) ? -80 : 0;
  const conn = String(item.connection_status || "");
  const freshPts = /CONNECTED_FRESH|STRUCTURED_OK/i.test(conn + " " + (item.parser_status || "")) ? 40 : 0;
  const modePenalty = String(item.mode || "").toUpperCase() === "COMPANION" ? -30 : 0;
  // Prefer lower row_no as mild tie-break (stable)
  return statusPts + apiPts + slowPenalty + freshPts + modePenalty + Math.min(sampleN, 250) + Math.min(usable, 5000) / 100 - (item.row_no || 0) * 0.001;
}

function twinWeaknessHint(champ, twin) {
  const reasons = [];
  if (twin.status === "PROVENANCE") reasons.push("nav page · not primary fetch");
  if (twin.status === "COMPANION") reasons.push("backup when primary empty");
  if (twin.status === "CONTEXT_NEWS" && champ.status === "STRONG") reasons.push("news context only");
  if (isSlowNavUrl(twin.canonical_url) && isApiLikeUrl(champ.canonical_url)) reasons.push("HTML portal · slower");
  if (isApiLikeUrl(twin.canonical_url) && isApiLikeUrl(champ.canonical_url) && twin.row_no !== champ.row_no) {
    reasons.push("alt URL / params · same feed");
  }
  const cn = (champ.records_sample || []).length;
  const tn = (twin.records_sample || []).length;
  if (tn < cn) reasons.push(`thinner sample (${tn} vs ${cn})`);
  if ((Number(twin.usable_rows) || 0) < (Number(champ.usable_rows) || 0)) {
    reasons.push("lower usable_rows meta");
  }
  if (sourceEfficiencyScore(twin) < sourceEfficiencyScore(champ)) {
    if (!reasons.length) reasons.push("lower efficiency score");
  }
  return reasons.length ? reasons.join(" · ") : "mirror contract · same dataset";
}

function buildSourceGroups(items) {
  sourceGroups = new Map();
  const buckets = new Map();
  (items || []).forEach(item => {
    const k = primarySourceKey(item);
    if (!buckets.has(k)) buckets.set(k, []);
    buckets.get(k).push(item);
  });

  let verifiedGroups = 0;
  let multiGroups = 0;

  buckets.forEach((members, key) => {
    const ranked = members.slice().sort((a, b) => sourceEfficiencyScore(b) - sourceEfficiencyScore(a));
    const champion = ranked[0];
    const twins = ranked.slice(1);

    // Double-verify same output among members (sample count + first/last row)
    const fps = members.map(sampleFingerprint);
    const sameN = fps.every(f => f.n === fps[0].n);
    const sameHead = fps.every(f => f.head === fps[0].head);
    const sameTail = fps.every(f => f.tail === fps[0].tail);
    const verifiedSame = members.length === 1 || (sameN && sameHead && sameTail);

    if (members.length > 1) {
      multiGroups++;
      if (verifiedSame) verifiedGroups++;
    }

    const twinMeta = twins.map(t => ({
      row_no: t.row_no,
      status: t.status,
      title: t.title,
      url: t.canonical_url,
      sample_n: (t.records_sample || []).length,
      usable_rows: t.usable_rows,
      score: Math.round(sourceEfficiencyScore(t)),
      hint: twinWeaknessHint(champion, t),
      isApi: isApiLikeUrl(t.canonical_url),
      isSlow: isSlowNavUrl(t.canonical_url)
    }));

    sourceGroups.set(key, {
      key,
      champion,
      twins: twinMeta,
      members,
      verifiedSame,
      championScore: Math.round(sourceEfficiencyScore(champion))
    });
  });

  console.info(
    `[Dedupe] ${sourceGroups.size} primary feeds · ${multiGroups} multi-link groups · ` +
    `${verifiedGroups}/${multiGroups} verified same sample output · collapse=${collapseDuplicates}`
  );
}

function getGroupForItem(item) {
  return sourceGroups.get(primarySourceKey(item));
}

/** Collapse filtered list to champions; keep twins only if collapse off. */
function applyDuplicateCollapse(filtered) {
  if (!collapseDuplicates) {
    return filtered.map(item => {
      const g = getGroupForItem(item);
      return Object.assign({}, item, {
        _isChampion: g && g.champion.row_no === item.row_no,
        _twins: (g && g.champion.row_no === item.row_no) ? g.twins : [],
        _groupSize: g ? g.members.length : 1,
        _verifiedSame: g ? g.verifiedSame : true,
        _championScore: g ? g.championScore : 0
      });
    });
  }

  // Status drill-down to PROVENANCE/COMPANION/etc.: pick best *within filtered set*
  // so we don't force a STRONG champion when user asked only for nav pages.
  const statusScoped = activeStatus !== "ALL" && activeStatus !== "STRONG";

  const champIds = new Set();
  const out = [];
  const seenKeys = new Set();

  filtered.forEach(item => {
    const g = getGroupForItem(item);
    if (!g) {
      out.push(Object.assign({}, item, { _isChampion: true, _twins: [], _groupSize: 1, _verifiedSame: true }));
      return;
    }

    const key = g.key;
    if (seenKeys.has(key)) return;
    seenKeys.add(key);

    let lead = g.champion;
    let twins = g.twins;
    let twinSearchHit = false;

    if (statusScoped) {
      // Best efficiency among rows that already passed the status filter
      const inFilter = g.members.filter(m => filtered.some(f => f.row_no === m.row_no));
      if (!inFilter.length) return;
      lead = inFilter.slice().sort((a, b) => sourceEfficiencyScore(b) - sourceEfficiencyScore(a))[0];
      twins = inFilter
        .filter(m => m.row_no !== lead.row_no)
        .map(t => ({
          row_no: t.row_no,
          status: t.status,
          title: t.title,
          url: t.canonical_url,
          sample_n: (t.records_sample || []).length,
          usable_rows: t.usable_rows,
          score: Math.round(sourceEfficiencyScore(t)),
          hint: twinWeaknessHint(lead, t),
          isApi: isApiLikeUrl(t.canonical_url),
          isSlow: isSlowNavUrl(t.canonical_url)
        }));
    } else {
      const champInFilter = filtered.some(f => f.row_no === g.champion.row_no);
      const twinMatched = g.twins.some(t => filtered.some(f => f.row_no === t.row_no));
      if (!champInFilter && !twinMatched) return;
      twinSearchHit = twinMatched && !champInFilter;
      lead = inventory.find(i => i.row_no === g.champion.row_no) || g.champion;
      twins = g.twins;
    }

    if (champIds.has(lead.row_no)) return;
    champIds.add(lead.row_no);

    out.push(Object.assign({}, lead, {
      _isChampion: true,
      _twins: twins,
      _groupSize: g.members.length,
      _verifiedSame: g.verifiedSame,
      _championScore: Math.round(sourceEfficiencyScore(lead)),
      _twinSearchHit: twinSearchHit
    }));
  });

  return out;
}

function toggleCollapseDuplicates() {
  collapseDuplicates = !collapseDuplicates;
  const btn = document.getElementById("dedupe-toggle-btn");
  if (btn) {
    btn.textContent = collapseDuplicates ? "▣ Strong feeds only" : `▦ Show all ${inventory.length} links`;
    btn.title = collapseDuplicates
      ? "Showing one strong primary per feed; mirrors as hints"
      : "Showing every inventory URL contract (including PROVENANCE twins)";
    btn.classList.toggle("active", collapseDuplicates);
  }
  applyFiltersAndRender();
}

function renderTwinHintsHTML(item) {
  const twins = item._twins || [];
  if (!twins.length) return "";

  const verified = item._verifiedSame
    ? `<span class="twin-verify ok" title="Double-checked: same sample row count + same first/last sample row">✓ same output · n=${(item.records_sample || []).length}</span>`
    : `<span class="twin-verify warn" title="Sample fingerprint differs — review before merging logic">⚠ sample differs</span>`;

  const lines = twins.map(t => {
    const kind = t.status === "PROVENANCE" ? "hint:nav" : t.status === "COMPANION" ? "hint:backup" : "hint:alt";
    const slow = t.isSlow ? " · slow/nav" : (t.isApi ? " · api" : "");
    return `<div class="twin-hint-line" title="${escapeHTML(t.hint)}">
      <code class="twin-cmd">#${t.row_no}</code>
      <span class="twin-kind">${kind}</span>
      <span class="twin-status status-chip status-${t.status}">${t.status}</span>
      <span class="twin-hint-text">${escapeHTML(t.hint)}${slow}</span>
      <span class="twin-actions">
        <button type="button" class="icon-btn" onclick="openDrawer(${t.row_no})" title="Open twin details">📄</button>
        <a class="icon-btn" href="${escapeHTML(t.url)}" target="_blank" rel="noopener" title="Open twin URL">↗</a>
      </span>
    </div>`;
  }).join("");

  // Collapsed by default so mirrors do not drown unique/primary feed content
  return `<details class="twin-hints-box">
    <summary class="twin-hints-header">
      <span>⛓ ${twins.length} weaker mirror link${twins.length > 1 ? "s" : ""} hidden (primary is #${item.row_no})</span>
      ${verified}
    </summary>
    <div class="twin-hints-list">${lines}</div>
    <div class="twin-hints-foot">Inventory still has all contracts · this card = strongest/fastest source · expand only to audit mirrors</div>
  </details>`;
}

function renderKPIs() {
  const total = inventory.length;
  const strong = inventory.filter(i => i.status === "STRONG").length;
  const research = inventory.filter(i =>
    /LINKED_RESEARCH_SCREENER|SUPPORTING_EVIDENCE|RISK_FILTER|GATE_DEPENDENCY/.test(i.screener_integration || "")
  ).length;
  const empty = inventory.filter(i => ["VALID_EMPTY","SOFT_EMPTY","BLOCKED"].includes(i.status)).length;
  const news = inventory.filter(i => i.status === "CONTEXT_NEWS").length;

  document.getElementById("kpi-total").textContent = total;
  document.getElementById("kpi-strong").textContent = strong;
  document.getElementById("kpi-research").textContent = research;
  document.getElementById("kpi-empty").textContent = empty;
  document.getElementById("kpi-news").textContent = news;
}

function renderSidebarTopics() {
  const topicCounts = { "All Topics": inventory.length };
  inventory.forEach(i => { topicCounts[i.topic] = (topicCounts[i.topic] || 0) + 1; });

  const topicOrder = [
    "All Topics","Price & Universe","Deals","Ownership & Insider",
    "Surveillance","Derivatives & Options","Institutional Flow",
    "Commodity / MCX / Global","Macro","News / Catalyst","Calendar / Regime"
  ];

  const el = document.getElementById("topic-list");
  el.innerHTML = topicOrder.map(topic => {
    const count = topicCounts[topic] || 0;
    const isActive = activeTopic === topic;
    return `<button class="topic-btn ${isActive ? 'active' : ''}" onclick="selectTopic('${topic}')">
      <span>${getTopicIcon(topic)} ${topic}</span>
      <span class="topic-count">${count}</span>
    </button>`;
  }).join("");
}

function getTopicIcon(topic) {
  return { "All Topics":"🌐","Price & Universe":"📈","Deals":"🤝","Ownership & Insider":"🏢",
    "Surveillance":"🛡️","Derivatives & Options":"⚡","Institutional Flow":"🏦",
    "Commodity / MCX / Global":"🛢️","Macro":"📊","News / Catalyst":"📰","Calendar / Regime":"🗓️"
  }[topic] || "📁";
}

function renderFieldTagCloud() {
  const fieldCounts = {};
  inventory.forEach(item => {
    (item.sample_fields || []).forEach(f => {
      if (f && f.length > 2 && f !== "null") fieldCounts[f] = (fieldCounts[f] || 0) + 1;
    });
  });

  const topFields = Object.entries(fieldCounts).sort((a,b) => b[1]-a[1]).slice(0,18).map(e => e[0]);
  const el = document.getElementById("field-cloud");
  el.innerHTML = topFields.map(field => {
    const isActive = activeTag === field;
    return `<span class="field-chip ${isActive ? 'active' : ''}" onclick="toggleFieldTag('${field}')">#${field}</span>`;
  }).join("");
}

function selectTopic(topic) {
  activeTopic = topic;
  renderSidebarTopics();
  applyFiltersAndRender();
}

function toggleFieldTag(field) {
  activeTag = (activeTag === field) ? null : field;
  renderFieldTagCloud();
  applyFiltersAndRender();
}

function filterKPI(type) {
  activeTopic = "All Topics"; activeTag = null; searchQuery = "";
  document.getElementById("search-input").value = "";
  renderSidebarTopics(); renderFieldTagCloud();

  activeStatus = "ALL";
  if (type === "STRONG") activeStatus = "STRONG";
  else if (type === "RESEARCH") { searchQuery = "LINKED_RESEARCH_SCREENER"; }
  else if (type === "EMPTY") activeStatus = "VALID_EMPTY";
  else if (type === "NEWS") activeStatus = "CONTEXT_NEWS";

  document.getElementById("status-filter").value = activeStatus;
  applyFiltersAndRender();
}

function setupEventListeners() {
  document.getElementById("search-input").addEventListener("input", e => {
    searchQuery = e.target.value.trim().toLowerCase();
    applyFiltersAndRender();
  });
  document.getElementById("status-filter").addEventListener("change", e => {
    activeStatus = e.target.value;
    applyFiltersAndRender();
  });
  document.getElementById("sort-select").addEventListener("change", e => {
    sortBy = e.target.value;
    applyFiltersAndRender();
  });
}

function setViewMode(mode) {
  viewMode = mode;
  document.getElementById("view-grid-btn").classList.toggle("active", mode === "grid");
  document.getElementById("view-table-btn").classList.toggle("active", mode === "table");
  applyFiltersAndRender();
}

function applyFiltersAndRender() {
  let filtered = inventory.filter(item => {
    if (activeTopic !== "All Topics" && item.topic !== activeTopic) return false;
    if (activeStatus !== "ALL") {
      if (activeStatus === "VALID_EMPTY") {
        if (!["VALID_EMPTY","SOFT_EMPTY","BLOCKED"].includes(item.status)) return false;
      } else if (item.status !== activeStatus) return false;
    }
    if (activeTag && (!(item.sample_fields||[]).includes(activeTag))) return false;
    if (searchQuery) {
      const q = searchQuery;
      const jsonStr = item.sample_row ? JSON.stringify(item.sample_row).toLowerCase() : "";
      const match = item.title.toLowerCase().includes(q) ||
        item.active_source_keys.toLowerCase().includes(q) ||
        item.canonical_url.toLowerCase().includes(q) ||
        item.topic.toLowerCase().includes(q) ||
        item.purpose_jobs.toLowerCase().includes(q) ||
        item.screener_integration.toLowerCase().includes(q) ||
        jsonStr.includes(q);
      if (!match) return false;
    }
    return true;
  });

  filtered.sort((a,b) => {
    if (sortBy === "usable_rows_desc") return b.usable_rows - a.usable_rows;
    if (sortBy === "row_no_asc") return a.row_no - b.row_no;
    if (sortBy === "title_asc") return a.title.localeCompare(b.title);
    return 0;
  });

  const rawMatchCount = filtered.length;
  const displayList = applyDuplicateCollapse(filtered);

  // When collapsed: show UNIQUE feeds first, then multi-link primaries (mirrors not full cards)
  displayList.sort((a, b) => {
    if (collapseDuplicates) {
      const aMulti = (a._groupSize || 1) > 1 ? 1 : 0;
      const bMulti = (b._groupSize || 1) > 1 ? 1 : 0;
      if (aMulti !== bMulti) return aMulti - bMulti; // unique (0) before multi (1)
    }
    if (sortBy === "usable_rows_desc") return b.usable_rows - a.usable_rows;
    if (sortBy === "row_no_asc") return a.row_no - b.row_no;
    if (sortBy === "title_asc") return a.title.localeCompare(b.title);
    return 0;
  });

  const uniqueShown = displayList.filter(i => (i._groupSize || 1) === 1).length;
  const multiShown = displayList.filter(i => (i._groupSize || 1) > 1).length;
  const hiddenTwins = Math.max(0, rawMatchCount - displayList.length);

  const container = document.getElementById("main-container");

  if (displayList.length === 0) {
    document.getElementById("results-count").textContent =
      `Showing 0 feeds (0 of ${inventory.length} contracts match filters)`;
    container.innerHTML = `<div style="text-align:center;padding:4rem 1rem;color:var(--text-muted);">
      <p style="font-size:2rem;margin-bottom:0.5rem;">🔍</p>
      <h3 style="color:#fff;margin-bottom:0.5rem;">No matching market sources found</h3>
      <p>Try clearing filters or adjusting your search.</p>
      <button class="btn btn-primary" style="margin-top:1rem;" onclick="resetAllFilters()">Reset Filters</button>
    </div>`;
    updateCollapseAllButton();
    return;
  }

  // Safe per-card render so one bad payload cannot truncate the whole grid
  let painted = 0;
  let paintErrors = 0;
  if (viewMode === "grid") {
    container.className = "cards-grid";
    container.innerHTML = displayList.map(item => {
      try {
        const html = renderCardHTML(item);
        painted++;
        return html;
      } catch (err) {
        paintErrors++;
        console.warn("[render] card failed row", item.row_no, err);
        return `<div class="source-card" data-row="${item.row_no}">
          <div class="card-title">#${item.row_no} ${escapeHTML(item.title || "")}</div>
          <div style="color:#fbbf24;font-size:0.8rem;">Preview render error — open Details. Data still in inventory.</div>
          <button class="btn" onclick="openDrawer(${item.row_no})">📄 Details</button>
        </div>`;
      }
    }).join("");
  } else {
    container.className = "";
    try {
      container.innerHTML = renderTableHTML(displayList);
      painted = displayList.length;
    } catch (err) {
      console.warn("[render] table failed", err);
      container.innerHTML = displayList.map(item => {
        painted++;
        return `<div class="source-card"><strong>#${item.row_no}</strong> ${escapeHTML(item.title || "")}
          <button class="btn" onclick="openDrawer(${item.row_no})">Details</button></div>`;
      }).join("");
    }
  }

  const domCards = container.querySelectorAll(".source-card, .table-view tbody tr").length;
  document.getElementById("results-count").textContent = collapseDuplicates
    ? `Showing ${displayList.length} feeds on page (painted ${domCards}) · ${uniqueShown} unique + ${multiShown} primary · hidden ${hiddenTwins} mirrors · inventory ${inventory.length}`
    : `Showing all ${displayList.length} of ${inventory.length} link contracts (painted ${domCards})`;

  if (paintErrors) {
    console.warn(`[render] ${paintErrors} card(s) used fallback; expected ${displayList.length}, painted ${domCards}`);
  }
  updateCollapseAllButton();
}

function resetAllFilters() {
  activeTopic = "All Topics"; activeStatus = "ALL"; activeTag = null; searchQuery = "";
  document.getElementById("search-input").value = "";
  document.getElementById("status-filter").value = "ALL";
  renderSidebarTopics(); renderFieldTagCloud(); applyFiltersAndRender();
}

// ======================================================================
// SMART PAYLOAD RENDERER
// Converts raw JSON into context-aware, human-readable market data tables
// ======================================================================

// Field label dictionary: raw key -> human-readable label
const FIELD_LABELS = {
  // Shared
  // Clean English keys (output by generator) — map to nice display labels
  // Identity
  Symbol: "Symbol", Company: "Company", ISIN: "ISIN", Series: "Series",
  Commodity: "Commodity", Contract: "Contract", Security: "Security",
  // Price
  "Open ₹": "Open ₹", "High ₹": "High ₹", "Low ₹": "Low ₹", "Close ₹": "Close ₹",
  "Last ₹": "Last Price ₹", "Prev Close ₹": "Prev Close ₹", "Strike ₹": "Strike ₹",
  "Settlement ₹": "Settlement ₹", "Benchmark Value": "Benchmark Value",
  // F&O / OI
  "Open Interest": "Open Interest", "OI Change": "OI Change", "Turnover Cr": "Turnover ₹ Cr",
  // Volume
  Volume: "Volume", "Traded Value": "Traded Value", Trades: "Trades",
  // Deals
  "Deal Date": "Deal Date", "Client Name": "Client Name", "Client": "Client",
  "Buy/Sell": "Buy / Sell", "Quantity Traded": "Quantity Traded",
  // FII/DII
  "Buy ₹ Cr": "Buy ₹ Cr", "Sell ₹ Cr": "Sell ₹ Cr", "Net ₹ Cr": "Net ₹ Cr",
  Category: "Category", Date: "Date",
  // CFTC
  "Market & Exchange": "Market & Exchange", "Report Date": "Report Date",
  "Report Week": "Report Week", "Open Interest (All)": "Open Interest (All)",
  "Non-Comm Long": "Non-Comm Long", "Non-Comm Short": "Non-Comm Short",
  "Commercial Long": "Commercial Long", "Commercial Short": "Commercial Short",
  "Dealer Long": "Dealer Long", "Dealer Short": "Dealer Short",
  "Asset Mgr Long": "Asset Mgr Long", "Asset Mgr Short": "Asset Mgr Short",
  "Leveraged Money Long": "Lev. Money Long", "Leveraged Money Short": "Lev. Money Short",
  "Δ Open Interest": "Change in OI", "Δ Non-Comm Long": "Chg Non-Comm Long",
  "Δ Non-Comm Short": "Chg Non-Comm Short",
  // Announcements
  Headline: "Headline / Subject", "Filing Text": "Filing Text",
  Description: "Description", "PDF Link": "PDF Link", "File Size": "File Size",
  Critical: "Critical News", "Scrip Code": "Scrip Code",
  // Corporate Actions
  "Book Closure Start": "Book Closure Start", "Book Closure End": "Book Closure End",
  "Broadcast Date": "Broadcast Date", "Ex-Date": "Ex-Date", "Face Value ₹": "Face Value ₹",
  "Record Date": "Record Date",
  // GSM/ASM Surveillance
  "GSM Stage": "GSM Stage", "Surv. Code": "Surveillance Code",
  Measure: "Measure", Stage: "Stage",
  // SLB
  "Open Positions": "Open Positions",
  // Equity Universe
  "Listing Date": "Listing Date", "Market Lot": "Market Lot", "Paid Up Value": "Paid Up Value",
  // Financial Results
  "Company": "Company", Audit: "Audit Status", Type: "Report Type",
  "Financial Year": "Financial Year", Filed: "Filed Date", "Period From": "Period From", "Period To": "Period To",
  // FRED / Macro
  "Real Yield 10Y (%)": "Real Yield 10Y (%)", "USD Index": "USD Index",
  // MCX
  Expiry: "Expiry", "Option Type": "Option Type", Unit: "Unit", "Turnover (L)": "Turnover (Lacs)",
  // Old API keys fallback (for any unprocessed rows)
  symbol: "Symbol", scripname: "Script Name", scrip_code: "Scrip Code", isin: "ISIN",
  SCRIP_CD: "Scrip Code", series: "Series", company: "Company", companyName: "Company",
  // OHLCV
  open: "Open ₹", high: "High ₹", low: "Low ₹", close: "Close ₹", ltp: "LTP ₹",
  lastPrice: "Last Price", previousClose: "Prev Close", prevClose: "Prev Close",
  prev_price: "Prev Price ₹", open_price: "Open ₹", high_price: "High ₹", low_price: "Low ₹",
  volume: "Volume", quantityTraded: "Volume", totalTradedVolume: "Volume",
  totalTradedValue: "Traded Value ₹", tradedValue: "Traded Value ₹",
  tradeCount: "Trade Count", tradeDate: "Trade Date",
  // Change
  change: "Change", pChange: "Chg %", net_price: "Chg %",
  // Derivatives
  underlying: "Underlying", contract: "Contract", instrument: "Instrument",
  instrumentType: "Instrument Type", expiryDate: "Expiry",
  optionType: "Option Type", strikePrice: "Strike Price ₹",
  openInterest: "Open Interest", latestOI: "Latest OI", prevOI: "Prev OI",
  oiChange: "OI Change", oiChangePercent: "OI Chg %", changeInOI: "OI Change",
  latestOi: "Latest OI", previousOi: "Prev OI",
  impliedVolatility: "IV %", delta: "Delta", gamma: "Gamma",
  premTurnover: "Prem Turnover Cr", futVolume: "Fut Volume", optVolume: "Opt Volume",
  // SLB
  openPositions: "Open Positions", borrowRate: "Borrow Rate %", turnover: "Turnover Cr",
  seriesCount: "Series Count", pressure: "Pressure",
  // Deals
  DEAL_DATE: "Deal Date", SCRIP_CODE: "Scrip Code",
  CLIENT_NAME: "Client Name", TRANSACTION_TYPE: "Txn Type",
  QUANTITY: "Quantity", PRICE: "Price ₹",
  dealType: "Deal Type", side: "Side", clientName: "Client Name",
  quantity: "Quantity", price: "Price ₹", date: "Date",
  // FII/DII
  dataDate: "Date", category: "Category",
  buyValueCrore: "Buy Cr ₹", sellValueCrore: "Sell Cr ₹", netValueCrore: "Net Cr ₹",
  // FPI
  netInvestmentCrore: "Net FPI Cr ₹", grossPurchaseCrore: "Gross Buy Cr",
  grossSalesCrore: "Gross Sell Cr", cumNetInvestment: "Cum Net Inv",
  // Pledges / shareholding
  Company_Name: "Company",
  shareholdername: "Shareholder", Acq_Sale: "Action",
  Acq_sale_qty: "Qty Changed", flag: "Regulation",
  promoterHoldingPercent: "Promoter Hold %",
  pledgedShares: "Pledged Shares", promoterEncumberedPercentOfTotal: "Encumbered %",
  // PIT / Insider
  entity: "Insider Entity", transactionType: "Transaction", value: "Value ₹", eventDate: "Event Date",
  // Surveillance
  measure: "Measure", stage: "Stage", code: "Code", description: "Description", effectiveDate: "Effective Date",
  // Gold / Commodity
  benchmark_value: "Benchmark Value", currency: "Currency",
  // Macro
  seriesId: "Series ID", observationDate: "Observation Date", units: "Units",
  // Calendar
  tradingDate: "Trading Date", weekDay: "Day", state: "Market State", exchange: "Exchange",
  segment: "Segment", listingDate: "Listing Date", industry: "Industry",
  indexMembership: "Index Membership", faceValue: "Face Value ₹",
  // --- CFTC COT fields ---
  market_and_exchange_names: "Market & Exchange",
  contract_market_name: "Contract",
  commodity_name: "Commodity",
  report_date_as_yyyy_mm_dd: "Report Date",
  yyyy_report_week_ww: "Report Week",
  open_interest_all: "Open Interest (All)",
  NonComm_Positions_Long_All: "Non-Commercial Long",
  NonComm_Positions_Short_All: "Non-Commercial Short",
  Comm_Positions_Long_All: "Commercial Long",
  Comm_Positions_Short_All: "Commercial Short",
  dealer_positions_long_all: "Dealer Long",
  dealer_positions_short_all: "Dealer Short",
  asset_mgr_positions_long: "Asset Mgr Long",
  asset_mgr_positions_short: "Asset Mgr Short",
  Lev_Money_Positions_Long_All: "Leveraged Money Long",
  Lev_Money_Positions_Short_All: "Leveraged Money Short",
  Change_in_Open_Interest_All: "Chg in OI (All)",
  Change_in_NonComm_Long_All: "Chg Non-Comm Long",
  Change_in_NonComm_Short_All: "Chg Non-Comm Short",
  // --- BSE/NSE Announcements (cleaned) ---
  headline: "Headline / Subject",
  critical: "Critical News",
  announcement_date: "Announced At",
  // NSE Announcements (cleaned)
  an_dt: "Announced At",
  attchmntText: "Filing Text",
  desc: "Description",
  smIndustry: "Industry",
  attFileSize: "File Size",
  attchmntFile: "PDF Link",
  pdf_link: "PDF Download Link",
  // NSE Corporate Actions (cleaned)
  actionType: "Action",
  actionClass: "Action Class",
  announcementDate: "Announced",
  exDate: "Ex-Date",
  recordDate: "Record Date",
  offerPrice: "Offer Price ₹",
  cashAmount: "Cash Amount ₹",
  // NSE Financial Results
  audited: "Audit Status", broadCastDate: "Broadcast Date", consolidated: "Type",
  financialYear: "Financial Year", filingDate: "Filed", fromDate: "Period From", toDate: "Period To",
  // Buyback
  last_updated: "Last Updated", status: "Status",
  // Financial results
  Fld_NameOfCompany: "Company",
  // AMFI / NAV
  schemeCode: "Scheme Code", schemeName: "Scheme Name", nav: "NAV",
  // Indices
  identifier: "Identifier", dayHigh: "Day High", dayLow: "Day Low",
  // Generic
  advanceState: "State", scope: "Data Scope", mode: "Mode"
};


// Fields to HIDE as internal/noise (old API keys — now cleaned, but keep as fallback)
const HIDE_FIELDS = new Set([
  "scope","mode","source","chart30Path","chart365Path","date30dAgo","date365dAgo",
  "ffmc","advanceState","metadata","Fld_CompanyId","preti",
  "PreStatus","cum_net_investment","difference","exchdisstime","week1volChange",
  "week2volChange","week1AvgVolume","week2AvgVolume","identifier",
  // CFTC internal noise
  "id","cftc_contract_market_code","cftc_market_code","cftc_region_code",
  "cftc_commodity_code","report_date_as_mm_dd_yyyy","contract_units",
  "as_of_date_in_form_yymmdd",
  // BSE/NSE announcement internal IDs
  "NEWSID","XML_NAME","FILESTATUS","ATTACHMENTNAME","MORE","RN",
  "ANNOUNCEMENT_TYPE","QUARTER_ID","bflag","csvName","hasXbrl","old_new",
  "orgid","seq_id","fileSize","dt",
  // Corporate actions internal noise
  "predecessorSymbol","successorSymbol","continuityConfirmed","revisionStatus",
  "priceAdjustmentFactor","ratioNumerator","ratioDenominator",
  // Financial results internal
  "bank","cumulative","format","indAs","oldNewFlag",
  // Sgmt/Source internal codes
  "Sgmt", "Src", "Inst Type", "Biz Date",
  // NSE extra internal
  "Sr No"
]);


// Fields that represent money/price (₹ or foreign currency) — both old and new clean keys
const PRICE_FIELDS = new Set([
  // Old API keys
  "open","high","low","close","ltp","lastPrice","previousClose","prevClose","prev_price",
  "open_price","high_price","low_price","price","PRICE","value","benchmark_value",
  "buyValueCrore","sellValueCrore","netValueCrore","netInvestmentCrore","grossPurchaseCrore",
  "grossSalesCrore","cumNetInvestment","nav","dayHigh","dayLow","strikePrice",
  // New clean English keys
  "Open ₹","High ₹","Low ₹","Close ₹","Last ₹","Prev Close ₹","Strike ₹",
  "Settlement ₹","Benchmark Value","Buy ₹ Cr","Sell ₹ Cr","Net ₹ Cr",
  "Face Value ₹","Cash Amount ₹","Offer Price ₹","NAV"
]);

// Fields that represent percentage
const PCT_FIELDS = new Set([
  "pChange","oiChangePercent","borrowRate","promoterHoldingPercent",
  "promoterEncumberedPercentOfTotal","net_price","impliedVolatility",
  "Real Yield 10Y (%)","Borrow Rate %"
]);

// Fields that are datetime/date strings  
const DATE_FIELDS = new Set([
  // Old API
  "DEAL_DATE","date","tradeDate","dataDate","eventDate","effectiveDate","tradingDate",
  "listingDate","observationDate","filingDate","broadCastDate","expiryDate","Acquisition_date",
  // New clean English
  "Date","Deal Date","Report Date","Trade Date","Listing Date","Broadcast Date",
  "Ex-Date","Record Date","Filed","Period From","Period To","Expiry","Last Updated"
]);

function formatFieldValue(key, value) {
  if (value === null || value === undefined || value === "") return "—";

  // Boolean
  if (typeof value === "boolean") return value ? "✓ Yes" : "✗ No";

  // Arrays first (typeof array === "object")
  if (Array.isArray(value)) {
    if (value.length === 0) return "[]";
    if (value.length <= 3 && value.every(v => typeof v !== "object" || v === null)) {
      return escapeHTML(value.map(String).join(", "));
    }
    return `[${value.length} items]`;
  }

  // Nested plain objects – briefly summarise (never throw on null — already excluded)
  if (typeof value === "object") {
    try {
      const keys = Object.keys(value);
      if (keys.length === 0) return "{}";
      return `{${keys.slice(0, 3).map(k => escapeHTML(k)).join(", ")}…}`;
    } catch (_) {
      return "[object]";
    }
  }

  const strVal = String(value);

  // PDF/URL fields — render as clickable link
  if (key === "pdf_link" || key === "attchmntFile" || key === "PDF Link") {
    if (strVal.startsWith("http")) {
      const fname = strVal.split("/").pop().slice(0, 40);
      return `<a href="${escapeHTML(strVal)}" target="_blank" rel="noopener" style="color:var(--accent-blue);word-break:break-all;">&#128196; ${escapeHTML(fname)}</a>`;
    }
    return escapeHTML(strVal);
  }

  // Long news text (headline, description, attchmntText) — wrap fully, no truncation
  if (["headline","description","attchmntText","desc","Headline","Filing Text","Description"].includes(key)) {
    return `<span style="white-space:normal;word-break:break-word;font-family:var(--font-sans);font-size:0.8rem;color:#e2e8f0;">${escapeHTML(strVal)}</span>`;
  }

  // Date detection
  if (DATE_FIELDS.has(key) || /^\d{4}-\d{2}-\d{2}/.test(strVal)) {
    try {
      const d = new Date(strVal);
      if (!isNaN(d)) {
        return d.toLocaleDateString("en-IN", { day:"2-digit", month:"short", year:"numeric" });
      }
    } catch(e) {}
    return strVal;
  }

  // Percentage fields
  if (PCT_FIELDS.has(key) && typeof value === "number") {
    const sign = value > 0 ? "+" : "";
    const cls = value > 0 ? "val-pos" : value < 0 ? "val-neg" : "";
    return `<span class="${cls}">${sign}${value.toFixed(2)}%</span>`;
  }

  // Large number formatting
  if (typeof value === "number") {
    if (Math.abs(value) >= 1e9) return (value/1e9).toFixed(2) + " B";
    if (Math.abs(value) >= 1e7) return (value/1e7).toFixed(2) + " Cr";
    if (Math.abs(value) >= 1e5) return value.toLocaleString("en-IN");
    if (Number.isInteger(value)) return value.toLocaleString("en-IN");
    return value.toFixed(2);
  }

  // TRANSACTION_TYPE code expansions
  if (key === "TRANSACTION_TYPE") return strVal === "P" ? "BUY (Purchase)" : strVal === "S" ? "SELL" : strVal;
  if (key === "Acq_Sale") return strVal === "SAL" ? "SALE" : strVal;

  // Long strings: truncate to 80 chars for most fields
  if (strVal.length > 80) return escapeHTML(strVal.slice(0, 80)) + "…";

  return escapeHTML(strVal);
}


function getFieldLabel(key) {
  return FIELD_LABELS[key] || key.replace(/_/g," ").replace(/([A-Z])/g," $1").trim();
}

/**
 * Best flat sample for card/table display.
 * Prefers records_sample[0] when sample_row is a nested wrapper (metadata/detail, rows[], buckets).
 * Does not invent fields — only unwraps existing structure.
 */
function getDisplaySample(item) {
  const rs0 = (item.records_sample && item.records_sample[0]) || null;
  let sr = item.sample_row;

  // Prefer flat holdings row over AMFI fund wrapper { rows: [...] }
  if (sr && typeof sr === "object" && !Array.isArray(sr) && Array.isArray(sr.rows) && rs0 && !rs0.rows) {
    sr = rs0;
  }
  // Prefer first real sample when sample_row missing
  if (!sr && rs0) sr = rs0;

  if (!sr) return null;
  if (typeof sr === "string") {
    try { sr = JSON.parse(sr); } catch (_) { return { _raw: sr }; }
  }
  if (Array.isArray(sr) && sr[0] && typeof sr[0] === "object") sr = sr[0];
  if (!sr || typeof sr !== "object" || Array.isArray(sr)) return null;

  // Pre-open nested API shape
  if (sr.metadata && typeof sr.metadata === "object") {
    const meta = sr.metadata || {};
    const detail = (sr.detail && typeof sr.detail === "object") ? sr.detail : {};
    const pre = detail.preOpenMarket || detail.preopen || {};
    const iep = pre.IEP != null ? pre.IEP : (meta.iep != null ? meta.iep : pre.iep);
    const prev = meta.previousClose != null ? meta.previousClose : pre.previousClose;
    let gap = null;
    if (iep != null && prev != null && Number(prev) !== 0) {
      gap = ((Number(iep) - Number(prev)) / Number(prev)) * 100;
    }
    return {
      symbol: meta.symbol || "",
      series: meta.series || "",
      lastPrice: meta.lastPrice,
      pChange: meta.pChange,
      change: meta.change,
      previousClose: prev,
      iep,
      gapPercent: gap != null && !isNaN(gap) ? Number(gap.toFixed(4)) : null,
      finalQuantity: meta.finalQuantity,
      totalTurnover: meta.totalTurnover
    };
  }

  // Market turnover nested today/yesterday
  if ((sr.today && typeof sr.today === "object") || (sr.yesterday && typeof sr.yesterday === "object")) {
    const t = sr.today || {};
    const y = sr.yesterday || {};
    return {
      segment: sr.name || sr.segment || "",
      todayVolume: t.volume, todayValue: t.value, todayOI: t.openInterest,
      yestVolume: y.volume, yestValue: y.value, yestOI: y.openInterest
    };
  }

  // OI spurts contract buckets: { "Slide-in-OI-Slide": [ {...}, ... ] }
  const bucketKeys = Object.keys(sr);
  if (bucketKeys.length && bucketKeys.every(k => Array.isArray(sr[k]))) {
    for (const k of bucketKeys) {
      if (sr[k].length && typeof sr[k][0] === "object") {
        return Object.assign({ _bucket: k }, sr[k][0]);
      }
    }
  }

  // AMFI wrapper still present
  if (Array.isArray(sr.rows) && sr.rows[0] && typeof sr.rows[0] === "object") {
    return Object.assign({
      mfId: sr.mfId, mfName: sr.mfName
    }, sr.rows[0]);
  }

  return sr;
}

function renderPayloadTable(item) {
  const status = item.status;
  const dataObj = getDisplaySample(item);

  // No data cases
  if (!dataObj) {
    return renderEmptyPayload(status);
  }

  if (dataObj._raw && typeof dataObj._raw === "string") {
    return `<div class="payload-table-wrap">
      <div class="payload-note">⚠ Partial payload (truncated JSON):</div>
      <pre class="payload-raw">${escapeHTML(dataObj._raw.slice(0, 300))}</pre>
    </div>`;
  }

  // If it's a flat object (most common case)
  if (dataObj && typeof dataObj === "object" && !Array.isArray(dataObj)) {
    return renderFlatObjectTable(dataObj, item);
  }

  return renderEmptyPayload(status);
}

function renderFlatObjectTable(obj, item) {
  const rows = [];
  let keyGroups;
  try {
    keyGroups = groupFieldsByCategory(obj, item);
  } catch (err) {
    console.warn("[payload] groupFields failed", item.row_no, err);
    keyGroups = { "📋 Other": Object.entries(obj || {}) };
  }

  for (const [groupName, groupFields] of Object.entries(keyGroups)) {
    if (!groupFields || groupFields.length === 0) continue;

    // Group header
    rows.push(`<tr class="payload-group-header"><td colspan="2">${escapeHTML(groupName)}</td></tr>`);

    for (const pair of groupFields) {
      const key = pair[0];
      const value = pair[1];
      if (HIDE_FIELDS.has(key)) continue;
      if (value === null || value === undefined || value === "") continue;

      const label = getFieldLabel(key);
      let formattedVal;
      try {
        formattedVal = formatFieldValue(key, value);
      } catch (_) {
        formattedVal = escapeHTML(String(value));
      }

      // Highlight important/primary fields
      const isPrimary = isPrimaryField(key);
      rows.push(`<tr class="${isPrimary ? 'payload-row-primary' : 'payload-row'}">
        <td class="payload-key">${escapeHTML(label)}</td>
        <td class="payload-val">${formattedVal}</td>
      </tr>`);
    }
  }

  if (rows.length === 0) return renderEmptyPayload(item.status);

  const rowCount = Number(item.usable_rows) || (item.records_sample || []).length || 1;
  const dateStr = item.data_date != null ? String(item.data_date) : "latest";
  return `<div class="payload-table-wrap">
    <div class="payload-meta">Sample row 1 of ${rowCount.toLocaleString("en-IN")} records · ${escapeHTML(dateStr)}</div>
    <table class="payload-table">${rows.join("")}</table>
  </div>`;
}

function groupFieldsByCategory(obj, item) {
  const key = item.active_source_keys;

  const groups = {
    "🏷 Identity & Symbol": [],
    "📰 News & Announcement": [],
    "🌍 COT Positions": [],
    "📋 Corporate Action": [],
    "💰 Price & OHLCV": [],
    "📊 Volume & Turnover": [],
    "⚡ Open Interest": [],
    "📈 Change": [],
    "🗓 Date & Time": [],
    "👤 Party / Entity": [],
    "🔍 Regulatory / Notes": [],
    "📋 Other": []
  };

  // CFTC detection — check both old API keys AND new clean keys
  const isCFTC = key.toLowerCase().includes('cftc') ||
    ('Market & Exchange' in obj) || ('Open Interest (All)' in obj);
  // News detection — check clean English keys AND old API keys
  const isNews = 'Headline' in obj || 'headline' in obj || 'NEWSSUB' in obj ||
    'Filing Text' in obj || 'attchmntText' in obj;
  // Corporate Actions detection — clean keys
  const isCorporateAction = 'Ex-Date' in obj || 'Book Closure Start' in obj ||
    'actionType' in obj || 'Action Type' in obj;

  for (const [k, v] of Object.entries(obj)) {
    if (HIDE_FIELDS.has(k)) continue;
    if (v === null || v === undefined || v === '' || v === '-' || v === 'null') continue;

    // --- CFTC routing (clean English keys) ---
    if (isCFTC) {
      if (['Market & Exchange','Contract','Commodity','Report Date','Report Week','Open Interest (All)',
           'market_and_exchange_names','contract_market_name','commodity_name',
           'report_date_as_yyyy_mm_dd','yyyy_report_week_ww','open_interest_all'].includes(k)) {
        groups["🏷 Identity & Symbol"].push([k, v]);
      } else if (k.includes('Long') || k.includes('Short') || k.includes('Δ') ||
                 k.includes('positions') || k.includes('Positions') || k.includes('Change_in')) {
        groups["🌍 COT Positions"].push([k, v]);
      } else if (DATE_FIELDS.has(k) || k.includes('Date') || k.includes('Week')) {
        groups["🗓 Date & Time"].push([k, v]);
      } else {
        groups["📋 Other"].push([k, v]);
      }
      continue;
    }

    // --- News / Announcements routing (clean English keys) ---
    if (isNews) {
      if (['Headline','headline','Filing Text','Description','NEWSSUB','attchmntText','desc'].includes(k)) {
        groups["📰 News & Announcement"].push([k, v]);
      } else if (['Date','announcement_date','an_dt','DT_TM','NEWS_DT'].includes(k) || DATE_FIELDS.has(k)) {
        groups["🗓 Date & Time"].push([k, v]);
      } else if (['Scrip Code','scrip_code','SCRIP_CD','company','Company'].includes(k)) {
        groups["🏷 Identity & Symbol"].push([k, v]);
      } else if (['Category','Critical','Industry','category','CATEGORYNAME','critical','industry'].includes(k)) {
        groups["🔍 Regulatory / Notes"].push([k, v]);
      } else if (['PDF Link','File Size','pdf_link','attchmntFile','file_size','attFileSize'].includes(k)) {
        groups["📋 Corporate Action"].push([k, v]);
      } else {
        groups["📋 Other"].push([k, v]);
      }
      continue;
    }

    // --- Corporate Actions routing (clean English keys) ---
    if (isCorporateAction) {
      if (['Symbol','Company','ISIN','symbol','company','isin'].includes(k)) {
        groups["🏷 Identity & Symbol"].push([k, v]);
      } else if (['Ex-Date','Record Date','Book Closure Start','Book Closure End',
                  'Broadcast Date','exDate','recordDate','announcementDate'].includes(k) || DATE_FIELDS.has(k)) {
        groups["🗓 Date & Time"].push([k, v]);
      } else if (['Action Type','actionType','actionClass','Cash Amount ₹','cashAmount',
                  'Face Value ₹','faceVal','faceValue','Series','series'].includes(k)) {
        groups["📋 Corporate Action"].push([k, v]);
      } else {
        groups["📋 Other"].push([k, v]);
      }
      continue;
    }

    // --- Standard field routing — both old API keys AND new clean English keys ---
    const kl = k.toLowerCase();
    if (["Symbol","Company","Security","ISIN","Series","Commodity","Contract",
         "symbol","scripname","scrip_code","SCRIP_CODE","SCRIP_CD","isin","series",
         "company","companyName","underlying","contract","instrument","instrumentType",
         "name","exchange","segment","measure","Measure","stage","Stage",
         "GSM Stage","Surv. Code","Description","description","code"].includes(k)) {
      groups["🏷 Identity & Symbol"].push([k, v]);
    } else if (["Open ₹","High ₹","Low ₹","Close ₹","Last ₹","Prev Close ₹","Strike ₹",
                "Settlement ₹","Benchmark Value","NAV",
                "open","high","low","close","ltp","lastPrice","previousClose","prevClose",
                "open_price","high_price","low_price","prev_price","price","PRICE",
                "strikePrice","benchmark_value","nav","dayHigh","dayLow","borrowRate",
                "Real Yield 10Y (%)","USD Index","DFII10","DTWEXBGS"].includes(k)) {
      groups["💰 Price & OHLCV"].push([k, v]);
    } else if (["Volume","Traded Value","Trades","Open Positions","Turnover Cr","Turnover (Lacs)",
                "Buy ₹ Cr","Sell ₹ Cr","Net ₹ Cr",
                "volume","quantityTraded","totalTradedVolume","QUANTITY","quantity",
                "openPositions","seriesCount","futVolume","optVolume",
                "totalTradedValue","tradedValue","turnover","premTurnover",
                "buyValueCrore","sellValueCrore","netValueCrore",
                "netInvestmentCrore","grossPurchaseCrore","grossSalesCrore"].includes(k)) {
      groups["📊 Volume & Turnover"].push([k, v]);
    } else if (["Open Interest","OI Change",
                "openInterest","latestOI","prevOI","latestOi","previousOi","oiChange",
                "oiChangePercent","changeInOI"].includes(k)) {
      groups["⚡ Open Interest"].push([k, v]);
    } else if (["change","pChange","net_price","oiChangePercent"].includes(k)) {
      groups["📈 Change"].push([k, v]);
    } else if (DATE_FIELDS.has(k) || k.includes('Date') || k.includes('date') ||
               k.includes('Time') || k.includes('Expiry') || k.includes('Listing')) {
      groups["🗓 Date & Time"].push([k, v]);
    } else if (["Client Name","Client","Buy/Sell","Quantity Traded","Category",
                "CLIENT_NAME","clientName","entity","Acq_Sale","shareholdername",
                "promoterHoldingPercent","pledgedShares","Option Type",
                "promoterEncumberedPercentOfTotal","Acq_sale_qty","flag",
                "transactionType","dealType","side","category","optionType",
                "TRANSACTION_TYPE","weekDay","state","audited","consolidated",
                "financialYear","Financial Year","Audit Status","Report Type"].includes(k)) {
      groups["👤 Party / Entity"].push([k, v]);
    } else if (["Paid Up Value","Market Lot","Face Value ₹","Industry","Unit",
                "measure","stage","code","description","effectiveDate","industry",
                "indexMembership","faceValue","listingDate","pressure",
                "seriesId","units"].includes(k)) {
      groups["🔍 Regulatory / Notes"].push([k, v]);
    } else {
      groups["📋 Other"].push([k, v]);
    }
  }

  // Remove empty groups
  return Object.fromEntries(Object.entries(groups).filter(([,v]) => v.length > 0));
}


function isPrimaryField(key) {
  // Primary = most important field to highlight — both old API keys AND new clean keys
  return [
    // Old API
    "symbol","underlying","ltp","lastPrice","close","netValueCrore","openInterest",
    "latestOI","latestOi","benchmark_value","PRICE","price","dealType","category",
    "measure","nav","value","stage","contract_market_name","open_interest_all","commodity_name",
    "headline","announcement_date","actionType","cashAmount","companyName","financialYear",
    // New clean English
    "Symbol","Company","Commodity","Contract","Security","Category","GSM Stage",
    "Headline","Filing Text","Open Interest (All)","Net ₹ Cr","Benchmark Value",
    "Close ₹","Ex-Date","Action Type","Financial Year","Real Yield 10Y (%)",
    "USD Index","Measure","Stage","Open Positions"
  ].includes(key);
}


function renderEmptyPayload(status) {
  const msgs = {
    VALID_EMPTY: "✓ Connected — 0 rows right now (valid empty contract, not a failure)",
    SOFT_EMPTY: "⚪ Endpoint returned empty structure (e.g. option chain {} — no events today)",
    BLOCKED: "🔒 Access blocked (WAF challenge) — endpoint exists but cannot download",
    PROVENANCE: "🔗 Navigation / provenance web page — see linked API endpoint for raw data",
    CONTEXT_NEWS: "📰 News & announcement feed — text metadata only, no market price rows",
    COMPANION: "🔄 Companion / backup feed — primary rows in matched DIRECT source above"
  };
  const msg = msgs[status] || "No sample payload available.";
  return `<div class="payload-empty"><span>${msg}</span></div>`;
}

// ======================================================================
// CARD & TABLE RENDERING
// ======================================================================

function renderCardHTML(item) {
  const fields = (item.sample_fields || []).slice(0, 4);
  const fieldsHTML = fields.map(f => `<span class="field-pill">${escapeHTML(f)}</span>`).join("");
  const payloadHTML = renderPayloadTable(item);
  
  const provLink = item.provenance_url ?
    `<button class="btn" style="padding:0.25rem 0.5rem;font-size:0.725rem;" onclick="openDrawer(${item.row_no})" title="View linked provenance/API pair">🔗 Pair</button>` : "";

  const shortUrl = String(item.canonical_url || "").replace(/^https?:\/\/(www\.)?/, "").slice(0, 55) || "—";
  const effBadge = isApiLikeUrl(item.canonical_url)
    ? `<span class="eff-badge eff-fast" title="API/file feed · preferred for automation">⚡ API</span>`
    : (isSlowNavUrl(item.canonical_url)
      ? `<span class="eff-badge eff-slow" title="HTML navigation page · slower / not primary fetch">🌐 NAV</span>`
      : `<span class="eff-badge" title="Feed URL">LINK</span>`);

  const groupBadge = (item._groupSize || 1) > 1
    ? `<span class="eff-badge eff-group" title="This is the strongest/fastest URL for this feed. ${item._groupSize - 1} weaker mirror URL(s) folded under hints.">PRIMARY · ${item._groupSize}×</span>`
    : `<span class="eff-badge eff-unique" title="Only one inventory contract for this feed — unique data source">UNIQUE</span>`;

  // Stock symbols preview chips strip
  const entities = item.entity_list || [];
  const entityCount = item.entity_count || entities.length;
  let stockChipsHTML = "";

  if (entities.length > 0) {
    const top6 = entities.slice(0, 6);
    const remaining = entityCount - top6.length;
    const chips = top6.map(s => 
      `<span class="stock-pill" onclick="openExplorer(${item.row_no}, '${escapeJS(s)}')" title="Filter dataset by ${escapeHTML(s)}">${escapeHTML(s)}</span>`
    ).join("");

    const moreChip = remaining > 0 ? 
      `<span class="stock-more-chip" onclick="openExplorer(${item.row_no})" title="View all ${entityCount} stocks">+${remaining} more</span>` : "";

    stockChipsHTML = `
      <div class="stock-chips-box">
        <div class="stock-chips-header">
          <span>📌 Stocks / Entities (${entityCount.toLocaleString("en-IN")})</span>
          <span style="color:var(--accent-blue);cursor:pointer;" onclick="openExplorer(${item.row_no})">Expand All ↗</span>
        </div>
        <div class="stock-chips-list">${chips}${moreChip}</div>
      </div>`;
  }

  const twinHints = collapseDuplicates ? renderTwinHintsHTML(item) : "";
  const twinSearchNote = item._twinSearchHit
    ? `<div class="twin-search-note">Search matched a mirror link · showing primary feed #${item.row_no}</div>`
    : "";

  const usableSafe = Number(item.usable_rows);
  const usableLabel = Number.isFinite(usableSafe) ? usableSafe.toLocaleString("en-IN") : "—";
  const sampleN = (item.records_sample || []).length;
  const dateLabel = item.data_date != null
    ? escapeHTML(String(item.data_date).slice(0, 24).replace(/^.*?:/, "").trim() || String(item.data_date).slice(0, 10))
    : "";
  const safeUrl = item.canonical_url || "#";
  const cardCollapsed = collapsedCardRows.has(Number(item.row_no));

  return `<div class="source-card ${ (item._groupSize || 1) > 1 ? "has-twins" : "" } ${cardCollapsed ? "is-collapsed" : ""}" data-row="${item.row_no}" data-key="${escapeHTML(primarySourceKey(item))}">
    <button type="button" class="card-collapse-toggle" onclick="toggleSourceCard(${item.row_no})"
      aria-expanded="${cardCollapsed ? "false" : "true"}"
      aria-label="${cardCollapsed ? "Maximize" : "Minimize"} ${escapeHTML(item.title || "source card")}"
      title="${cardCollapsed ? "Maximize card" : "Minimize card"}">${cardCollapsed ? "⌄" : "⌃"}</button>
    <div class="card-top">
      <span class="row-num">#${item.row_no}</span>
      <span class="topic-badge">${escapeHTML(item.topic || "")}</span>
      <span class="status-chip status-${escapeHTML(item.status || "STRONG")}">${escapeHTML(item.status || "")}</span>
      ${effBadge}
      ${groupBadge}
    </div>

    <div>
      <div class="card-title">${escapeHTML(item.title || "")}</div>
      <span class="source-key-tag">${escapeHTML(item.active_source_keys || "")}</span>
    </div>

    <div class="card-collapsible">
    <div class="url-box">
      <span class="url-text" title="${escapeHTML(safeUrl)}">${escapeHTML(shortUrl)}</span>
      <div class="url-actions">
        <button class="icon-btn" onclick="copyToClipboard('${escapeJS(safeUrl)}')" title="Copy URL">📋</button>
        <a href="${escapeHTML(safeUrl)}" target="_blank" rel="noopener" class="icon-btn" title="Open in browser">↗</a>
      </div>
    </div>

    <div class="meta-stats">
      <div class="meta-item"><span>Total Rows:</span><span class="meta-val">${usableLabel}</span></div>
      <div class="meta-item"><span>Sample:</span><span class="meta-val">${sampleN}</span></div>
      ${dateLabel ? `<div class="meta-item"><span>Date:</span><span class="meta-val">${dateLabel}</span></div>` : ""}
    </div>

    ${twinSearchNote}
    ${twinHints}

    ${stockChipsHTML}

    ${fieldsHTML ? `<div class="sample-fields-preview">${fieldsHTML}</div>` : ""}

    ${payloadHTML}

    <div class="card-footer">
      <button class="btn btn-primary" style="padding:0.35rem 0.8rem;font-size:0.8rem;background:linear-gradient(135deg,#059669,#10b981);" onclick="openExplorer(${item.row_no})">
        🔍 Explore All ${item.usable_rows > 1 ? item.usable_rows.toLocaleString("en-IN") : ""} Rows
      </button>
      <div style="display:flex;gap:0.3rem;">
        <button class="btn" style="padding:0.25rem 0.5rem;font-size:0.725rem;" onclick="openDrawer(${item.row_no})">
          📄 Details
        </button>
        <button class="btn" style="padding:0.25rem 0.5rem;font-size:0.725rem;" onclick="openCodeModal(${item.row_no})" title="Get Python / cURL fetch snippet">
          🐍 Code
        </button>
        ${provLink}
      </div>
    </div>
    </div>
  </div>`;
}

function getPrimaryCardRows() {
  return Array.from(sourceGroups.values())
    .map(group => Number(group && group.champion && group.champion.row_no))
    .filter(Number.isFinite);
}

function setSourceCardCollapsed(rowNo, collapsed) {
  const row = Number(rowNo);
  if (!Number.isFinite(row)) return false;
  if (collapsed) collapsedCardRows.add(row);
  else collapsedCardRows.delete(row);

  const card = document.querySelector(`.source-card[data-row="${row}"]`);
  if (card) {
    card.classList.toggle("is-collapsed", collapsed);
    const button = card.querySelector(".card-collapse-toggle");
    if (button) {
      button.textContent = collapsed ? "⌄" : "⌃";
      button.setAttribute("aria-expanded", collapsed ? "false" : "true");
      button.setAttribute("aria-label", `${collapsed ? "Maximize" : "Minimize"} source card #${row}`);
      button.title = collapsed ? "Maximize card" : "Minimize card";
    }
  }
  return collapsed;
}

function updateCollapseAllButton() {
  const button = document.getElementById("collapse-all-cards-btn");
  if (!button) return;
  const primaryRows = getPrimaryCardRows();
  const allCollapsed = primaryRows.length > 0 && primaryRows.every(row => collapsedCardRows.has(row));
  const count = primaryRows.length;
  const gridActive = viewMode === "grid";

  button.disabled = !gridActive || count === 0;
  button.textContent = allCollapsed ? `⌄ Maximize all ${count}` : `⌃ Minimize all ${count}`;
  button.setAttribute("aria-pressed", allCollapsed ? "true" : "false");
  button.setAttribute("aria-label", `${allCollapsed ? "Maximize" : "Minimize"} all ${count} primary feed cards`);
  button.title = gridActive
    ? `${allCollapsed ? "Maximize" : "Minimize"} all ${count} primary feed cards`
    : "Available in Cards view";
}

function toggleSourceCard(rowNo) {
  const row = Number(rowNo);
  if (!Number.isFinite(row)) return false;
  const collapsed = setSourceCardCollapsed(row, !collapsedCardRows.has(row));
  updateCollapseAllButton();
  return collapsed;
}

function toggleAllSourceCards() {
  if (viewMode !== "grid") return false;
  const primaryRows = getPrimaryCardRows();
  if (!primaryRows.length) return false;
  const collapse = !primaryRows.every(row => collapsedCardRows.has(row));
  primaryRows.forEach(row => setSourceCardCollapsed(row, collapse));
  updateCollapseAllButton();
  return collapse;
}

if (typeof window !== "undefined") {
  window.toggleSourceCard = toggleSourceCard;
  window.toggleAllSourceCards = toggleAllSourceCards;
}

function renderTableHTML(items) {
  const rows = items.map(item => {
    const twinNote = (item._twins && item._twins.length)
      ? `<div style="font-size:0.68rem;color:#64748b;margin-top:2px;">+${item._twins.length} mirror hint(s)${item._verifiedSame ? " · ✓ same sample" : ""}</div>`
      : "";
    const eff = isApiLikeUrl(item.canonical_url) ? "⚡" : (isSlowNavUrl(item.canonical_url) ? "🌐" : "");
    return `<tr>
    <td style="font-family:var(--font-mono);font-weight:bold;">#${item.row_no}</td>
    <td><span class="status-chip status-${item.status}">${item.status}</span> ${eff}</td>
    <td>
      <div style="font-weight:600;color:#fff;">${escapeHTML(item.title)}</div>
      <span class="source-key-tag">${escapeHTML(item.active_source_keys)}</span>
      ${twinNote}
    </td>
    <td><span class="topic-badge">${item.topic}</span></td>
    <td style="font-family:var(--font-mono);text-align:right;font-weight:bold;">${item.usable_rows.toLocaleString("en-IN")}</td>
    <td style="font-family:var(--font-mono);font-size:0.75rem;max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
      ${escapeHTML(item.canonical_url)}
    </td>
    <td>
      <button class="btn btn-primary" style="padding:0.25rem 0.6rem;font-size:0.75rem;background:linear-gradient(135deg,#059669,#10b981);" onclick="openExplorer(${item.row_no})">🔍 Expand All</button>
      <button class="btn" style="padding:0.25rem 0.6rem;font-size:0.75rem;" onclick="openDrawer(${item.row_no})">Details</button>
      <button class="btn" style="padding:0.25rem 0.5rem;font-size:0.75rem;" onclick="openCodeModal(${item.row_no})">🐍 Code</button>
    </td>
  </tr>`;
  }).join("");

  return `<table class="table-view">
    <thead><tr>
      <th>Row</th><th>Status</th><th>Source / Key</th>
      <th>Topic</th><th style="text-align:right;">Rows</th>
      <th>URL</th><th>Actions</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

// ======================================================================
// STOCK & DATASET EXPLORER DRAWER — Schema-Driven (inventory-count aware)
// ======================================================================

let currentExplorerItem = null;
let currentExplorerFilter = "";
let currentExplorerStock = null;

function openExplorer(rowNo, filterStock = null) {
  const item = inventory.find(i => i.row_no === rowNo);
  if (!item) return;

  currentExplorerItem = item;
  currentExplorerFilter = filterStock || "";
  currentExplorerStock = filterStock || null;

  document.getElementById("explorer-row-num").textContent = `#${item.row_no}`;
  document.getElementById("explorer-title").textContent = item.title;
  document.getElementById("explorer-subtitle").textContent =
    `${item.topic} · ${item.usable_rows.toLocaleString("en-IN")} Total Records · ${item.status}`;
  document.getElementById("explorer-search-input").value = currentExplorerFilter;
  document.getElementById("explorer-entity-total").textContent = (item.entity_list || []).length;

  const searchEl = document.getElementById("explorer-search-input");
  searchEl.oninput = (e) => {
    currentExplorerFilter = e.target.value.trim().toLowerCase();
    currentExplorerStock = null;
    updateExplorerContent();
  };

  renderExplorerStockCloud(item);
  updateExplorerContent();

  document.getElementById("explorer-backdrop").classList.add("active");
  document.getElementById("explorer-drawer").classList.add("active");
}

function closeExplorer() {
  document.getElementById("explorer-backdrop").classList.remove("active");
  document.getElementById("explorer-drawer").classList.remove("active");
  currentExplorerItem = null;
}

function renderExplorerStockCloud(item) {
  const cloudEl = document.getElementById("explorer-stock-cloud");
  const entities = item.entity_list || [];
  if (entities.length === 0) {
    cloudEl.innerHTML = `<span style="font-size:0.75rem;color:var(--text-dim);font-style:italic;">No distinct stock symbols indexed for this source type.</span>`;
    return;
  }
  const chips = entities.slice(0, 150).map(stock => {
    const isActive = currentExplorerStock === stock;
    return `<span class="stock-pill ${isActive ? 'active' : ''}" onclick="filterExplorerByStock('${escapeJS(stock)}')">${escapeHTML(stock)}</span>`;
  }).join("");
  const more = entities.length > 150
    ? `<span style="font-size:0.7rem;color:var(--text-dim);padding:0.2rem;">+${entities.length - 150} more</span>`
    : "";
  cloudEl.innerHTML = chips + more;
}

function filterExplorerByStock(stock) {
  if (currentExplorerStock === stock) {
    currentExplorerStock = null;
    currentExplorerFilter = "";
  } else {
    currentExplorerStock = stock;
    currentExplorerFilter = stock.toLowerCase();
  }
  document.getElementById("explorer-search-input").value = currentExplorerStock || "";
  renderExplorerStockCloud(currentExplorerItem);
  updateExplorerContent();
}

// ──────────────────────────────────────────────────────────────────────
// Core schema helpers
// ──────────────────────────────────────────────────────────────────────

function applySchemaDerive(schema, records) {
  if (!schema.derive) return records;
  return records.map(r => ({ ...r, ...schema.derive(r) }));
}

function applySchemaSort(schema, records) {
  const { field, dir, abs } = schema.sort || {};
  if (!field) return records;
  return [...records].sort((a, b) => {
    let av = parseFloat(String(a[field] || '0').replace(/,/g, '')) || 0;
    let bv = parseFloat(String(b[field] || '0').replace(/,/g, '')) || 0;
    if (abs) { av = Math.abs(av); bv = Math.abs(bv); }
    return dir === 'asc' ? av - bv : bv - av;
  });
}

function resolveCompanionRecords(companionKey) {
  if (!companionKey || !inventory) return [];
  const companion = inventory.find(i =>
    i.active_source_keys && i.active_source_keys.split('|').some(k => k.trim() === companionKey)
  );
  return companion ? (companion.records_sample || []) : [];
}

// ──────────────────────────────────────────────────────────────────────
// updateExplorerContent — entry point after every filter/search change
// ──────────────────────────────────────────────────────────────────────

function updateExplorerContent() {
  if (!currentExplorerItem) return;

  const item = currentExplorerItem;
  const schema = window.getSchemaForItem ? window.getSchemaForItem(item) : null;
  const tableWrap = document.getElementById("explorer-table-wrap");

  // ── STATUS_ONLY: named feed is empty/blocked ──────────────────────
  if (schema && schema.mode === 'STATUS_ONLY') {
    const hasNativeRows = (item.records_sample || []).length > 0;
    const companionRecords = schema.companionKey ? resolveCompanionRecords(schema.companionKey) : [];

    let html = `
      <div style="margin:1rem;padding:1rem 1.2rem;background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.3);border-radius:8px;">
        <div style="font-size:0.85rem;font-weight:700;color:#fbbf24;margin-bottom:0.4rem;">⚠ Named Feed Status</div>
        <div style="font-size:0.78rem;color:#94a3b8;">${escapeHTML(schema.statusNote || 'Feed is empty or blocked.')}</div>
      </div>`;

    if (hasNativeRows && schema.displayColumns) {
      // Some STATUS_ONLY feeds still have rows (e.g. buyback with 3 rows)
      html += renderSchemaTable(schema, item.records_sample, item);
    } else if (schema.companionKey && companionRecords.length > 0) {
      html += `
        <div style="margin:0 1rem 0.5rem;padding:0.6rem 1rem;background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.3);border-radius:6px;font-size:0.75rem;color:#a5b4fc;">
          📎 ${escapeHTML(schema.companionNote || 'Companion data')} — ${companionRecords.length} rows
        </div>`;
      const companionSchema = schema.companionKey ? (window.LINK_SCHEMAS && window.LINK_SCHEMAS[schema.companionKey]) : null;
      html += renderSchemaTable(companionSchema || schema, companionRecords, item);
    } else {
      html += `<div style="padding:2rem;text-align:center;color:var(--text-dim);font-size:0.85rem;">No companion data available at this time.</div>`;
    }

    document.getElementById("explorer-match-count").textContent = hasNativeRows
      ? `Showing ${item.records_sample.length} native rows`
      : `Named feed empty · ${companionRecords.length} companion rows`;
    tableWrap.innerHTML = html;
    return;
  }

  // ── Get raw records — with sample_row fallback ────────────────────
  let records = item.records_sample || [];
  let isSampleFallback = false;

  // When records_sample is empty but sample_row is a valid object,
  // use it as a 1-row preview so the explorer never shows a blank table
  // for STRONG/PROVENANCE links that simply store sample separately.
  if (records.length === 0) {
    const sr = item.sample_row;
    if (sr && typeof sr === 'object' && !Array.isArray(sr) && Object.keys(sr).length > 0) {
      records = [sr];
      isSampleFallback = true;
    }
  }

  // Preprocess nested structures (PreOpen, OI Spurts, Market Turnover)
  if (schema && schema.preprocess) {
    records = schema.preprocess(records);
  }

  // Apply derived fields
  if (schema) records = applySchemaDerive(schema, records);

  // Search/stock filter
  if (currentExplorerFilter) {
    const q = currentExplorerFilter.toLowerCase();
    records = records.filter(r =>
      typeof r === "object"
        ? JSON.stringify(r).toLowerCase().includes(q)
        : String(r).toLowerCase().includes(q)
    );
  }

  const totalStr = item.usable_rows > 0
    ? item.usable_rows.toLocaleString("en-IN")
    : (isSampleFallback ? '1 (sample)' : '0');

  document.getElementById("explorer-match-count").textContent =
    isSampleFallback
      ? `Showing 1 sample row · full dataset has ${item.usable_rows.toLocaleString("en-IN")} rows`
      : `Showing ${records.length} of ${item.usable_rows.toLocaleString("en-IN")} rows`;

  if (records.length === 0) {
    tableWrap.innerHTML = `
      <div style="padding:3rem 1rem;text-align:center;color:var(--text-muted);">
        <p style="font-size:1.5rem;margin-bottom:0.5rem;">🔍</p>
        <p style="color:#fff;font-weight:600;">No matching records in this dataset</p>
        <p style="font-size:0.8rem;">Try clearing the search filter or choosing another stock symbol.</p>
      </div>`;
    return;
  }

  // Prepend a "Sample preview" notice when using fallback
  const sampleBanner = isSampleFallback
    ? `<div style="margin:0.75rem 1rem 0.25rem;padding:0.5rem 1rem;background:rgba(99,102,241,0.08);
                   border:1px solid rgba(99,102,241,0.25);border-radius:6px;
                   font-size:0.72rem;color:#a5b4fc;display:flex;align-items:center;gap:0.5rem;">
         <span>ℹ</span>
         <span><strong>Sample preview</strong> — full dataset has <strong>${item.usable_rows.toLocaleString("en-IN")}</strong> rows.
         Sample data was stored separately from the bulk records snapshot.</span>
       </div>`
    : '';

  tableWrap.innerHTML = sampleBanner + renderSchemaTable(schema, records, item);
}

// ──────────────────────────────────────────────────────────────────────
// renderSchemaTable — the full schema-aware table renderer
// ──────────────────────────────────────────────────────────────────────

function renderSchemaTable(schema, records, item) {
  if (!schema || !records || records.length === 0) {
    return renderExplorerTableHTML(records); // fallback to generic
  }

  const mode = schema.mode || 'RANKED';

  // POSITIVE_AND_NEGATIVE: split into two panels
  if (mode === 'POSITIVE_AND_NEGATIVE') {
    return renderPosNegPanels(schema, records, item);
  }

  // DIRECTORY: all rows, schema sort but no Top 5 strip header
  if (mode === 'DIRECTORY') {
    const sorted = applySchemaSort(schema, records);
    return buildSchemaTableHTML(schema, sorted, item, null);
  }

  // NEXT_5: sort asc by date field, show next 5 + full table
  if (mode === 'NEXT_5') {
    const sorted = applySchemaSort(schema, records);
    const top5 = sorted.slice(0, schema.topN || 5);
    return buildTop5Strip(schema, top5) + buildSchemaTableHTML(schema, sorted, item, schema.topLabel);
  }

  // LATEST_5 / RANKED (default)
  const sorted = applySchemaSort(schema, records);
  const topN = schema.topN || 5;
  const top5 = sorted.slice(0, topN);
  return buildTop5Strip(schema, top5) + buildSchemaTableHTML(schema, sorted, item, schema.topLabel);
}

// ──────────────────────────────────────────────────────────────────────
// Top 5 highlight strip above the full table
// ──────────────────────────────────────────────────────────────────────

function buildTop5Strip(schema, topRows) {
  if (!topRows || topRows.length === 0) return "";
  const identField = schema.identityField;
  const sortField = schema.sort && schema.sort.field;

  const pills = topRows.map((r, i) => {
    const label = identField ? escapeHTML(String(r[identField] || '—').slice(0, 25)) : `Row ${i+1}`;
    const val = sortField ? formatNum(r[sortField]) : '';
    const rankColor = ['#ffd700','#c0c0c0','#cd7f32','#60a5fa','#34d399'][i] || '#60a5fa';
    return `
      <div style="display:flex;align-items:center;gap:0.5rem;padding:0.4rem 0.75rem;
                  background:rgba(255,255,255,0.04);border-radius:6px;min-width:140px;flex:1;border:1px solid rgba(255,255,255,0.06);">
        <span style="font-size:0.9rem;font-weight:800;color:${rankColor};min-width:1.2rem;">#${i+1}</span>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:700;font-size:0.8rem;color:#e2e8f0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${label}</div>
          ${val ? `<div style="font-size:0.72rem;color:#94a3b8;font-family:var(--font-mono);">${val}</div>` : ''}
        </div>
      </div>`;
  }).join('');

  return `
    <div style="padding:0.75rem 1rem 0.5rem;">
      <div style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--text-dim);margin-bottom:0.5rem;">
        🏆 ${escapeHTML(schema.topLabel || 'Top Results')}
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:0.5rem;">${pills}</div>
    </div>
    <div style="height:1px;background:var(--border-color);margin:0 1rem 0.5rem;"></div>`;
}

// ──────────────────────────────────────────────────────────────────────
// POSITIVE_AND_NEGATIVE: two side-by-side panels
// ──────────────────────────────────────────────────────────────────────

function renderPosNegPanels(schema, records, item) {
  const sorted = applySchemaSort(schema, records);
  const posRows = schema.posFilter ? sorted.filter(schema.posFilter) : [];
  const negRows = schema.negFilter ? sorted.filter(schema.negFilter) : [];
  const topN = schema.topN || 5;

  const posTop = posRows.slice(0, topN);
  const negTop = negRows.slice(0, topN);

  const posColor = '#34d399';
  const negColor = '#f87171';

  const buildPanel = (rows, label, color, colDef) => {
    if (rows.length === 0) {
      return `<div style="padding:1.5rem;text-align:center;color:var(--text-dim);font-size:0.8rem;">No ${label} data</div>`;
    }
    const cols = colDef || schema.displayColumns;
    const ths = cols.map(c =>
      `<th style="${c.numeric ? 'text-align:right;' : ''}min-width:80px;">${escapeHTML(c.label)}</th>`
    ).join('');

    const trs = rows.map((r, idx) => {
      const tds = cols.map(c => {
        const v = r[c.key];
        if (v == null || v === '' || v === '-') return `<td style="color:var(--text-dim);font-size:0.7rem;">—</td>`;
        const fmt = c.numeric ? formatNum(v) : escapeHTML(String(v).slice(0, 80));
        const style = c.numeric ? `text-align:right;color:${color};font-family:var(--font-mono);font-weight:700;` : '';
        return `<td style="${style}">${fmt}</td>`;
      }).join('');
      const bg = idx % 2 === 1 ? 'style="background:rgba(255,255,255,0.015)"' : '';
      return `<tr ${bg}><td style="color:var(--text-dim);font-size:0.7rem;text-align:center;">${idx+1}</td>${tds}</tr>`;
    }).join('');

    return `
      <div style="margin-bottom:0.5rem;padding:0.3rem 0.5rem;font-size:0.72rem;font-weight:700;color:${color};text-transform:uppercase;letter-spacing:0.04em;">
        ${label} (${rows.length})
      </div>
      <div style="overflow-x:auto;">
        <table class="explorer-table">
          <thead><tr><th style="min-width:32px;">#</th>${ths}</tr></thead>
          <tbody>${trs}</tbody>
        </table>
      </div>`;
  };

  const posHtml = buildPanel(posTop, schema.posLabel || 'Positive', posColor);
  const negHtml = buildPanel(negTop, schema.negLabel || 'Negative', negColor);

  const note = schema.note ? `<div style="padding:0.4rem 1rem;font-size:0.72rem;color:var(--text-dim);">ℹ ${escapeHTML(schema.note)}</div>` : '';

  return `
    ${note}
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;padding:0.75rem 1rem;">
      <div style="background:rgba(52,211,153,0.04);border:1px solid rgba(52,211,153,0.15);border-radius:8px;padding:0.75rem;overflow:hidden;">${posHtml}</div>
      <div style="background:rgba(248,113,113,0.04);border:1px solid rgba(248,113,113,0.15);border-radius:8px;padding:0.75rem;overflow:hidden;">${negHtml}</div>
    </div>
    <div style="padding:0 1rem 0.5rem;">
      <div style="font-size:0.72rem;color:var(--text-dim);margin-bottom:0.5rem;">Full Dataset</div>
      ${buildSchemaTableHTML(schema, applySchemaSort(schema, records), item, null)}
    </div>`;
}

// ──────────────────────────────────────────────────────────────────────
// Build the actual schema-column table HTML
// ──────────────────────────────────────────────────────────────────────

function buildSchemaTableHTML(schema, records, item, topLabelOverride) {
  const cols = schema && schema.displayColumns
    ? schema.displayColumns
    : null;

  if (!cols) return renderExplorerTableHTML(records); // fallback generic

  const limited = records.slice(0, 250);

  const ths = cols.map(c => {
    let style = 'min-width:90px;';
    if (c.wide)    style = 'min-width:240px;max-width:380px;';
    if (c.numeric) style += 'text-align:right;';
    return `<th style="${style}">${escapeHTML(c.label)}</th>`;
  }).join('');

  const trs = limited.map((r, idx) => {
    const bg = idx % 2 === 1 ? 'style="background:rgba(255,255,255,0.015)"' : '';
    const tds = cols.map(c => {
      const raw = r[c.key];
      if (raw == null || raw === '' || raw === '-') {
        return `<td style="color:var(--text-dim);font-size:0.7rem;">—</td>`;
      }
      const strVal = String(raw);

      // Link columns
      if (c.isLink && strVal.startsWith('http')) {
        const fname = strVal.split('/').pop().slice(0, 28);
        return `<td><a href="${strVal}" target="_blank" style="color:#38bdf8;font-size:0.75rem;">📄 ${escapeHTML(fname)}</a></td>`;
      }

      // Wide text wrapping
      if (c.wide) {
        const short = strVal.length > 200 ? strVal.slice(0, 200) + '…' : strVal;
        return `<td style="white-space:normal;word-break:break-word;max-width:380px;font-size:0.75rem;color:#cbd5e1;line-height:1.4;">${escapeHTML(short)}</td>`;
      }

      // Numeric with colour
      if (c.numeric) {
        const num = parseFloat(strVal.replace(/,/g, ''));
        const col = !isNaN(num) && num < 0 ? '#f87171' : '#34d399';
        return `<td style="text-align:right;font-weight:700;color:${col};font-family:var(--font-mono);">${formatNum(raw)}</td>`;
      }

      // Default text
      return `<td>${escapeHTML(strVal.slice(0, 80))}</td>`;
    }).join('');
    return `<tr ${bg}><td style="color:var(--text-dim);font-size:0.7rem;text-align:center;font-family:var(--font-mono);">${idx+1}</td>${tds}</tr>`;
  }).join('');

  const overflow = records.length >= 250
    ? `<div style="padding:0.5rem 1rem;font-size:0.72rem;color:var(--text-dim);border-top:1px solid var(--border-color);">
        ⚠ Showing first 250 of ${(item ? item.usable_rows : records.length).toLocaleString('en-IN')} records.
       </div>` : '';

  return `
    <div style="overflow-x:auto;">
      <table class="explorer-table">
        <thead><tr><th style="min-width:32px;text-align:center;">#</th>${ths}</tr></thead>
        <tbody>${trs}</tbody>
      </table>
    </div>${overflow}`;
}

// ──────────────────────────────────────────────────────────────────────
// formatNum — compact number formatting for explorer cells
// ──────────────────────────────────────────────────────────────────────

function formatNum(val) {
  const n = parseFloat(String(val || '').replace(/,/g, ''));
  if (isNaN(n)) return escapeHTML(String(val || '—'));
  if (Math.abs(n) >= 1e7)  return (n / 1e7).toFixed(2) + ' Cr';
  if (Math.abs(n) >= 1e5)  return (n / 1e5).toFixed(2) + ' L';
  if (Math.abs(n) >= 1e3)  return n.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  return n.toFixed(2);
}

// ──────────────────────────────────────────────────────────────────────
// Generic fallback table (used when no schema found)
// ──────────────────────────────────────────────────────────────────────

function renderExplorerTableHTML(records) {
  if (!records || records.length === 0) return "";

  const sampleObj = records[0];
  if (typeof sampleObj !== "object" || Array.isArray(sampleObj)) {
    const lines = records.map((r, i) =>
      `<div style="padding:0.3rem 0.8rem;border-bottom:1px solid rgba(255,255,255,0.04);font-family:var(--font-mono);font-size:0.78rem;">
        <span style="color:var(--text-dim);margin-right:0.5rem;">${i+1}</span>${escapeHTML(String(r))}
      </div>`
    ).join("");
    return `<div>${lines}</div>`;
  }

  const allKeys = Object.keys(sampleObj).filter(k => !HIDE_FIELDS.has(k));
  const primaryOrder = [
    "Symbol","Company","Commodity","Contract","Security","symbol","company",
    "Close ₹","Open ₹","High ₹","Low ₹","Last ₹","Prev Close ₹","Volume","Open Interest",
    "Date","Trade Date","Deal Date","Report Date","Ex-Date","Headline","Description"
  ];
  const sortedKeys = [
    ...primaryOrder.filter(k => allKeys.includes(k)),
    ...allKeys.filter(k => !primaryOrder.includes(k))
  ].slice(0, 12);

  const ths = sortedKeys.map(k => `<th>${getFieldLabel(k)}</th>`).join("");
  const trs = records.slice(0, 250).map((rowObj, idx) => {
    const bg = idx % 2 === 1 ? 'style="background:rgba(255,255,255,0.015)"' : '';
    const tds = sortedKeys.map(k => {
      const val = rowObj[k];
      if (val == null || val === '' || val === '-')
        return `<td style="color:var(--text-dim);font-size:0.7rem;">—</td>`;
      return `<td>${escapeHTML(String(val).slice(0, 80))}</td>`;
    }).join("");
    return `<tr ${bg}><td style="color:var(--text-dim);font-size:0.7rem;text-align:center;">${idx+1}</td>${tds}</tr>`;
  }).join("");

  return `
    <div style="overflow-x:auto;">
      <table class="explorer-table">
        <thead><tr><th style="min-width:32px;">#</th>${ths}</tr></thead>
        <tbody>${trs}</tbody>
      </table>
    </div>`;
}

function exportExplorerCSV() {
  if (!currentExplorerItem) return;
  const item = currentExplorerItem;
  const records = item.records_sample || [];

  if (records.length === 0) {
    showToast("No dataset records available to export");
    return;
  }

  const sampleObj = records[0];
  const keys = typeof sampleObj === "object" ? Object.keys(sampleObj) : ["Value"];

  const csvRows = [keys.join(",")];

  records.forEach(r => {
    if (typeof r === "object") {
      const vals = keys.map(k => `"${esc(r[k])}"`);
      csvRows.push(vals.join(","));
    } else {
      csvRows.push(`"${esc(r)}"`);
    }
  });

  const encodedUri = "data:text/csv;charset=utf-8," + encodeURI(csvRows.join("\n"));
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `${item.active_source_keys}_dataset_${new Date().toISOString().slice(0,10)}.csv`);
  document.body.appendChild(link); link.click(); document.body.removeChild(link);
  showToast(`Exported ${records.length} records to CSV`);
}


// ======================================================================
// DRAWER & MODALS
// ======================================================================

function openDrawer(rowNo) {
  const item = inventory.find(i => i.row_no === rowNo);
  if (!item) return;

  document.getElementById("drawer-row-num").textContent = `#${item.row_no}`;
  document.getElementById("drawer-title").textContent = item.title;
  const statusEl = document.getElementById("drawer-status");
  statusEl.className = `status-chip status-${item.status}`;
  statusEl.textContent = item.status;

  const rawJson = item.sample_row
    ? (typeof item.sample_row === "object" ? JSON.stringify(item.sample_row, null, 2) : item.sample_row)
    : "No sample payload row available.";
  document.getElementById("drawer-json").textContent = rawJson;

  // Full payload table in drawer
  const drawerPayload = document.getElementById("drawer-payload");
  if (drawerPayload) drawerPayload.innerHTML = renderPayloadTable(item);

  document.getElementById("drawer-body-content").innerHTML = `
    <div class="drawer-section">
      <div class="drawer-section-title">Core Usability Stats</div>
      <div class="meta-grid">
        <div class="meta-block"><label>Usable Rows</label><val>${item.usable_rows.toLocaleString("en-IN")}</val></div>
        <div class="meta-block"><label>Data Date</label><val>${item.data_date || "—"}</val></div>
        <div class="meta-block"><label>Source Role</label><val>${item.source_role}</val></div>
        <div class="meta-block"><label>Mode</label><val>${item.mode}</val></div>
        <div class="meta-block"><label>Connection</label><val>${item.connection_status}</val></div>
        <div class="meta-block"><label>Parser Status</label><val>${item.parser_status}</val></div>
        <div class="meta-block"><label>Freshness Cadence</label><val>${item.freshness_status}</val></div>
        <div class="meta-block"><label>Inventory ID</label><val>${item.inventory_id}</val></div>
        <div class="meta-block"><label>Record Scope</label><val>${item.records_scope || "display_sample_max_250"}</val></div>
        <div class="meta-block"><label>Source Rows</label><val>${Number(item.source_row_count || 0).toLocaleString("en-IN")}</val></div>
        <div class="meta-block"><label>Normalized Rows</label><val>${Number(item.normalized_row_count || 0).toLocaleString("en-IN")}</val></div>
        <div class="meta-block"><label>Source Trust</label><val>${escapeHTML(item.source_trust || item.source_role || "")}</val></div>
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">Governance & Integration</div>
      <div class="meta-block" style="margin-bottom:0.5rem;"><label>Screener Tag</label><val>${item.screener_integration}</val></div>
      <div class="meta-block" style="margin-bottom:0.5rem;"><label>Purpose & Jobs</label><val>${escapeHTML(item.purpose_jobs)}</val></div>
      <div class="meta-block" style="margin-bottom:0.5rem;"><label>Safe Use Policy</label><val>${escapeHTML(item.safe_use)}</val></div>
      <div class="meta-block"><label>Next Recommended Action</label><val>${escapeHTML(item.next_action)}</val></div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">Endpoints & Audit Trail</div>
      <div class="meta-block" style="margin-bottom:0.5rem;">
        <label>Canonical URL</label>
        <val><a href="${item.canonical_url}" target="_blank" style="color:var(--accent-blue);">${escapeHTML(item.canonical_url)}</a></val>
      </div>
      ${item.provenance_url ? `<div class="meta-block" style="margin-bottom:0.5rem;">
        <label>Linked API ↔ Provenance Pair</label>
        <val><a href="${item.provenance_url}" target="_blank" style="color:var(--status-prov);">${escapeHTML(item.provenance_url)}</a></val>
      </div>` : ""}
      <div class="meta-block" style="margin-bottom:0.5rem;">
        <label>Local Archive Path</label>
        <val style="font-family:var(--font-mono);font-size:0.725rem;">${escapeHTML(item.raw_path || "N/A")}</val>
      </div>
      <div class="meta-block">
        <label>Audit Summary</label>
        <val style="font-size:0.75rem;color:var(--text-muted);">${escapeHTML(item.summary)}</val>
      </div>
    </div>`;

  document.getElementById("drawer-backdrop").classList.add("active");
  document.getElementById("drawer").classList.add("active");
}

function closeDrawer() {
  document.getElementById("drawer-backdrop").classList.remove("active");
  document.getElementById("drawer").classList.remove("active");
}

function openCodeModal(rowNo) {
  const item = inventory.find(i => i.row_no === rowNo);
  if (!item) return;
  document.getElementById("code-modal-title").textContent = `Fetch Code: ${item.title}`;
  document.getElementById("python-code-block").textContent = item.python_snippet;
  document.getElementById("curl-code-block").textContent = item.curl_snippet;
  document.getElementById("code-modal-backdrop").classList.add("active");
  document.getElementById("code-modal").classList.add("active");
}

function closeCodeModal() {
  document.getElementById("code-modal-backdrop").classList.remove("active");
  document.getElementById("code-modal").classList.remove("active");
}

function openLegendModal() {
  document.getElementById("legend-modal-backdrop").classList.add("active");
  document.getElementById("legend-modal").classList.add("active");
}

function closeLegendModal() {
  document.getElementById("legend-modal-backdrop").classList.remove("active");
  document.getElementById("legend-modal").classList.remove("active");
}

// ======================================================================
// UTILITIES
// ======================================================================

function exportCSV() {
  let filtered = inventory.filter(item => {
    if (activeTopic !== "All Topics" && item.topic !== activeTopic) return false;
    if (activeStatus !== "ALL" && item.status !== activeStatus) return false;
    if (activeTag && (!(item.sample_fields||[]).includes(activeTag))) return false;
    if (searchQuery) {
      const q = searchQuery;
      const jsonStr = item.sample_row ? JSON.stringify(item.sample_row).toLowerCase() : "";
      if (!item.title.toLowerCase().includes(q) && !item.active_source_keys.toLowerCase().includes(q) && !jsonStr.includes(q)) return false;
    }
    return true;
  });

  if (!filtered.length) { showToast("No visible data to export"); return; }

  const headers = ["Row","Title","Source Key","Topic","Status","Usable Rows","Date","Canonical URL","Integration","Purpose"];
  const csvRows = [headers.join(",")];
  filtered.forEach(item => {
    csvRows.push([
      item.row_no, `"${esc(item.title)}"`, `"${esc(item.active_source_keys)}"`,
      `"${esc(item.topic)}"`, `"${item.status}"`, item.usable_rows,
      `"${esc(item.data_date||"")}"`, `"${esc(item.canonical_url)}"`,
      `"${esc(item.screener_integration)}"`, `"${esc(item.purpose_jobs)}"`
    ].join(","));
  });

  const encodedUri = "data:text/csv;charset=utf-8," + encodeURI(csvRows.join("\n"));
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `trendforge_${new Date().toISOString().slice(0,10)}.csv`);
  document.body.appendChild(link); link.click(); document.body.removeChild(link);
  showToast(`Exported ${filtered.length} rows to CSV`);
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text)
    .then(() => showToast("Copied!"))
    .catch(err => console.error("Copy failed:", err));
}

function copyDrawerJSON() {
  copyToClipboard(document.getElementById("drawer-json").textContent);
}

function copyPythonSnippet() {
  copyToClipboard(document.getElementById("python-code-block").textContent);
}

function showToast(msg) {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 2500);
}

function escapeHTML(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;").replace(/'/g,"&#039;");
}

function escapeJS(str) {
  if (!str) return "";
  return String(str).replace(/'/g,"\\'").replace(/"/g,'\\"');
}

function esc(str) {
  if (!str) return "";
  return String(str).replace(/"/g,'""');
}

// ----------------------------------------------------------------------
// Source Operations: compiler/fetch/parser evidence, never catalog samples.
// ----------------------------------------------------------------------
const SOURCE_OPS_STATES = ["HEALTHY", "VALID_EMPTY", "STALE_PARTIAL", "BLOCKED", "FAILED", "NOT_ATTEMPTED"];
const SOURCE_OPS_META = {
  HEALTHY: { label: "HEALTHY", dot: "is-healthy" },
  VALID_EMPTY: { label: "VALID EMPTY", dot: "is-empty" },
  STALE_PARTIAL: { label: "STALE / PARTIAL", dot: "is-stale" },
  BLOCKED: { label: "BLOCKED", dot: "is-blocked" },
  FAILED: { label: "FAILED", dot: "is-failed" },
  NOT_ATTEMPTED: { label: "NOT ATTEMPTED", dot: "is-idle" }
};
let sourceOpsRows = [];
let sourceOpsFilter = "ATTENTION";

function initSourceOperationsPanel() {
  const panel = document.getElementById("source-ops-panel");
  if (!panel) return;

  document.getElementById("source-ops-reload")?.addEventListener("click", loadSourceOperations);
  document.getElementById("source-ops-toggle")?.addEventListener("click", () => {
    const detail = document.getElementById("source-ops-detail");
    const shouldOpen = detail?.hidden !== false;
    setSourceOpsDetailOpen(shouldOpen);
    if (shouldOpen) renderSourceOperationsTable(sourceOpsFilter);
  });
  document.querySelectorAll("[data-source-state]").forEach(button => {
    button.addEventListener("click", () => {
      sourceOpsFilter = button.dataset.sourceState || "ATTENTION";
      document.querySelectorAll("[data-source-state]").forEach(item => {
        item.classList.toggle("is-active", item === button);
        item.setAttribute("aria-pressed", item === button ? "true" : "false");
      });
      setSourceOpsDetailOpen(true);
      renderSourceOperationsTable(sourceOpsFilter);
    });
  });

  loadSourceOperations();
}

function sourceOpsApiUrl(path) {
  if (location.protocol.startsWith("http") && location.port === "8000") return path;
  return `http://127.0.0.1:8000${path}`;
}

async function sourceOpsFetch(path) {
  const response = await fetch(sourceOpsApiUrl(path), { cache: "no-store" });
  if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}`);
  return response.json();
}

async function loadSourceOperations() {
  const reload = document.getElementById("source-ops-reload");
  const state = document.getElementById("source-ops-panel-state");
  if (reload) {
    reload.disabled = true;
    reload.setAttribute("aria-busy", "true");
    reload.textContent = "Loading...";
  }
  if (state) {
    state.textContent = "LOADING";
    state.className = "source-ops-state is-loading";
  }

  try {
    const snapshot = await sourceOpsFetch("/api/source-operations/snapshot");
    renderSourceOperationsSnapshot(snapshot);
  } catch (error) {
    renderSourceOperationsUnavailable(error);
  } finally {
    if (reload) {
      reload.disabled = false;
      reload.setAttribute("aria-busy", "false");
      reload.textContent = "Reload status";
    }
  }
}

function sourceOpsLatestBy(rows, keyField, timeField) {
  const latest = new Map();
  (rows || []).forEach(row => {
    const key = String(row?.[keyField] || "").trim();
    if (!key) return;
    const previous = latest.get(key);
    const currentTime = Date.parse(row?.[timeField] || "") || Number(row?.id) || 0;
    const previousTime = previous ? (Date.parse(previous?.[timeField] || "") || Number(previous?.id) || 0) : -1;
    if (!previous || currentTime > previousTime) latest.set(key, row);
  });
  return latest;
}

function sourceOpsProofExpired(timestamp, staleAfterHours, frequency) {
  const observed = Date.parse(timestamp || "");
  if (!Number.isFinite(observed)) return true;
  const defaults = {
    intraday: 8,
    daily: 72,
    weekly: 240,
    fortnightly: 480,
    monthly: 1080,
    quarterly: 2640,
    annual: 9600,
    event_based: 720
  };
  const declared = Number(staleAfterHours);
  const fallback = defaults[String(frequency || "").toLowerCase()] || 72;
  const allowedHours = Number.isFinite(declared) && declared > 0 ? declared : fallback;
  return (Date.now() - observed) > allowedHours * 60 * 60 * 1000;
}

function sourceOpsClassify(source, freshness, output, attempt) {
  const reason = String(freshness?.reason || output?.parser_status || attempt?.result_state || "No observed fetch or parser proof");
  const proofAt = freshness?.checked_at || output?.created_at || attempt?.attempted_at || null;
  const expired = proofAt
    ? sourceOpsProofExpired(proofAt, source?.staleAfterHours, freshness?.expected_frequency || source?.expectedFrequency)
    : true;
  const upper = reason.toUpperCase();

  if (!freshness && !output && !attempt) {
    return { state: "NOT_ATTEMPTED", reason, proofAt, dataDate: null };
  }
  if (expired) {
    return {
      state: "STALE_PARTIAL",
      reason: `Monitor observation expired. Last result: ${reason}`,
      proofAt,
      dataDate: freshness?.latest_data_date || output?.data_date || null
    };
  }
  if (/BLOCK|ACCESS_DENIED|CAPTCHA|WAF|RATE_LIMIT|HTTP 403|HTTP 429/.test(upper) ||
      [401, 403, 429].includes(Number(attempt?.status_code))) {
    return { state: "BLOCKED", reason, proofAt, dataDate: freshness?.latest_data_date || output?.data_date || null };
  }
  if (/PARSED_EMPTY|VALID_EMPTY|SOFT_EMPTY/.test(upper)) {
    return { state: "VALID_EMPTY", reason, proofAt, dataDate: freshness?.latest_data_date || output?.data_date || null };
  }
  if (/SCHEMA_MISMATCH|METADATA_ONLY|PARSE_FAIL|FETCH_FAIL|MALFORMED|INVALID|ERROR/.test(upper)) {
    return { state: "FAILED", reason, proofAt, dataDate: freshness?.latest_data_date || output?.data_date || null };
  }
  if (/WAIT_FETCH_REQUIRED|NOT_ATTEMPTED|NO_FETCH/.test(upper)) {
    return { state: "NOT_ATTEMPTED", reason, proofAt, dataDate: freshness?.latest_data_date || output?.data_date || null };
  }
  if (Number(freshness?.is_fresh) === 1 && /FRESH STRUCTURED DATA/.test(upper)) {
    return { state: "HEALTHY", reason, proofAt, dataDate: freshness?.latest_data_date || output?.data_date || null };
  }
  return {
    state: "STALE_PARTIAL",
    reason: output && Number(output.record_count) > 0
      ? `Parsed records exist, but current freshness proof is incomplete. ${reason}`
      : reason,
    proofAt,
    dataDate: freshness?.latest_data_date || output?.data_date || null
  };
}

function sourceOpsResearchEffect(key, state) {
  if (state === "HEALTHY" || state === "VALID_EMPTY") return "No failure impact.";
  const effects = {
    nse_bhavcopy_eod: "Cash price fact unavailable; dependent cash rows remain WAIT.",
    nse_fo_bhavcopy: "Futures OI enrichment unavailable; cash names are not penalized.",
    nse_fno_ban: "F&O restriction gate unknown; dependent F&O profiles remain WAIT.",
    nse_mwpl_ban: "F&O restriction gate unknown; dependent F&O profiles remain WAIT.",
    nse_mwpl_percentages: "MWPL_MISSING; MWPL-required profiles remain WAIT.",
    nse_index_close_eod: "Index context unavailable; no stock state is inferred.",
    nse_corporate_filings_actions: "Corporate-action integrity unresolved; affected symbols remain WAIT."
  };
  return effects[key] || "Research fact unavailable; no stock impact is inferred.";
}

function renderSourceOperationsSnapshot(snapshot) {
  const track = snapshot.sourceTrack || {};
  const permissions = snapshot.permissions || {};
  sourceOpsRows = Array.isArray(track.rows) ? track.rows : [];
  const stateCounts = track.stateCounts || Object.fromEntries(SOURCE_OPS_STATES.map(name => [name, 0]));

  setSourceOpsValue("ops-contracts", track.compilerContracts ?? "--");
  setSourceOpsValue("ops-monitored", track.runtimeCatalogKeys ?? "--");
  setSourceOpsValue("ops-attempted", track.attemptedKeys ?? "--");
  setSourceOpsValue("ops-parsed", track.parsedKeys ?? "--");
  setSourceOpsValue("ops-current", track.currentFacts ?? "--");
  setSourceOpsValue("ops-usable", track.researchUsableFacts ?? "--");
  setSourceOpsValue("ops-lastgood", track.lastGoodKeys ?? "--");
  SOURCE_OPS_STATES.forEach(name => setSourceOpsValue(`ops-count-${name}`, stateCounts[name] || 0));

  const asOf = document.getElementById("source-ops-asof");
  if (asOf) asOf.textContent = snapshot.asOf
    ? `As of ${sourceOpsFormatDate(new Date(snapshot.asOf))}`
    : "As of unknown";

  const contract = document.getElementById("source-ops-contract");
  if (contract) {
    contract.textContent = snapshot.note
      || `${track.compilerContracts || 0} compiler contracts; ${track.runtimeCatalogKeys || 0} runtime keys.`;
  }
  const lastGood = document.getElementById("source-ops-lastgood");
  if (lastGood) lastGood.textContent =
    `Last-good keys: ${track.lastGoodKeys ?? 0}` +
    (track.lastGoodViaAlias ? ` (${track.lastGoodViaAlias} via alias)` : "") +
    `. Refresh jobs: ${track.collectorContracts ?? 123}. ` +
    `165 cards are not 165 downloads — aliases share a parent job.`;

  const permission = document.getElementById("source-ops-permission");
  if (permission) {
    permission.textContent =
      `sourceActivationReady=${permissions.sourceActivationReady === true} | ` +
      `gateAuthorized=${Number(permissions.gateAuthorized) || 0} | ` +
      `ceiling=${permissions.researchCeiling || "WATCH_WAIT_REJECT"} | ` +
      `CONFIRMED locked`;
  }

  const needsAttention = (stateCounts.STALE_PARTIAL || 0) + (stateCounts.BLOCKED || 0) +
    (stateCounts.FAILED || 0) + (stateCounts.NOT_ATTEMPTED || 0);
  const panelState = document.getElementById("source-ops-panel-state");
  if (panelState) {
    panelState.textContent = needsAttention > 0 ? `ATTENTION ${needsAttention}` : "OBSERVED";
    panelState.className = `source-ops-state ${needsAttention > 0 ? "is-attention" : "is-ready"}`;
  }

  renderCashTrack(snapshot.cashTrack);
  renderSourceOperationsTable(sourceOpsFilter);
}

const CASH_TRACK_STAGES = ["A1", "A2", "A3", "A4", "A5", "A6", "C0", "B", "C1"];

function renderCashTrack(cashTrack) {
  const stateEl = document.getElementById("source-ops-cash-state");
  const detailEl = document.getElementById("source-ops-cash-detail")
    || document.getElementById("source-ops-cash-summary");
  const run = cashTrack?.latestRun || cashTrack?.latest_run || null;
  const dispatch = cashTrack?.latestDispatch || cashTrack?.latest_dispatch || null;
  const stages = run?.stages || [];
  const byId = new Map(stages.map(stage => [stage.stageId || stage.stage_id, stage]));

  CASH_TRACK_STAGES.forEach(id => {
    const node = document.getElementById(`cash-stage-${id}`);
    const wrap = document.querySelector(`[data-cash-stage="${id}"]`);
    const stage = byId.get(id);
    const label = stage ? String(stage.state || "--") : "--";
    if (node) node.textContent = label;
    else if (wrap) {
      const small = wrap.querySelector("small");
      if (small) small.textContent = label;
    }
    if (wrap) {
      wrap.classList.remove("is-pass", "is-wait", "is-fail", "is-skip");
      const value = String(stage?.state || "").toUpperCase();
      if (value === "COMPLETED" || value === "REUSED") wrap.classList.add("is-pass");
      else if (value === "BLOCKED") wrap.classList.add("is-wait");
      else if (value === "FAILED") wrap.classList.add("is-fail");
      else if (value === "SKIPPED") wrap.classList.add("is-skip");
    }
  });

  if (!cashTrack) {
    if (stateEl) stateEl.textContent = "No post-commit run yet";
    if (detailEl) {
      detailEl.textContent = "A1–C1 starts only after a cash-relevant last-good save. HTTP 200 does not start it.";
    }
    return;
  }
  if (stateEl) {
    stateEl.textContent = run
      ? `${run.state || "UNKNOWN"} ${run.runId || run.run_id || ""}`.trim()
      : (dispatch?.decision || "NO_RUN");
  }
  if (detailEl) {
    const bits = [];
    if (dispatch?.detail) bits.push(dispatch.detail);
    if (run?.error) bits.push(run.error);
    if (run?.researchCeiling || run?.research_ceiling) {
      bits.push(`ceiling=${run.researchCeiling || run.research_ceiling}`);
    }
    detailEl.textContent = bits.join(" · ")
      || "Cash pipeline snapshot loaded. Research output remains WATCH/WAIT/REJECT.";
  }
}

function renderSourceOperations(compiler, catalog, attempts, outputs, freshness, results) {
  const latestAttempt = sourceOpsLatestBy(attempts, "source_key", "attempted_at");
  const latestOutput = sourceOpsLatestBy(outputs, "source_key", "created_at");
  const freshnessByKey = new Map(freshness.map(row => [String(row.source_key || "").trim(), row]));
  const compilerKeys = new Set((compiler.sourceKeyMap || []).map(row => String(row.sourceKey || "").trim()));

  sourceOpsRows = catalog.map(source => {
    const key = String(source.key || "").trim();
    const fresh = freshnessByKey.get(key);
    const output = latestOutput.get(key);
    const attempt = latestAttempt.get(key);
    const observed = sourceOpsClassify(source, fresh, output, attempt);
    const researchUsable = observed.state === "HEALTHY" &&
      Boolean(fresh?.latest_parser_output_id) &&
      compilerKeys.has(key);
    return {
      key,
      name: source.name || key,
      url: source.url || "",
      authority: source.authority || "UNSPECIFIED",
      ...observed,
      attempted: Boolean(attempt),
      observed: Boolean(attempt || output || fresh),
      parsed: Boolean(output && Number(output.record_count) > 0 && /STRUCTURED/.test(String(output.parser_status || "").toUpperCase())),
      researchUsable,
      effect: sourceOpsResearchEffect(key, observed.state)
    };
  });

  const stateCounts = Object.fromEntries(SOURCE_OPS_STATES.map(name => [name, 0]));
  sourceOpsRows.forEach(row => { stateCounts[row.state] = (stateCounts[row.state] || 0) + 1; });

  const contracts = Number(compiler.normalizedSourceContractCount) || (compiler.sourceContracts || []).length;
  const monitored = catalog.length;
  const attempted = sourceOpsRows.filter(row => row.observed).length;
  const parsed = sourceOpsRows.filter(row => row.parsed).length;
  const current = stateCounts.HEALTHY || 0;
  const usable = sourceOpsRows.filter(row => row.researchUsable).length;

  setSourceOpsValue("ops-contracts", contracts);
  setSourceOpsValue("ops-monitored", monitored);
  setSourceOpsValue("ops-attempted", attempted);
  setSourceOpsValue("ops-parsed", parsed);
  setSourceOpsValue("ops-current", current);
  setSourceOpsValue("ops-usable", usable);
  SOURCE_OPS_STATES.forEach(name => setSourceOpsValue(`ops-count-${name}`, stateCounts[name] || 0));

  const compiledAt = compiler.compiledAt ? new Date(compiler.compiledAt) : new Date();
  const asOf = document.getElementById("source-ops-asof");
  if (asOf) asOf.textContent = `As of ${sourceOpsFormatDate(compiledAt)}`;

  const contract = document.getElementById("source-ops-contract");
  if (contract) {
    const optionalFailures = results.slice(2).filter(result => result.status !== "fulfilled").length;
    contract.textContent = `${contracts} compiler contracts; ${monitored} runtime keys. ${optionalFailures ? optionalFailures + " operational API(s) unavailable; counts fail closed." : "Fetch, parser and freshness evidence loaded."}`;
  }

  const activationReady = compiler.sourceActivationReady === true;
  const gateAuthorized = Number(compiler.gateAuthorizedSourceKeyCount) || 0;
  const permission = document.getElementById("source-ops-permission");
  if (permission) permission.textContent = `sourceActivationReady=${activationReady} | gateAuthorized=${gateAuthorized} | research facts do not unlock CONFIRMED`;

  const needsAttention = (stateCounts.STALE_PARTIAL || 0) + (stateCounts.BLOCKED || 0) +
    (stateCounts.FAILED || 0) + (stateCounts.NOT_ATTEMPTED || 0);
  const panelState = document.getElementById("source-ops-panel-state");
  if (panelState) {
    panelState.textContent = needsAttention > 0 ? `ATTENTION ${needsAttention}` : "OBSERVED";
    panelState.className = `source-ops-state ${needsAttention > 0 ? "is-attention" : "is-ready"}`;
  }

  renderSourceOperationsTable(sourceOpsFilter);
}

function renderSourceOperationsUnavailable(error) {
  sourceOpsRows = [];
  ["ops-contracts", "ops-monitored", "ops-attempted", "ops-parsed", "ops-current", "ops-usable"]
    .forEach(id => setSourceOpsValue(id, "--"));
  SOURCE_OPS_STATES.forEach(name => setSourceOpsValue(`ops-count-${name}`, "--"));

  const state = document.getElementById("source-ops-panel-state");
  if (state) {
    state.textContent = "UNAVAILABLE";
    state.className = "source-ops-state is-error";
  }
  const contract = document.getElementById("source-ops-contract");
  if (contract) contract.textContent = "Operational APIs are unavailable. Catalog cards remain visible, but no source health is inferred.";
  const permission = document.getElementById("source-ops-permission");
  if (permission) permission.textContent = "Activation, gate permission and research usability unknown";
  const asOf = document.getElementById("source-ops-asof");
  if (asOf) asOf.textContent = "As of unavailable";
  const lastGood = document.getElementById("source-ops-lastgood");
  if (lastGood) lastGood.textContent = "Last-good keys: unavailable";
  renderCashTrack(null);
  console.error("[SourceOperations]", error);
  renderSourceOperationsTable(sourceOpsFilter);
}

function renderSourceOperationsTable(filter) {
  const body = document.getElementById("source-ops-table-body");
  const empty = document.getElementById("source-ops-empty");
  const count = document.getElementById("source-ops-detail-count");
  if (!body || !empty || !count) return;

  const attentionStates = new Set(["STALE_PARTIAL", "BLOCKED", "FAILED", "NOT_ATTEMPTED"]);
  const selected = (filter === "ATTENTION"
    ? sourceOpsRows.filter(row => attentionStates.has(row.state))
    : sourceOpsRows.filter(row => row.state === filter))
    .sort((a, b) => SOURCE_OPS_STATES.indexOf(a.state) - SOURCE_OPS_STATES.indexOf(b.state) || a.key.localeCompare(b.key));

  count.textContent = filter === "ATTENTION"
    ? `${selected.length} sources needing attention`
    : `${selected.length} source${selected.length === 1 ? "" : "s"}: ${SOURCE_OPS_META[filter]?.label || filter}`;

  empty.hidden = selected.length > 0;
  body.innerHTML = selected.map(row => {
    const meta = SOURCE_OPS_META[row.state] || SOURCE_OPS_META.NOT_ATTEMPTED;
    const sourceName = escapeHTML(row.name);
    const sourceKey = escapeHTML(row.key);
    const sourceLink = row.url
      ? `<a href="${escapeHTML(row.url)}" target="_blank" rel="noopener">${sourceName}</a>`
      : `<span>${sourceName}</span>`;
    const proof = row.proofAt ? sourceOpsFormatDate(new Date(row.proofAt)) : "No proof";
    const dataDate = row.dataDate ? `Data ${escapeHTML(String(row.dataDate))}` : "Data date unknown";
    return `<tr>
      <td><div class="source-ops-source"><span class="source-ops-status-dot ${meta.dot}"></span><div>${sourceLink}<br><code>${sourceKey}</code></div></div></td>
      <td><span class="source-ops-badge"><span class="source-ops-status-dot ${meta.dot}"></span>${meta.label}</span><span class="source-ops-reason">${escapeHTML(row.reason)}</span></td>
      <td><span class="source-ops-proof">${escapeHTML(proof)}<br>${dataDate}</span></td>
      <td>${escapeHTML(row.effect)}</td>
      <td>Shared HTTP / breaker unspecified<br><span class="source-ops-reason">No automatic retry claim.</span></td>
    </tr>`;
  }).join("");
}

function setSourceOpsDetailOpen(open) {
  const detail = document.getElementById("source-ops-detail");
  const toggle = document.getElementById("source-ops-toggle");
  if (detail) detail.hidden = !open;
  if (toggle) {
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.textContent = open ? "Hide sources" : "View sources";
  }
}

function setSourceOpsValue(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = String(value);
}

function sourceOpsFormatDate(value) {
  if (!(value instanceof Date) || Number.isNaN(value.getTime())) return "Unknown time";
  return value.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  });
}
