/* ===========================================================================
   SA ARTS FUNDING DASHBOARD — app.js
   Plain ES — no framework, no build. Fetches data/funding.json.
   =========================================================================== */
(function () {
  "use strict";

  const DATA_URL = "data/funding.json";

  /* ---------- tiny helpers ---------- */
  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const el = (tag, attrs = {}, html) => {
    const n = document.createElement(tag);
    for (const k in attrs) {
      if (k === "class") n.className = attrs[k];
      else if (attrs[k] != null) n.setAttribute(k, attrs[k]);
    }
    if (html != null) n.innerHTML = html;
    return n;
  };
  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  const TODAY = startOfDay(new Date());
  function startOfDay(d) { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; }

  /* ---------- deadline math ---------- */
  // returns { kind, daysLeft, dateLabel, word } where kind drives all urgency styling.
  // Handles real dates plus free-text "Rolling…" / "Varies…" deadlines.
  function deadlineInfo(opp) {
    const raw = opp.deadline;
    if (!raw || /^rolling/i.test(raw)) return { kind: "rolling", word: "Rolling" };
    if (/^varies/i.test(raw)) return { kind: "varies", word: "Varies" };

    const d = startOfDay(new Date(raw));
    if (isNaN(d)) return { kind: "varies", word: "Varies" };

    const days = Math.round((d - TODAY) / 86400000);
    const dateLabel = d.toLocaleDateString("en-ZA", { day: "numeric", month: "short", year: "numeric" });

    if (opp.status === "closed" || days < 0)
      return { kind: "closed", word: "Closed", dateLabel, daysLeft: days };
    if (days === 0) return { kind: "urgent", word: "Today", dateLabel, daysLeft: 0 };
    if (days <= 7)  return { kind: "urgent", daysLeft: days, dateLabel };
    if (days <= 30) return { kind: "soon",   daysLeft: days, dateLabel };
    return { kind: "open", daysLeft: days, dateLabel };
  }

  // is this opp effectively closed (status OR past deadline)?
  function isClosed(opp) {
    const i = deadlineInfo(opp);
    return opp.status === "closed" || i.kind === "closed";
  }
  // open AND within 30 days (incl. today)
  function isClosingSoon(opp) {
    if (isClosed(opp)) return false;
    const i = deadlineInfo(opp);
    return i.kind === "urgent" || i.kind === "soon";
  }

  /* ---------- state (URL-synced) ---------- */
  const DEFAULTS = { q: "", type: "all", discipline: "all", purpose: "all", status: "open", funder: "all", sort: "deadline", view: "all" };

  const intersects = (arr, set) => Array.isArray(arr) && arr.some((x) => set.includes(x));
  // Curated "saved views" — each is a predicate over the enriched taxonomy fields.
  const VIEW_PREDICATES = {
    all: () => true,
    vansa: (o) => (o.audiences || []).includes("vansa"),
    newmedia: (o) => intersects(o.disciplines, ["new-media-digital", "podcast-audio", "film-screen"]),
    capacity: (o) => (o.purpose || []).includes("capacity-building"),
    experimental: (o) => intersects(o.tags, ["experimental", "site-specific", "spatial", "socially-engaged", "research-based", "public-space", "interdisciplinary"]),
  };

  function readURL() {
    const p = new URLSearchParams(location.search);
    const s = { ...DEFAULTS };
    for (const k in DEFAULTS) if (p.has(k)) s[k] = p.get(k);
    return s;
  }
  function writeURL(s, replace) {
    const p = new URLSearchParams();
    for (const k in DEFAULTS) if (s[k] !== DEFAULTS[k]) p.set(k, s[k]);
    const url = location.pathname + (p.toString() ? "?" + p.toString() : "");
    history[replace ? "replaceState" : "pushState"]({}, "", url);
  }

  let state = readURL();
  let DATA = [];
  let SOURCES = [];
  let LAST_UPDATED = "";

  /* ---------- filtering + sorting ---------- */
  function apply() {
    const q = state.q.trim().toLowerCase();
    let out = DATA.filter((o) => {
      if (state.type !== "all" && o.type !== state.type) return false;
      if (state.funder !== "all" && o.funder !== state.funder) return false;

      // Discipline matches the entry's disciplines, or entries marked "all-disciplines".
      const disc = o.disciplines || [];
      if (state.discipline !== "all" && !disc.includes(state.discipline) && !disc.includes("all-disciplines")) return false;
      if (state.purpose !== "all" && !(o.purpose || []).includes(state.purpose)) return false;
      if (state.view !== "all" && !(VIEW_PREDICATES[state.view] || VIEW_PREDICATES.all)(o)) return false;

      if (state.status === "open" && isClosed(o)) return false;
      if (state.status === "closed" && !isClosed(o)) return false;
      if (state.status === "closing" && !isClosingSoon(o)) return false;

      if (q) {
        const hay = [o.title, o.funder, o.description, (o.focus_areas || []).join(" "), o.type]
          .join(" ").toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    out.sort((a, b) => {
      switch (state.sort) {
        case "added":   return new Date(b.date_added) - new Date(a.date_added);
        case "title":   return a.title.localeCompare(b.title);
        case "funder":  return a.funder.localeCompare(b.funder) || a.title.localeCompare(b.title);
        case "deadline":
        default: {
          // soonest real deadline first; rolling/varies after dated; closed last
          const rank = (o) => {
            const i = deadlineInfo(o);
            if (i.kind === "closed") return [3, 0];
            if (i.kind === "rolling" || i.kind === "varies") return [2, 0];
            return [1, i.daysLeft];
          };
          const ra = rank(a), rb = rank(b);
          return ra[0] - rb[0] || ra[1] - rb[1];
        }
      }
    });
    return out;
  }

  /* ---------- stat counts (always over the full dataset) ---------- */
  function counts() {
    return {
      total: DATA.length,
      open: DATA.filter((o) => !isClosed(o)).length,
      soon: DATA.filter(isClosingSoon).length,
      closed: DATA.filter(isClosed).length,
    };
  }

  /* ---------- card render ---------- */
  const ARROW = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 11L11 5M11 5H6M11 5V10"/></svg>';
  const ARROW_SRC = '<svg class="source__arrow" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M5 11L11 5M11 5H6M11 5V10"/></svg>';
  const CHEV  = '<svg class="chev" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6l4 4 4-4"/></svg>';

  function cardEl(o) {
    const di = deadlineInfo(o);
    const closed = isClosed(o);
    const accentClass =
      closed ? "card--closed"
      : di.kind === "urgent" ? "card--urgent"
      : di.kind === "soon" ? "card--closing"
      : "card--open";

    const card = el("article", { class: "card " + accentClass });

    // deadline cell inner
    let dlInner;
    if (di.kind === "rolling" || di.kind === "varies") {
      dlInner = `<div class="deadline__word">${esc(di.word)}</div>
                 <div class="deadline__date">Apply anytime</div>`;
    } else if (di.kind === "closed") {
      dlInner = `<div class="deadline__word">Closed</div>
                 <div class="deadline__date">${esc(di.dateLabel || "")}</div>`;
    } else if (di.word === "Today") {
      dlInner = `<div class="deadline__word">Today</div>
                 <div class="deadline__date">${esc(di.dateLabel)}</div>`;
    } else {
      dlInner = `<div class="deadline"><span class="deadline__num">${di.daysLeft}</span><span class="deadline__unit">${di.daysLeft === 1 ? "day" : "days"} left</span></div>
                 <div class="deadline__date">${esc(di.dateLabel)}</div>`;
    }
    const dlStateClass =
      di.kind === "urgent" ? "is-urgent"
      : di.kind === "soon" ? "is-soon"
      : di.kind === "closed" ? "is-closed"
      : (di.kind === "open" ? "is-open" : "");

    const tags = (o.focus_areas || [])
      .slice(0, 4)
      .map((t) => `<span class="tag">${esc(t)}</span>`)
      .join("");

    card.innerHTML = `
      <div class="card__body">
        <div class="card__top">
          <div class="card__head">
            <span class="card__type">${esc(o.type)}</span>
            <h3 class="card__title">${esc(o.title)}</h3>
            <div class="card__funder">${esc(o.funder)}</div>
          </div>
          <span class="badge ${closed ? "badge--closed" : "badge--open"}">${closed ? "Closed" : "Open"}</span>
        </div>

        <p class="card__desc">${esc(o.description)}</p>

        ${tags ? `<div class="tags">${tags}</div>` : ""}

        <div class="facts">
          <div class="fact fact--deadline ${dlStateClass}">
            <div class="fact__k">Deadline</div>
            ${dlInner}
          </div>
          <div class="fact">
            <div class="fact__k">Amount</div>
            <div class="amount__v">${esc(o.amount || "—")}</div>
          </div>
        </div>
      </div>

      <details class="more">
        <summary>Eligibility &amp; how to apply ${CHEV}</summary>
        <div class="more__inner">
          <div class="more__block">
            <h4>Eligibility</h4>
            <p>${esc(o.eligibility || "See funder site for details.")}</p>
          </div>
          <div class="more__block">
            <h4>How to apply</h4>
            <p>${esc(o.how_to_apply || "See funder site for details.")}</p>
          </div>
        </div>
      </details>

      <div class="card__cta">
        <a class="btn-view" href="${esc(o.url)}" target="_blank" rel="noopener noreferrer">
          View details ${ARROW}
        </a>
      </div>`;
    return card;
  }

  /* ---------- skeletons ---------- */
  function skeletons(n) {
    const frag = document.createDocumentFragment();
    for (let i = 0; i < n; i++) {
      frag.appendChild(el("div", { class: "skel-card", "aria-hidden": "true" },
        `<div class="shimmer l-type"></div>
         <div class="shimmer l-title"></div>
         <div class="shimmer l-sub"></div>
         <div class="shimmer l-text"></div>
         <div class="shimmer l-band"></div>`));
    }
    return frag;
  }

  /* ---------- DOM refs ---------- */
  const grid = $("#grid");
  const resultCount = $("#result-count");

  const DIA = '<svg viewBox="0 0 56 56" fill="none"><path d="M28 4 52 28 28 52 4 28Z" stroke="currentColor" stroke-width="2.5"/><path d="M28 18 38 28 28 38 18 28Z" fill="currentColor"/></svg>';

  /* ---------- render grid + states ---------- */
  function renderResults() {
    const list = apply();
    grid.innerHTML = "";

    if (list.length === 0) {
      grid.appendChild(el("div", { class: "state" },
        `<div class="state__emblem">${DIA}</div>
         <h3>No opportunities match</h3>
         <p>Try widening your filters — switch Status to “All”, or clear your search.</p>
         <button class="btn-line" id="clear-filters" type="button">Clear all filters</button>`));
      $("#clear-filters").addEventListener("click", resetAll);
    } else {
      const frag = document.createDocumentFragment();
      list.forEach((o) => frag.appendChild(cardEl(o)));
      grid.appendChild(frag);
    }

    resultCount.innerHTML = `Showing <b>${list.length}</b> of ${DATA.length} opportunities`;
    syncControls();
    renderStats();
  }

  function renderError(message) {
    grid.setAttribute("aria-busy", "false");
    grid.innerHTML = "";
    grid.appendChild(el("div", { class: "state state--error" },
      `<div class="state__emblem">${DIA}</div>
       <h3>Couldn’t load opportunities</h3>
       <p>${esc(message || "Something went wrong fetching the latest data. Please try again.")}</p>
       <button class="btn-line" id="retry" type="button">Retry</button>`));
    $("#retry").addEventListener("click", boot);
  }

  /* ---------- stats ---------- */
  function renderStats() {
    const c = counts();
    $("#stat-total .stat__num").textContent = c.total;
    $("#stat-open .stat__num").textContent = c.open;
    $("#stat-soon .stat__num").textContent = c.soon;
    $("#stat-closed .stat__num").textContent = c.closed;

    // pressed reflects current status filter
    const map = { all: "stat-total", open: "stat-open", closing: "stat-soon", closed: "stat-closed" };
    $$(".stat").forEach((s) => s.setAttribute("aria-pressed", s.id === map[state.status] ? "true" : "false"));
  }

  /* ---------- monitored sources (from data.sources) ---------- */
  function renderSources() {
    const wrap = $("#sources-grid");
    if (!wrap) return;
    wrap.innerHTML = SOURCES.map((s) =>
      `<a class="source" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">` +
      `<span class="source__dia" aria-hidden="true"></span>` +
      `<span class="source__name">${esc(s.name)}</span>${ARROW_SRC}</a>`
    ).join("");
  }

  /* ---------- controls binding ---------- */
  function buildSelectOptions() {
    const funders = [...new Set(DATA.map((o) => o.funder))].sort((a, b) => a.localeCompare(b));
    const fSel = $("#f-funder");
    fSel.innerHTML = `<option value="all">All funders</option>` +
      funders.map((f) => `<option value="${esc(f)}">${esc(f)}</option>`).join("");
  }

  function syncControls() {
    $("#f-search").value = state.q;
    $("#f-type").value = state.type;
    $("#f-discipline").value = state.discipline;
    $("#f-purpose").value = state.purpose;
    $("#f-status").value = state.status;
    $("#f-funder").value = state.funder;
    $("#f-sort").value = state.sort;
    $$(".view-chip").forEach((c) => c.classList.toggle("is-active", c.dataset.view === state.view));
  }

  function update(patch, replace) {
    state = { ...state, ...patch };
    writeURL(state, replace);
    renderResults();
  }

  function resetAll() {
    state = { ...DEFAULTS };
    writeURL(state, false);
    renderResults();
  }

  let searchTimer = null;
  function bindControls() {
    $("#f-search").addEventListener("input", (e) => {
      const v = e.target.value;
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => update({ q: v }, true), 220);
    });
    $("#f-type").addEventListener("change",       (e) => update({ type: e.target.value }));
    $("#f-discipline").addEventListener("change", (e) => update({ discipline: e.target.value }));
    $("#f-purpose").addEventListener("change",    (e) => update({ purpose: e.target.value }));
    $("#f-status").addEventListener("change",     (e) => update({ status: e.target.value }));
    $("#f-funder").addEventListener("change",     (e) => update({ funder: e.target.value }));
    $("#f-sort").addEventListener("change",       (e) => update({ sort: e.target.value }));
    $("#reset").addEventListener("click", resetAll);

    // Saved views — each chip jumps to a curated lens across all statuses.
    $$(".view-chip").forEach((chip) =>
      chip.addEventListener("click", () => {
        const v = chip.dataset.view;
        if (v === "all") { resetAll(); return; }
        update({ ...DEFAULTS, view: v, status: "all" });
      })
    );

    // stat cards → set status filter
    const map = { "stat-total": "all", "stat-open": "open", "stat-soon": "closing", "stat-closed": "closed" };
    $$(".stat").forEach((s) =>
      s.addEventListener("click", () => update({ status: map[s.id] }))
    );

    // back/forward
    window.addEventListener("popstate", () => { state = readURL(); renderResults(); });
  }

  /* ---------- theme ---------- */
  function initTheme() {
    const saved = localStorage.getItem("safd-theme");
    const sysDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const theme = saved || (sysDark ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", theme);
    const btn = $("#theme-toggle");
    btn.setAttribute("aria-pressed", theme === "dark");
    btn.addEventListener("click", () => {
      const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      btn.setAttribute("aria-pressed", next === "dark");
      try { localStorage.setItem("safd-theme", next); } catch (e) {}
    });
  }

  /* ---------- updated date (from data.last_updated) ---------- */
  function initUpdated() {
    const node = $("#updated-date");
    if (!node || !LAST_UPDATED) return;
    const d = startOfDay(new Date(LAST_UPDATED));
    node.textContent = isNaN(d)
      ? LAST_UPDATED
      : d.toLocaleDateString("en-ZA", { day: "numeric", month: "long", year: "numeric" });
  }

  /* ---------- boot: skeleton → fetch → content ---------- */
  async function boot() {
    grid.setAttribute("aria-busy", "true");
    grid.innerHTML = "";
    grid.appendChild(skeletons(6));
    resultCount.textContent = "Loading opportunities…";

    try {
      const resp = await fetch(DATA_URL, { cache: "no-cache" });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const data = await resp.json();

      DATA = (data.opportunities || []).slice();
      SOURCES = data.sources || [];
      LAST_UPDATED = data.last_updated || "";

      buildSelectOptions();
      renderSources();
      initUpdated();
      renderResults();
      grid.setAttribute("aria-busy", "false");
    } catch (err) {
      console.error(err);
      renderError(err && err.message);
    }
  }

  /* ---------- go ---------- */
  document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    bindControls();
    boot();
  });
})();
