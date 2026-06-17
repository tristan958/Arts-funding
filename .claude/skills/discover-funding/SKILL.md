---
name: discover-funding
description: Weekly discovery of NEW South African arts-funding opportunities. Crawls the monitored aggregators and funders, extracts candidates into the dashboard's taxonomy schema, dedupes against data/funding.json, and opens a review PR adding to data/candidates.json. Curated-first — it never modifies or auto-publishes curated entries.
---

# Discover funding opportunities

You are running as a scheduled **Routine** to keep the SA Arts Funding Dashboard current. Your job: find NEW, real, currently-relevant arts-funding opportunities for South African artists and arts organisations, and open a **review PR** proposing them. A human merges them into the live data later. **Never invent data. Never modify existing entries in `data/funding.json`.**

## Procedure

1. **Load state.** Read `data/funding.json` (existing `opportunities` + `sources`) and `data/candidates.json` (already-proposed). Build a dedupe set of existing `id`s, lowercased `url`s, and `funder`+`title` pairs.

2. **Crawl sources.** For every entry in `tools/discovery/sources.yml`, fetch its opportunities/calls page (the routine's environment has **Full** network access). Go sequentially and politely. If a page blocks bots (HTTP 403) or fails, try its `/rss`, `/feed`, or sitemap; if still blocked, skip it and record it under "needs manual check" for the PR body.

3. **Extract candidates.** Pull out individual open calls / grants / residencies / fellowships / awards / bursaries. For each, build an object matching `tools/discovery/SCHEMA.md` exactly — including the taxonomy fields (`disciplines`, `purpose`, `eligibility_type`, `org_focus`, `tags`, `audiences`, `region`). Set `date_added` to today (YYYY-MM-DD).

4. **Quality gates.** Keep a candidate only if **all** hold:
   - It is a genuine funding/opportunity (not navigation, a teaser, a news post, or a past/archived call).
   - It is plausibly open to South African artists or arts organisations (SA, pan-African incl. SA, or international explicitly open to SA/Africa).
   - It has a real official `url` you actually fetched.
   - It is **not already** in `funding.json` or `candidates.json` (by `id`, `url`, or `funder`+`title`).
   - It has a parseable deadline **or** an explicit cadence (`Rolling`, `Varies`, or a named annual/quarterly cycle).

5. **Tag thoughtfully.** Use the controlled vocabulary in `SCHEMA.md`. Add `audiences: ["vansa"]` for contemporary-visual-arts-relevant items. Prefer conservative values; when a field is genuinely unknown, use `"Varies"`/empty arrays and flag it — do not guess amounts or deadlines.

6. **Write the review queue.** Append accepted candidates to the JSON array in `data/candidates.json` (keep it valid JSON). **Do not touch `data/funding.json`.**

7. **Open a PR.** Branch `discovery/<YYYY-MM-DD>`; title `Discovery: <N> new funding candidates (week of <YYYY-MM-DD>)`; body = a markdown table (funder · title · type · deadline · confidence · "verify?" flag) plus a "needs manual check" list of any blocked sources. **If there are zero new candidates, do not open a PR.**

## Rules

- **Curated-first.** A human reviews `candidates.json` and promotes entries into `funding.json`. You never publish to `funding.json` yourself.
- **Accuracy over volume.** Five solid candidates beat thirty noisy ones. Never fabricate URLs, deadlines, amounts or eligibility.
- **Respect robots/ToS.** Skip anything that blocks automated access and list it for manual review rather than working around it.
- Keep `data/candidates.json` from growing unbounded: if an entry there has since appeared in `funding.json`, drop it.
