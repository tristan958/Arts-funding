# Automated source discovery (Claude Code Routine)

This dashboard is **curated-first**: a human always approves what goes live. To
keep it current without manual trawling, a weekly **Claude Code Routine** crawls
the monitored aggregators and funders, extracts new candidate opportunities into
the dashboard's taxonomy, and opens a **review PR**. Nothing publishes
automatically — you merge candidates from `data/candidates.json` into
`data/funding.json` after a look.

Routines run on Anthropic's cloud using your **Claude subscription** — there is
**no `ANTHROPIC_API_KEY` to manage**.

## Moving parts (in this repo)
- `.claude/skills/discover-funding/SKILL.md` — what the routine does each run.
- `tools/discovery/sources.yml` — the seed aggregators/funders to crawl.
- `tools/discovery/SCHEMA.md` — the candidate schema + controlled vocabularies.
- `data/candidates.json` — the review queue the routine appends to (starts `[]`).

## One-time setup
1. Go to **https://claude.ai/code/routines** (Pro, Max, Team, or Enterprise plan).
2. **New routine** → choose this repository (`tristan958/Arts-funding`).
3. **Trigger:** Scheduled → **Weekly** (e.g. Monday 06:00 SAST).
4. **Environment → Network access:** set to **Full** (the routine must reach
   external funder/aggregator sites). See
   https://code.claude.com/docs/en/claude-code-on-the-web#network-access
5. **Prompt:** `Run the discover-funding skill.`
6. Save. The first run will open a PR if it finds anything.

## Reviewing a discovery PR
1. Open the PR; skim the candidate table (each row notes confidence + any
   "verify deadline" flag).
2. Spot-check the official `url` and the deadline for anything you'll keep.
3. Move good entries from `data/candidates.json` into the `opportunities` array
   in `data/funding.json` (and add the funder to `sources` if new), then delete
   them from `candidates.json`. Merge.
4. Vercel redeploys production automatically.

## Tuning
- Add/remove sites in `tools/discovery/sources.yml`.
- Tighten or relax the quality gates in the skill's **Quality gates** section.
- If a source keeps getting blocked (bot protection), prefer its RSS/sitemap or
  drop it — the skill already flags blocked sources for manual review.
