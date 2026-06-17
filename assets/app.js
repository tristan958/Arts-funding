(() => {
  "use strict";

  const DATA_URL = "data/funding.json";
  const ROLLING = new Set(["Rolling", "Varies", "Varies per tender"]);

  /** @type {Array<Object>} */
  let allOpportunities = [];
  let sources = [];
  // Cache of id -> days-until-deadline so we don't re-parse dates on every sort/filter.
  const daysCache = new Map();

  const els = {};
  const FILTER_IDS = ["filterType", "filterStatus", "filterFunder", "filterSort", "searchInput"];

  // --- Helpers ---------------------------------------------------------------

  /** Escape text destined for innerHTML. Data is third-party (scraped) so this is required. */
  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function isRolling(dateStr) {
    return !dateStr || ROLLING.has(dateStr) || dateStr.startsWith("Varies") || dateStr.startsWith("Rolling");
  }

  function daysUntil(opp) {
    if (daysCache.has(opp.id)) return daysCache.get(opp.id);
    let result = null;
    if (!isRolling(opp.deadline)) {
      const deadline = new Date(opp.deadline + "T23:59:59");
      if (!Number.isNaN(deadline.getTime())) {
        result = Math.ceil((deadline - Date.now()) / 86400000);
      }
    }
    daysCache.set(opp.id, result);
    return result;
  }

  function formatDate(dateStr) {
    if (isRolling(dateStr)) return dateStr || "N/A";
    const d = new Date(dateStr + "T00:00:00");
    if (Number.isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString("en-ZA", { day: "numeric", month: "long", year: "numeric" });
  }

  /** Returns { text, level } for a deadline pill, or null when nothing useful to show. */
  function deadlineInfo(opp) {
    if (isRolling(opp.deadline)) return { text: opp.deadline || "Rolling", level: "rolling" };
    const days = daysUntil(opp);
    if (days === null) return null;
    if (days < 0) return { text: "Closed", level: "passed" };
    if (days === 0) return { text: "Closes today", level: "urgent" };
    if (days <= 7) return { text: `${days} day${days > 1 ? "s" : ""} left`, level: "urgent" };
    if (days <= 30) return { text: `${days} days left`, level: "soon" };
    return { text: `${days} days left`, level: "open" };
  }

  function isClosingSoon(opp) {
    if (opp.status !== "open") return false;
    const d = daysUntil(opp);
    return d !== null && d >= 0 && d <= 30;
  }

  // --- Rendering -------------------------------------------------------------

  function renderStats() {
    const open = allOpportunities.filter((o) => o.status === "open");
    els.statTotal.textContent = allOpportunities.length;
    els.statOpen.textContent = open.length;
    els.statClosingSoon.textContent = open.filter(isClosingSoon).length;
    els.statClosed.textContent = allOpportunities.filter((o) => o.status === "closed").length;
  }

  function cardHTML(opp) {
    const dl = deadlineInfo(opp);
    const tags = (opp.focus_areas || [])
      .map((f) => `<li class="tag">${esc(f)}</li>`)
      .join("");

    const more = (opp.eligibility || opp.how_to_apply)
      ? `<details class="card-more">
           <summary>Eligibility &amp; how to apply</summary>
           ${opp.eligibility ? `<p><strong>Eligibility:</strong> ${esc(opp.eligibility)}</p>` : ""}
           ${opp.how_to_apply ? `<p><strong>How to apply:</strong> ${esc(opp.how_to_apply)}</p>` : ""}
         </details>`
      : "";

    return `
      <article class="card status-${esc(opp.status)}">
        <div class="card-head">
          <div class="card-headings">
            <h3 class="card-title">${esc(opp.title)}</h3>
            <p class="card-funder">${esc(opp.funder)}</p>
          </div>
          <div class="card-badges">
            <span class="badge badge-type">${esc(opp.type)}</span>
            <span class="badge badge-${esc(opp.status)}">${esc(opp.status)}</span>
          </div>
        </div>
        <p class="card-desc">${esc(opp.description)}</p>
        ${tags ? `<ul class="card-tags">${tags}</ul>` : ""}
        <dl class="card-facts">
          <div class="fact">
            <dt>Deadline</dt>
            <dd>${esc(formatDate(opp.deadline))}${dl ? ` <span class="pill pill-${dl.level}">${esc(dl.text)}</span>` : ""}</dd>
          </div>
          <div class="fact">
            <dt>Amount</dt>
            <dd>${esc(opp.amount)}</dd>
          </div>
        </dl>
        ${more}
        <div class="card-actions">
          <a href="${esc(opp.url)}" target="_blank" rel="noopener noreferrer" class="btn btn-primary">
            View details <span aria-hidden="true">↗</span>
          </a>
        </div>
      </article>`;
  }

  function sortOpps(opps) {
    const mode = els.filterSort.value;
    const copy = [...opps];
    if (mode === "title") return copy.sort((a, b) => a.title.localeCompare(b.title));
    if (mode === "funder") return copy.sort((a, b) => a.funder.localeCompare(b.funder) || a.title.localeCompare(b.title));
    if (mode === "added") return copy.sort((a, b) => (b.date_added || "").localeCompare(a.date_added || ""));
    // default: deadline — open first, soonest deadline first, rolling/closed last
    return copy.sort((a, b) => {
      if (a.status !== b.status) return a.status === "open" ? -1 : 1;
      const da = daysUntil(a);
      const db = daysUntil(b);
      if (da === null && db === null) return 0;
      if (da === null) return 1;
      if (db === null) return -1;
      return da - db;
    });
  }

  function renderGrid(opps) {
    if (opps.length === 0) {
      els.grid.innerHTML = `
        <div class="empty-state">
          <p class="empty-title">No opportunities match your filters</p>
          <button class="btn btn-primary" type="button" id="emptyReset">Clear filters</button>
        </div>`;
      document.getElementById("emptyReset").addEventListener("click", resetFilters);
      return;
    }
    els.grid.innerHTML = sortOpps(opps).map(cardHTML).join("");
  }

  function renderSources() {
    els.sourcesGrid.innerHTML = sources
      .map(
        (s) =>
          `<a class="source-card" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.name)}</a>`
      )
      .join("");
  }

  function populateFunderFilter() {
    const funders = [...new Set(allOpportunities.map((o) => o.funder))].sort((a, b) => a.localeCompare(b));
    els.filterFunder.append(
      ...funders.map((f) => new Option(f, f))
    );
  }

  // --- Filtering -------------------------------------------------------------

  function getFiltered() {
    const type = els.filterType.value;
    const status = els.filterStatus.value;
    const funder = els.filterFunder.value;
    const search = els.searchInput.value.toLowerCase().trim();

    return allOpportunities.filter((o) => {
      if (type !== "all" && o.type !== type) return false;
      if (status === "closing") {
        if (!isClosingSoon(o)) return false;
      } else if (status !== "all" && o.status !== status) {
        return false;
      }
      if (funder !== "all" && o.funder !== funder) return false;
      if (search) {
        const haystack = `${o.title} ${o.funder} ${o.description} ${(o.focus_areas || []).join(" ")}`.toLowerCase();
        if (!haystack.includes(search)) return false;
      }
      return true;
    });
  }

  function applyFilters() {
    const filtered = getFiltered();
    renderGrid(filtered);
    els.resultCount.textContent =
      `Showing ${filtered.length} of ${allOpportunities.length} opportunities`;
    syncStatCards();
    toggleResetButton();
    saveStateToURL();
  }

  function syncStatCards() {
    const active = els.filterStatus.value;
    els.statCards.forEach((card) => {
      card.classList.toggle("is-active", card.dataset.status === active);
    });
  }

  // --- Filter state: defaults, reset, URL sync -------------------------------

  const DEFAULTS = { type: "all", status: "open", funder: "all", sort: "deadline", q: "" };

  function currentState() {
    return {
      type: els.filterType.value,
      status: els.filterStatus.value,
      funder: els.filterFunder.value,
      sort: els.filterSort.value,
      q: els.searchInput.value.trim(),
    };
  }

  function toggleResetButton() {
    const s = currentState();
    const changed = Object.keys(DEFAULTS).some((k) => s[k] !== DEFAULTS[k]);
    els.resetFilters.hidden = !changed;
  }

  function resetFilters() {
    els.filterType.value = DEFAULTS.type;
    els.filterStatus.value = DEFAULTS.status;
    els.filterFunder.value = DEFAULTS.funder;
    els.filterSort.value = DEFAULTS.sort;
    els.searchInput.value = DEFAULTS.q;
    applyFilters();
  }

  function saveStateToURL() {
    const s = currentState();
    const params = new URLSearchParams();
    Object.keys(DEFAULTS).forEach((k) => {
      if (s[k] && s[k] !== DEFAULTS[k]) params.set(k, s[k]);
    });
    const qs = params.toString();
    history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
  }

  function loadStateFromURL() {
    const p = new URLSearchParams(location.search);
    if (p.has("type")) els.filterType.value = p.get("type");
    if (p.has("status")) els.filterStatus.value = p.get("status");
    if (p.has("funder")) els.filterFunder.value = p.get("funder");
    if (p.has("sort")) els.filterSort.value = p.get("sort");
    if (p.has("q")) els.searchInput.value = p.get("q");
  }

  // --- Theme -----------------------------------------------------------------

  function initTheme() {
    const stored = localStorage.getItem("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setTheme(stored || (prefersDark ? "dark" : "light"));
    els.themeToggle.addEventListener("click", () => {
      setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
    });
  }

  function setTheme(theme) {
    document.documentElement.dataset.theme = theme;
    els.themeToggle.setAttribute("aria-pressed", String(theme === "dark"));
    localStorage.setItem("theme", theme);
  }

  // --- Init ------------------------------------------------------------------

  function debounce(fn, ms) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  function showSkeletons() {
    els.grid.innerHTML = Array.from({ length: 6 }, () =>
      `<div class="card card-skeleton" aria-hidden="true">
         <div class="sk sk-line sk-title"></div>
         <div class="sk sk-line sk-sub"></div>
         <div class="sk sk-block"></div>
         <div class="sk sk-line"></div>
       </div>`
    ).join("");
  }

  function showError(message) {
    els.grid.setAttribute("aria-busy", "false");
    els.grid.innerHTML = `
      <div class="empty-state">
        <p class="empty-title">Couldn't load funding data</p>
        <p class="empty-sub">${esc(message)}</p>
        <button class="btn btn-primary" type="button" id="retryBtn">Try again</button>
      </div>`;
    document.getElementById("retryBtn").addEventListener("click", load);
  }

  async function load() {
    showSkeletons();
    els.grid.setAttribute("aria-busy", "true");
    try {
      const resp = await fetch(DATA_URL, { cache: "no-cache" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      allOpportunities = data.opportunities || [];
      sources = data.sources || [];
      daysCache.clear();

      els.lastUpdated.textContent = data.last_updated
        ? `Data last updated: ${formatDate(data.last_updated)}`
        : "";
      els.footerDate.textContent = formatDate(data.last_updated);

      // Funder filter is populated once; clear extras on retry.
      els.filterFunder.length = 1;
      populateFunderFilter();
      loadStateFromURL();
      renderSources();
      renderStats();
      applyFilters();
      els.grid.setAttribute("aria-busy", "false");
    } catch (err) {
      showError(err.message);
    }
  }

  function init() {
    // Cache element references.
    [
      "lastUpdated", "footerDate", "filterType", "filterStatus", "filterFunder",
      "filterSort", "searchInput", "resultCount", "resetFilters", "sourcesGrid",
      "themeToggle", "statTotal", "statOpen", "statClosingSoon", "statClosed",
    ].forEach((id) => (els[id] = document.getElementById(id)));
    els.grid = document.getElementById("opportunitiesGrid");
    els.statCards = Array.from(document.querySelectorAll(".stat-card"));

    initTheme();

    els.filterType.addEventListener("change", applyFilters);
    els.filterStatus.addEventListener("change", applyFilters);
    els.filterFunder.addEventListener("change", applyFilters);
    els.filterSort.addEventListener("change", applyFilters);
    els.searchInput.addEventListener("input", debounce(applyFilters, 200));
    els.resetFilters.addEventListener("click", resetFilters);
    els.statCards.forEach((card) =>
      card.addEventListener("click", () => {
        els.filterStatus.value = card.dataset.status;
        applyFilters();
      })
    );

    load();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
