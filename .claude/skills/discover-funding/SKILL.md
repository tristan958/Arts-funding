---
name: discover-funding
description: Weekly AUTO-UPDATE of the SA Arts Funding Dashboard. Crawls monitored aggregators/funders, adds newly-found OPEN opportunities directly to data/funding.json, refreshes every entry's open/closed status by deadline, REMOVES entries that have closed, updates last_updated, and commits straight to the default branch (which auto-deploys to the live site). Accuracy-first; never fabricates.
---

# Auto-update the funding dashboard

You run weekly as a scheduled **Routine** to keep the **live** SA Arts Funding Dashboard current and accurate. You edit `data/funding.json` **directly** and commit to the **default branch** — the site redeploys automatically. There is no review queue. **Never fabricate data.**

## Each run

1. **Load.** Read `data/funding.json` and `tools/discovery/SCHEMA.md` (schema + controlled vocabularies).
2. **Refresh status.** For every existing opportunity that has a real *dated* deadline, recompute `status`: `"closed"` if the deadline is in the past (Africa/Johannesburg time), else `"open"`. Leave `Rolling`/`Varies`/annual entries `"open"` unless you have clear evidence the programme ended.
3. **Remove closed.** Delete every opportunity whose deadline has passed or whose `status` is `"closed"`. The dashboard shows **current opportunities only**. Do **not** delete still-live `Rolling`/`Varies`/annual entries.
4. **Discover.** Crawl each source in `tools/discovery/sources.yml` (the environment has **Full** network access). Extract individual open calls / grants / residencies / fellowships / awards / bursaries / tenders.
5. **Add.** For each genuinely new, **currently-open** opportunity that passes the quality gates, append a fully-formed entry (every schema field, taxonomy included, `date_added` = today) to `opportunities`. Skip anything already present (by `id`, `url`, or `funder`+`title`) or already closed.
6. **Stamp.** Set `last_updated` to today.
7. **Commit directly.** Commit to the **default branch** with a clear message, e.g. `chore: weekly discovery — +N new, -M closed (YYYY-MM-DD)`, and push. **Do not open a PR** — this routine updates the site directly. If nothing changed, make no commit.

## Quality gates (for additions)

Keep a candidate only if **all** hold: it's a genuine funding opportunity (not nav/teaser/news/archived); plausibly open to South African artists or arts organisations (SA, pan-African incl. SA, or international explicitly open to SA/Africa); has a real official `url` you actually fetched; is not a duplicate; and is **currently open** with a parseable deadline or an explicit `Rolling`/`Varies`/annual cadence. Add `audiences: ["vansa"]` for contemporary-visual-arts-relevant items.

## Rules

- **Accuracy over volume.** Never invent URLs, deadlines, amounts or eligibility. When unsure of a value, use `"Varies"` and keep the entry conservative — do not guess.
- **Respect robots/ToS.** Skip sites that block automated access (try their RSS/sitemap first) and note them in the commit message.
- Keep `data/funding.json` **valid JSON** and schema-consistent at all times.
- If pushing to the default branch is ever blocked (branch protection / permissions), fall back to opening a PR and say so in the PR body.
