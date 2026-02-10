(() => {
  "use strict";

  const DATA_URL = "data/funding.json";

  let allOpportunities = [];
  let sources = [];

  // --- Helpers ---

  function daysUntil(dateStr) {
    if (!dateStr || dateStr === "Rolling" || dateStr.startsWith("Varies")) return null;
    const deadline = new Date(dateStr + "T23:59:59");
    const now = new Date();
    return Math.ceil((deadline - now) / (1000 * 60 * 60 * 24));
  }

  function formatDate(dateStr) {
    if (!dateStr || dateStr === "Rolling" || dateStr.startsWith("Varies")) return dateStr || "N/A";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-ZA", { day: "numeric", month: "long", year: "numeric" });
  }

  function deadlineLabel(dateStr) {
    const days = daysUntil(dateStr);
    if (days === null) return "";
    if (days < 0) return "Deadline passed";
    if (days === 0) return "Closes today!";
    if (days <= 7) return `${days} day${days > 1 ? "s" : ""} left`;
    if (days <= 30) return `${days} days left`;
    return "";
  }

  // --- Rendering ---

  function renderStats(opps) {
    const open = opps.filter((o) => o.status === "open");
    const closed = opps.filter((o) => o.status === "closed");
    const closingSoon = open.filter((o) => {
      const d = daysUntil(o.deadline);
      return d !== null && d >= 0 && d <= 30;
    });

    document.getElementById("statTotal").textContent = opps.length;
    document.getElementById("statOpen").textContent = open.length;
    document.getElementById("statClosingSoon").textContent = closingSoon.length;
    document.getElementById("statClosed").textContent = closed.length;
  }

  function renderCard(opp) {
    const dl = deadlineLabel(opp.deadline);
    const focusTags = (opp.focus_areas || [])
      .map((f) => `<span class="focus-tag">${f}</span>`)
      .join("");

    return `
      <article class="card status-${opp.status}">
        <div class="card-header">
          <h3 class="card-title">${opp.title}</h3>
          <div class="card-badges">
            <span class="badge badge-${opp.status}">${opp.status}</span>
            <span class="badge badge-type">${opp.type}</span>
          </div>
        </div>
        <p class="card-funder">${opp.funder}</p>
        <p class="card-description">${opp.description}</p>
        <div class="card-meta">
          <span><strong>Deadline:</strong> ${formatDate(opp.deadline)}</span>
          <span><strong>Amount:</strong> ${opp.amount}</span>
          ${dl ? `<span class="card-deadline-warning">${dl}</span>` : ""}
        </div>
        ${focusTags ? `<div class="card-focus">${focusTags}</div>` : ""}
        <div class="card-actions">
          <a href="${opp.url}" target="_blank" rel="noopener" class="btn btn-primary">View Details</a>
          ${opp.how_to_apply ? `<span class="btn btn-outline" title="${opp.how_to_apply}">How to Apply</span>` : ""}
        </div>
      </article>
    `;
  }

  function renderGrid(opps) {
    const grid = document.getElementById("opportunitiesGrid");
    if (opps.length === 0) {
      grid.innerHTML = '<p class="no-results">No opportunities match your filters.</p>';
      return;
    }
    // Sort: open first, then by deadline ascending (rolling deadlines last)
    const sorted = [...opps].sort((a, b) => {
      if (a.status !== b.status) return a.status === "open" ? -1 : 1;
      const da = daysUntil(a.deadline);
      const db = daysUntil(b.deadline);
      if (da === null && db === null) return 0;
      if (da === null) return 1;
      if (db === null) return -1;
      return da - db;
    });
    grid.innerHTML = sorted.map(renderCard).join("");
  }

  function renderSources() {
    const grid = document.getElementById("sourcesGrid");
    grid.innerHTML = sources
      .map(
        (s) => `
        <div class="source-card">
          <a href="${s.url}" target="_blank" rel="noopener">${s.name}</a>
        </div>`
      )
      .join("");
  }

  function populateFunderFilter() {
    const select = document.getElementById("filterFunder");
    const funders = [...new Set(allOpportunities.map((o) => o.funder))].sort();
    funders.forEach((f) => {
      const opt = document.createElement("option");
      opt.value = f;
      opt.textContent = f;
      select.appendChild(opt);
    });
  }

  // --- Filtering ---

  function getFiltered() {
    const type = document.getElementById("filterType").value;
    const status = document.getElementById("filterStatus").value;
    const funder = document.getElementById("filterFunder").value;
    const search = document.getElementById("searchInput").value.toLowerCase().trim();

    return allOpportunities.filter((o) => {
      if (type !== "all" && o.type !== type) return false;
      if (status !== "all" && o.status !== status) return false;
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
    renderStats(filtered);
  }

  // --- Init ---

  async function init() {
    try {
      const resp = await fetch(DATA_URL);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();

      allOpportunities = data.opportunities || [];
      sources = data.sources || [];

      document.getElementById("lastUpdated").textContent = `Data last updated: ${formatDate(data.last_updated)}`;
      document.getElementById("footerDate").textContent = formatDate(data.last_updated);

      populateFunderFilter();
      renderSources();
      applyFilters();
    } catch (err) {
      document.getElementById("opportunitiesGrid").innerHTML =
        `<p class="no-results">Failed to load data. ${err.message}</p>`;
    }
  }

  // Event listeners
  document.getElementById("filterType").addEventListener("change", applyFilters);
  document.getElementById("filterStatus").addEventListener("change", applyFilters);
  document.getElementById("filterFunder").addEventListener("change", applyFilters);
  document.getElementById("searchInput").addEventListener("input", applyFilters);

  init();
})();
