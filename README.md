# South Africa Arts Funding Dashboard

A live dashboard tracking grants, tenders, bursaries and calls for proposals for South African arts organisations.

## How it works

- **Dashboard** (`index.html`): Static, dependency-free HTML/CSS/JS page that reads from `data/funding.json` and renders filterable, sortable funding opportunities. Features search, type/status/funder filters, sort, shareable filter URLs, light/dark mode and a responsive card grid.
- **Data** (`data/funding.json`): The source of truth. It is **curated-first** — hand-written entries are authoritative and are never overwritten or removed by automation.
- **Scraper** (`scraper/scrape.py`): Python script that discovers new opportunities from key funding sources (NAC, DSAC, Goethe-Institut, VANSA). It only *adds* auto-discovered entries (tagged `"auto": true`), and only candidates that pass strict quality gates — they must mention a funding keyword **and** carry a parseable deadline. Previous auto entries are replaced on every run, so noise can't accumulate. It also keeps every entry's open/closed status in sync with its deadline.
- **Automation** (`.github/workflows/update-funding.yml`): GitHub Actions workflow runs the scraper every Monday at 08:00 SAST.

### Data model

Each opportunity in `data/funding.json` has: `id`, `title`, `funder`, `type` (`grant` \| `tender` \| `bursary` \| `call`), `status` (`open` \| `closed`), `deadline` (`YYYY-MM-DD`, `Rolling`, or `Varies…`), `amount`, `description`, `eligibility`, `focus_areas` (array), `how_to_apply`, `url`, `date_added`. Auto-discovered entries also carry `"auto": true`. To add a curated opportunity, append an object with a unique slug `id` (and no `auto` flag).

## Monitored sources

| Source | URL |
|--------|-----|
| National Arts Council (NAC) | https://www.nac.org.za |
| Dept of Sport, Arts & Culture (DSAC) | https://www.dsac.gov.za |
| National Lotteries Commission (NLC) | https://www.nlcsa.org.za |
| Goethe-Institut South Africa | https://www.goethe.de/ins/za/en/kul/kul.html |
| Business and Arts South Africa (BASA) | https://www.basa.co.za |
| Arts & Culture Trust (ACT) | https://act.org.za |
| VANSA Arts Opportunities | https://vansa.co.za/arts-opportunities/funding/ |
| Western Cape Government | https://www.westerncape.gov.za/cas/service/arts-and-culture-funding |
| eTenders Portal | https://www.etenders.gov.za |

## Local development

Open `index.html` in a browser. For the fetch to work you need a local server:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## Running the scraper manually

```bash
pip install -r requirements.txt
python scraper/scrape.py
```

## Deploying

The dashboard is a static site. Deploy via GitHub Pages, Netlify, or any static host by pointing at the repo root.
