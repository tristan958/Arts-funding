# Automated updates (Claude Code Routine)

A weekly **Claude Code Routine** keeps the dashboard current with **no API key**
— it runs on Anthropic's cloud using your Claude subscription. It updates the
live site **directly**: it adds newly-discovered open opportunities, refreshes
each entry's open/closed status, **removes opportunities that have closed**, and
commits straight to the default branch (Vercel then redeploys).

> The dashboard intentionally shows **current opportunities only** — closed/past
> calls are pruned automatically.

## Moving parts (in this repo)
- `.claude/skills/discover-funding/SKILL.md` — what the routine does each run.
- `tools/discovery/sources.yml` — the seed aggregators/funders/tender portals to crawl.
- `tools/discovery/SCHEMA.md` — the entry schema + controlled vocabularies.
- `tools/discovery/fetch_tenders.py` — stdlib script that pulls **arts/culture government
  tenders** from the National Treasury **eTenders OCDS API** (structured, dated, CC-BY) and
  prints ready-shaped candidate entries. Far more robust than scraping the JS eTenders site.

## One-time setup (must be a **remote** routine)
1. Go to **https://claude.ai/code/routines** (Pro / Max / Team / Enterprise).
2. **New routine** → choose this repository (`tristan958/Arts-funding`).
3. **Trigger:** Scheduled → **Weekly** (e.g. Monday 06:00 SAST).
4. **Environment → Network access:** **Full** (needed to crawl funder sites) —
   https://code.claude.com/docs/en/claude-code-on-the-web#network-access
5. **Prompt:** either `Run the discover-funding skill.` **or** paste the full
   prompt below.
6. Save. It will keep the live site updated each week.

### Full routine prompt (self-contained, if you prefer not to rely on the skill)

```
You maintain the South African Arts Funding Dashboard in this repository. Once a
week, keep data/funding.json current and accurate, then commit directly to the
default branch (the site auto-deploys). Steps:
1. Read data/funding.json and tools/discovery/SCHEMA.md.
2. For every entry with a real dated deadline, recompute status (closed if the
   deadline is in the past, else open).
3. REMOVE every opportunity that is closed or past its deadline — the dashboard
   shows only current opportunities (keep live Rolling/Varies/annual ones).
4. Crawl each source in tools/discovery/sources.yml (you have Full network
   access) and find new, currently-open arts-funding opportunities open to South
   African artists or arts organisations.
4b. Run `python3 tools/discovery/fetch_tenders.py` to pull arts/culture government
   tenders from the eTenders OCDS API; treat its JSON output as candidates (drop the
   _source field, re-confirm each closing date, dedupe). It prints [] if unreachable.
5. For each genuinely new one that passes basic checks (real funder URL you
   fetched, not a duplicate, currently open, parseable or Rolling/Varies
   deadline), append a full entry matching tools/discovery/SCHEMA.md — include
   disciplines, purpose, eligibility_type, org_focus, tags, audiences, region;
   date_added = today; add audiences:["vansa"] for contemporary-visual-arts items.
6. Set last_updated to today.
7. Commit directly to the default branch (message like "chore: weekly discovery
   — +N new, -M closed (date)") and push. Do not open a PR.
Never fabricate data — be conservative and accurate. Skip sites that block bots
(try their RSS/sitemap first). If nothing changed, make no commit.
```

## Tuning
- Add/remove crawl targets in `tools/discovery/sources.yml`.
- Adjust the quality gates / removal policy in the skill (e.g. keep recently-closed
  entries for a 30-day grace period instead of removing immediately).
