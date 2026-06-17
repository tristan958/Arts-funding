#!/usr/bin/env python3
"""
SA Arts Funding Scraper

Discovers funding opportunities from key South African arts funding sources and
merges them into data/funding.json. Designed to run weekly via GitHub Actions
(or manually).

Design notes
------------
The dashboard is curated-first: hand-written entries in funding.json are the
source of truth and are never overwritten or removed by this script. The scraper
only *adds* auto-discovered entries, and every auto entry is tagged ``auto:true``.

Web pages on the monitored sites do not expose a clean, machine-readable list of
opportunities, so naive scraping picks up navigation and teaser noise. To avoid
polluting the dashboard, candidates must pass strict quality gates
(``looks_like_opportunity``) before being added — in practice they must mention a
funding keyword *and* carry a parseable deadline date. Previous auto entries are
discarded on every run and replaced with the current findings, so junk can never
accumulate.
"""

import json
import hashlib
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin

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

# A candidate must mention at least one of these to be considered.
FUNDING_KEYWORDS = (
    "grant", "fund", "bursary", "scholarship", "tender", "call for",
    "apply", "application", "deadline", "award", "residency", "fellowship",
    "open call", "proposal", "submission",
)

# Obvious non-opportunity titles to reject outright (case-insensitive substring).
TITLE_BLOCKLIST = (
    "read more", "learn more", "home", "about", "contact", "newsletter",
    "privacy", "cookie", "sitemap", "menu", "search", "subscribe", "login",
    "have been announced", "now closed", "jury", "gallery", "funded projects",
    "worldwide", "overview",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch(url):
    """GET a URL and return a (BeautifulSoup, base_url) tuple, or (None, url)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser"), resp.url
    except requests.RequestException as exc:
        print(f"  [WARN] Failed to fetch {url}: {exc}")
        return None, url


def make_id(title, funder):
    """Deterministic short id from title + funder."""
    raw = f"{funder}:{title}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def absolute_url(href, base):
    """Resolve a possibly-relative href against the page's base URL."""
    if not href:
        return base
    return urljoin(base, href.strip())


def parse_date(text):
    """Try to parse a single date string. Returns YYYY-MM-DD or None."""
    for fmt in ("%d %B %Y", "%B %d, %Y", "%B %d %Y", "%Y-%m-%d", "%d %b %Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def extract_date(text):
    """Search for the first date-like pattern in a block of text."""
    patterns = (
        r"\d{1,2}\s+[A-Za-z]+\s+\d{4}",
        r"[A-Za-z]+\s+\d{1,2},?\s+\d{4}",
        r"\d{4}-\d{2}-\d{2}",
        r"\d{1,2}/\d{1,2}/\d{4}",
    )
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            parsed = parse_date(match.group())
            if parsed:
                return parsed
    return None


def has_real_deadline(deadline):
    """True only for a concrete YYYY-MM-DD date (not 'Rolling'/'Varies'/empty)."""
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", deadline or ""))


def looks_like_opportunity(opp):
    """Quality gate: keep only candidates that read like a real opportunity."""
    title = opp["title"]
    if not (8 <= len(title) <= 160):
        return False
    if any(bad in title.lower() for bad in TITLE_BLOCKLIST):
        return False
    haystack = f"{title} {opp['description']}".lower()
    if not any(kw in haystack for kw in FUNDING_KEYWORDS):
        return False
    # A concrete, parseable deadline is the strongest signal that a candidate is a
    # real, time-bound call rather than a page heading or teaser.
    return has_real_deadline(opp["deadline"])


def build_opp(title, funder, body, link, *, type_="grant",
              eligibility="", focus_areas=None, deadline=None):
    """Assemble a normalised opportunity dict for an auto-discovered candidate."""
    return {
        "id": make_id(title, funder),
        "title": title[:200].strip(),
        "funder": funder,
        "type": type_,
        "status": "open",
        "deadline": deadline or "Rolling",
        "amount": "Varies",
        "description": " ".join(body.split())[:300].strip(),
        "eligibility": eligibility,
        "focus_areas": focus_areas or [],
        "how_to_apply": link,
        "url": link,
        "date_added": date.today().isoformat(),
        "auto": True,
    }


# ---------------------------------------------------------------------------
# Scrapers — one per source. Each yields candidate opportunities; quality
# gating is applied centrally in collect().
# ---------------------------------------------------------------------------

def _scrape_listing(url, funder, *, type_="grant", eligibility="",
                    focus_areas=None, selectors="article, .post, .entry, .views-row, .teaser"):
    """Generic listing scraper shared by most sources."""
    soup, base = fetch(url)
    if not soup:
        return []

    results = []
    seen_titles = set()
    for block in soup.select(selectors):
        title_el = block.select_one("h2, h3, h4, .entry-title, .teaser-title, a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title or title.lower() in seen_titles:
            continue
        seen_titles.add(title.lower())

        anchor = title_el if title_el.name == "a" else block.find("a", href=True)
        link = absolute_url(anchor.get("href") if anchor else "", base)

        body = block.get_text(" ", strip=True)
        results.append(build_opp(
            title, funder, body, link or url,
            type_=type_, eligibility=eligibility,
            focus_areas=focus_areas, deadline=extract_date(body),
        ))
    return results


def scrape_nac():
    print("[NAC] Scraping nac.org.za ...")
    return _scrape_listing(
        "https://www.nac.org.za/funding-news/funding-overview/",
        "National Arts Council (NAC)",
        eligibility="South African arts practitioners and organisations",
    )


def scrape_dsac_tenders():
    print("[DSAC] Scraping dsac.gov.za tenders ...")
    return _scrape_listing(
        "https://www.dsac.gov.za/qt-tenders",
        "Department of Sport, Arts and Culture",
        type_="tender",
        eligibility="Registered service providers",
        selectors="tr, .views-row, article",
    )


def scrape_goethe():
    print("[Goethe] Scraping goethe.de ...")
    return _scrape_listing(
        "https://www.goethe.de/ins/za/en/kul/kul.html",
        "Goethe-Institut South Africa",
        eligibility="Artists in South Africa and the region",
        focus_areas=["International collaboration"],
        selectors="article, .teaser, .accordion-item",
    )


def scrape_vansa():
    print("[VANSA] Scraping vansa.co.za ...")
    return _scrape_listing(
        "https://vansa.co.za/arts-opportunities/funding/",
        "VANSA / Various",
        eligibility="South African arts practitioners",
        selectors="article, .post, .opportunity-item, .entry",
    )


SCRAPERS = (scrape_nac, scrape_dsac_tenders, scrape_goethe, scrape_vansa)


# ---------------------------------------------------------------------------
# Collect, merge, status
# ---------------------------------------------------------------------------

def collect():
    """Run all scrapers concurrently and return gated, de-duplicated candidates."""
    raw = []
    with ThreadPoolExecutor(max_workers=len(SCRAPERS)) as pool:
        for fn, items in zip(SCRAPERS, pool.map(_safe_run, SCRAPERS)):
            print(f"  {fn.__name__}: {len(items)} candidate(s)")
            raw.extend(items)

    gated, seen = [], set()
    for opp in raw:
        if opp["id"] in seen or not looks_like_opportunity(opp):
            continue
        seen.add(opp["id"])
        gated.append(opp)
    print(f"\n{len(gated)} candidate(s) passed quality gates (from {len(raw)} raw).")
    return gated


def _safe_run(fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - never let one source kill the run
        print(f"  [ERROR] {fn.__name__} failed: {exc}")
        return []


def load_existing():
    if FUNDING_FILE.exists():
        with open(FUNDING_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": None, "sources": [], "opportunities": []}


def merge(existing, scraped):
    """
    Curated entries (no ``auto`` flag) are kept verbatim. All previous auto
    entries are dropped and replaced by the current scrape, so stale or junk
    auto entries never accumulate. Auto entries that collide with a curated id
    are skipped in favour of the curated version.
    """
    curated = [o for o in existing if not o.get("auto")]
    curated_ids = {o["id"] for o in curated}
    fresh_auto = [o for o in scraped if o["id"] not in curated_ids]
    return curated + fresh_auto


def update_statuses(opportunities):
    """Mark opportunities with past deadlines as closed (reliable automation)."""
    today = date.today()
    for opp in opportunities:
        dl = opp.get("deadline", "")
        if has_real_deadline(dl):
            dl_date = datetime.strptime(dl, "%Y-%m-%d").date()
            opp["status"] = "closed" if dl_date < today else "open"
    return opportunities


def main():
    print(f"=== SA Arts Funding Scraper - {date.today().isoformat()} ===\n")

    scraped = collect()

    data = load_existing()
    merged = update_statuses(merge(data.get("opportunities", []), scraped))

    data["opportunities"] = merged
    data["last_updated"] = date.today().isoformat()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(FUNDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    auto = sum(1 for o in merged if o.get("auto"))
    print(f"\nWritten {len(merged)} opportunities "
          f"({len(merged) - auto} curated, {auto} auto) to {FUNDING_FILE}")
    print("Done.")


if __name__ == "__main__":
    sys.exit(main())
