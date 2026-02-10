# South Africa Arts Funding Dashboard

A live dashboard tracking grants, tenders, bursaries and calls for proposals for South African arts organisations.

## How it works

- **Dashboard** (`index.html`): Static HTML/CSS/JS page that reads from `data/funding.json` and renders filterable funding opportunities.
- **Scraper** (`scraper/scrape.py`): Python script that fetches live data from key funding sources (NAC, DSAC, NLC, Goethe-Institut, VANSA) and merges it into the data file.
- **Automation** (`.github/workflows/update-funding.yml`): GitHub Actions workflow runs the scraper every Monday at 08:00 SAST.

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
