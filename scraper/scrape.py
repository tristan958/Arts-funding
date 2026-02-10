#!/usr/bin/env python3
"""
SA Arts Funding Scraper

Scrapes funding opportunities from key South African arts funding sources
and writes them to data/funding.json.  Designed to run weekly via GitHub
Actions (or manually).

Each scraper function returns a list of opportunity dicts.  The main()
function merges them with any existing manually-curated entries, deduplicates
by id, and writes the result.
"""

import json
import hashlib
import re
import sys
from datetime import date, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FUNDING_FILE = DATA_DIR / "funding.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SA-Arts-Funding-Bot/1.0; "
        "+https://github.com/tristanpringlecoach-coder/Arts-funding)"
    )
}

TIMEOUT = 30  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch(url):
    """GET a URL and return a BeautifulSoup object, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as exc:
        print(f"  [WARN] Failed to fetch {url}: {exc}")
        return None


def make_id(title, funder):
    """Deterministic short id from title + funder."""
    raw = f"{funder}:{title}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def parse_date(text):
    """Try to extract a date from free-form text.  Returns YYYY-MM-DD or None."""
    # Patterns: '13 March 2026', 'March 13, 2026', '2026-03-13'
    for fmt in ("%d %B %Y", "%B %d, %Y", "%Y-%m-%d", "%d %b %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def extract_dates_from_text(text):
    """Search for date-like patterns in a block of text."""
    patterns = [
        r"\d{1,2}\s+\w+\s+\d{4}",
        r"\w+\s+\d{1,2},?\s+\d{4}",
        r"\d{4}-\d{2}-\d{2}",
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            d = parse_date(match.group())
            if d:
                return d
    return None


# ---------------------------------------------------------------------------
# Scrapers — one per source
# ---------------------------------------------------------------------------

def scrape_nac():
    """Scrape the National Arts Council funding overview page."""
    print("[NAC] Scraping nac.org.za ...")
    results = []
    soup = fetch("https://www.nac.org.za/funding-news/funding-overview/")
    if not soup:
        return results

    # The NAC funding overview page lists funding calls in article / post blocks
    for article in soup.select("article, .post, .entry, .funding-item"):
        title_el = article.select_one("h2, h3, h4, .entry-title, a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue

        link = title_el.get("href") or ""
        if title_el.name != "a":
            a = title_el.find("a")
            if a:
                link = a.get("href", "")
        if link and not link.startswith("http"):
            link = "https://www.nac.org.za" + link

        body = article.get_text(" ", strip=True)
        deadline = extract_dates_from_text(body)

        opp = {
            "id": make_id(title, "NAC"),
            "title": title,
            "funder": "National Arts Council (NAC)",
            "type": "grant",
            "status": "open",
            "deadline": deadline or "Rolling",
            "amount": "Varies",
            "description": body[:300].strip(),
            "eligibility": "South African arts practitioners and organisations",
            "focus_areas": [],
            "how_to_apply": link or "https://www.nac.org.za/funding-news/funding-overview/",
            "url": link or "https://www.nac.org.za/funding-news/funding-overview/",
            "date_added": date.today().isoformat(),
        }
        results.append(opp)

    print(f"  Found {len(results)} items from NAC")
    return results


def scrape_dsac_tenders():
    """Scrape DSAC tenders page."""
    print("[DSAC] Scraping dsac.gov.za tenders ...")
    results = []
    soup = fetch("https://www.dsac.gov.za/qt-tenders")
    if not soup:
        return results

    for row in soup.select("tr, .view-content .views-row, article"):
        text = row.get_text(" ", strip=True)
        if len(text) < 20:
            continue

        # Try to find a link
        a = row.find("a")
        link = ""
        title = text[:120]
        if a:
            link = a.get("href", "")
            title = a.get_text(strip=True) or title
            if link and not link.startswith("http"):
                link = "https://www.dsac.gov.za" + link

        deadline = extract_dates_from_text(text)

        opp = {
            "id": make_id(title, "DSAC"),
            "title": title[:200],
            "funder": "Department of Sport, Arts and Culture",
            "type": "tender",
            "status": "open",
            "deadline": deadline or "Varies per tender",
            "amount": "Varies per tender",
            "description": text[:300].strip(),
            "eligibility": "Registered service providers",
            "focus_areas": [],
            "how_to_apply": link or "https://www.dsac.gov.za/qt-tenders",
            "url": link or "https://www.dsac.gov.za/qt-tenders",
            "date_added": date.today().isoformat(),
        }
        results.append(opp)

    print(f"  Found {len(results)} items from DSAC tenders")
    return results


def scrape_nlc():
    """Scrape the NLC arts and culture page."""
    print("[NLC] Scraping nlcsa.org.za ...")
    results = []
    soup = fetch("https://www.nlcsa.org.za/arts-and-culture/")
    if not soup:
        return results

    # NLC page is mostly informational; extract what we can
    main = soup.select_one("main, .entry-content, #content, article")
    if main:
        text = main.get_text(" ", strip=True)
        desc = text[:400].strip() if text else ""
        results.append({
            "id": make_id("NLC Arts and Culture Sector", "NLC"),
            "title": "National Lotteries Commission - Arts and Culture Sector",
            "funder": "National Lotteries Commission (NLC)",
            "type": "grant",
            "status": "open",
            "deadline": "Rolling",
            "amount": "Varies",
            "description": desc or (
                "Funds the development of the arts and the preservation of "
                "South African culture and national heritage."
            ),
            "eligibility": "South African registered non-profit organisations",
            "focus_areas": [
                "Arts development",
                "Cultural preservation",
                "National heritage",
            ],
            "how_to_apply": "https://www.nlcsa.org.za/arts-and-culture/",
            "url": "https://www.nlcsa.org.za/arts-and-culture/",
            "date_added": date.today().isoformat(),
        })

    print(f"  Found {len(results)} items from NLC")
    return results


def scrape_goethe():
    """Scrape Goethe-Institut SA cultural funding page."""
    print("[Goethe] Scraping goethe.de ...")
    results = []
    soup = fetch("https://www.goethe.de/ins/za/en/kul/kul.html")
    if not soup:
        return results

    for section in soup.select("article, .teaser, .accordion-item, section"):
        title_el = section.select_one("h2, h3, h4, .teaser-title")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        body = section.get_text(" ", strip=True)
        a = section.find("a", href=True)
        link = ""
        if a:
            link = a["href"]
            if link and not link.startswith("http"):
                link = "https://www.goethe.de" + link

        deadline = extract_dates_from_text(body)

        results.append({
            "id": make_id(title, "Goethe"),
            "title": title[:200],
            "funder": "Goethe-Institut South Africa",
            "type": "grant",
            "status": "open",
            "deadline": deadline or "Rolling",
            "amount": "Varies",
            "description": body[:300].strip(),
            "eligibility": "Artists in South Africa and the region",
            "focus_areas": ["International collaboration"],
            "how_to_apply": link or "https://www.goethe.de/ins/za/en/kul/kul.html",
            "url": link or "https://www.goethe.de/ins/za/en/kul/kul.html",
            "date_added": date.today().isoformat(),
        })

    print(f"  Found {len(results)} items from Goethe-Institut")
    return results


def scrape_vansa():
    """Scrape VANSA arts opportunities / funding page."""
    print("[VANSA] Scraping vansa.co.za ...")
    results = []
    soup = fetch("https://vansa.co.za/arts-opportunities/funding/")
    if not soup:
        return results

    for item in soup.select("article, .post, .opportunity-item, .entry"):
        title_el = item.select_one("h2, h3, h4, .entry-title, a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title:
            continue

        link = ""
        a = item.find("a", href=True)
        if a:
            link = a["href"]

        body = item.get_text(" ", strip=True)
        deadline = extract_dates_from_text(body)

        results.append({
            "id": make_id(title, "VANSA"),
            "title": title[:200],
            "funder": "VANSA / Various",
            "type": "grant",
            "status": "open",
            "deadline": deadline or "Varies",
            "amount": "Varies",
            "description": body[:300].strip(),
            "eligibility": "South African arts practitioners",
            "focus_areas": [],
            "how_to_apply": link or "https://vansa.co.za/arts-opportunities/funding/",
            "url": link or "https://vansa.co.za/arts-opportunities/funding/",
            "date_added": date.today().isoformat(),
        })

    print(f"  Found {len(results)} items from VANSA")
    return results


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def load_existing():
    """Load the current funding.json, if it exists."""
    if FUNDING_FILE.exists():
        with open(FUNDING_FILE) as f:
            return json.load(f)
    return {"last_updated": None, "sources": [], "opportunities": []}


def merge_opportunities(existing, scraped):
    """
    Merge scraped opportunities into existing ones.
    - Manually curated entries (those already in the file) are kept as-is.
    - Scraped entries are added or updated by id.
    """
    by_id = {o["id"]: o for o in existing}

    for opp in scraped:
        oid = opp["id"]
        if oid not in by_id:
            by_id[oid] = opp
        else:
            # Update scraped fields but keep manual overrides for description, etc.
            old = by_id[oid]
            # Only overwrite if the old entry was also scraped (date_added will match pattern)
            if old.get("date_added") != opp.get("date_added"):
                # Keep the existing curated entry
                continue
            by_id[oid] = opp

    return list(by_id.values())


def update_statuses(opportunities):
    """Mark opportunities with past deadlines as closed."""
    today = date.today()
    for opp in opportunities:
        dl = opp.get("deadline", "")
        if dl and dl not in ("Rolling", "Varies", "Varies per tender"):
            try:
                dl_date = datetime.strptime(dl, "%Y-%m-%d").date()
                if dl_date < today:
                    opp["status"] = "closed"
            except ValueError:
                pass
    return opportunities


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"=== SA Arts Funding Scraper - {date.today().isoformat()} ===\n")

    scraped = []
    scrapers = [
        scrape_nac,
        scrape_dsac_tenders,
        scrape_nlc,
        scrape_goethe,
        scrape_vansa,
    ]

    for scraper_fn in scrapers:
        try:
            scraped.extend(scraper_fn())
        except Exception as exc:
            print(f"  [ERROR] {scraper_fn.__name__} failed: {exc}")
        print()

    print(f"Total scraped: {len(scraped)} opportunities\n")

    data = load_existing()
    existing_opps = data.get("opportunities", [])
    merged = merge_opportunities(existing_opps, scraped)
    merged = update_statuses(merged)

    data["opportunities"] = merged
    data["last_updated"] = date.today().isoformat()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(FUNDING_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Written {len(merged)} opportunities to {FUNDING_FILE}")
    print("Done.")


if __name__ == "__main__":
    main()
