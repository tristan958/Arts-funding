#!/usr/bin/env python3
"""
fetch_tenders.py — robust arts/culture tender discovery from the SA eTenders OCDS API.

The South African National Treasury publishes all government tenders as Open
Contracting Data Standard (OCDS) releases via a JSON REST API:

    Swagger:  https://ocds-api.etenders.gov.za/swagger/index.html
    Portal:   https://data.etenders.gov.za/

This is far more reliable than scraping the JavaScript eTenders site: it is
structured, dated, and licensed CC-BY 4.0. This script pulls OCDS releases over
a date window, keyword-filters them down to arts / culture / heritage relevance,
and prints candidate entries already shaped like data/funding.json `opportunities`.

It is meant to be run by the weekly **discover-funding** routine (which has Full
network access). It uses only the Python standard library — no pip install.

Usage:
    python3 tools/discovery/fetch_tenders.py                 # next 120 days
    python3 tools/discovery/fetch_tenders.py --days 90
    python3 tools/discovery/fetch_tenders.py --date-from 2026-06-01 --date-to 2026-09-30

Output: a JSON array of candidate entries on stdout. Diagnostics go to stderr.
The routine should then de-duplicate (by id/url/funder+title), re-confirm each
closing date, and merge the genuine ones into data/funding.json.

NOTE: the OCDS host blocks generic bot user-agents, so a browser-like UA is sent.
Endpoint/param names follow the documented eTenders OCDS API; if the API changes,
check the Swagger above and adjust API_BASE / the release-parsing below.
"""

import argparse
import datetime as dt
import json
import re
import sys
import urllib.error
import urllib.request

API_BASE = "https://ocds-api.etenders.gov.za/api/OCDSReleases"
PORTAL = "https://www.etenders.gov.za/Home/opportunities?id=1"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# --- Arts/culture relevance --------------------------------------------------
# Word-boundary patterns so "agriculture"/"horticulture"/"aquaculture" never
# match "culture". Keep this list curated; the routine may extend it.
INCLUDE = re.compile(
    r"\b("
    r"arts?|artist\w*|artwork|"
    r"culture|cultural|"
    r"heritage|museum\w*|galler(?:y|ies)|"
    r"theatre|theater|performing\s+arts|visual\s+arts?|public\s+art|"
    r"creative\s+(?:industr\w+|economy|sector|arts)|"
    r"craft\w*|sculptur\w*|exhibition\w*|monument\w*|"
    r"archive\w*|librar(?:y|ies)|"
    r"music\w*|orchestra|choir|dance|choreograph\w*|"
    r"film|cinema|festival|"
    r"sport,?\s+arts\s+and\s+culture|\bdsac\b"
    r")\b",
    re.IGNORECASE,
)
# Hard excludes — drop obvious non-arts tenders even if a token slips through.
EXCLUDE = re.compile(
    r"\b(agricultur\w*|horticultur\w*|aquacultur\w*|viticultur\w*|"
    r"permacultur\w*|sport\s+field|stadium\s+turf)\b",
    re.IGNORECASE,
)

# Map a matched keyword to a dashboard discipline (best-effort; default below).
DISCIPLINE_HINTS = [
    (re.compile(r"heritage|museum|monument|archive", re.I), "heritage"),
    (re.compile(r"theatre|theater|performing\s+arts|dance|choir|orchestra", re.I), "performing-arts"),
    (re.compile(r"music", re.I), "music"),
    (re.compile(r"film|cinema|video", re.I), "film-screen"),
    (re.compile(r"public\s+art|sculptur|monument", re.I), "public-art"),
    (re.compile(r"visual\s+arts?|galler|exhibition|artwork", re.I), "visual-art"),
    (re.compile(r"craft", re.I), "craft"),
]

PROVINCE_HINTS = [
    (re.compile(r"kwazulu|kzn", re.I), "kwazulu-natal"),
    (re.compile(r"western\s+cape", re.I), "western-cape"),
    (re.compile(r"gauteng", re.I), "gauteng"),
]


def today():
    return dt.date.today()


def slugify(s, maxlen=48):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:maxlen].strip("-") or "tender"


def iso_date(s):
    """Pull a YYYY-MM-DD out of an OCDS datetime string, or None."""
    if not s:
        return None
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(s))
    return m.group(1) if m else None


def fetch_page(date_from, date_to, page, page_size):
    url = (f"{API_BASE}?PageNumber={page}&PageSize={page_size}"
           f"&dateFrom={date_from}&dateTo={date_to}")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def relevant(text):
    return bool(INCLUDE.search(text)) and not EXCLUDE.search(text)


def discipline_for(text):
    for pat, disc in DISCIPLINE_HINTS:
        if pat.search(text):
            return disc
    return "all-disciplines"


def region_for(text):
    for pat, reg in PROVINCE_HINTS:
        if pat.search(text):
            return reg
    return "national"


def to_entry(release):
    """Map one OCDS release to a funding.json candidate, or None if not usable."""
    tender = release.get("tender") or {}
    title = (tender.get("title") or "").strip()
    desc = (tender.get("description") or "").strip()
    buyer = ((release.get("buyer") or {}).get("name")
             or (tender.get("procuringEntity") or {}).get("name") or "").strip()
    haystack = " ".join([title, desc, buyer])
    if not title or not relevant(haystack):
        return None

    deadline = iso_date((tender.get("tenderPeriod") or {}).get("endDate"))
    if not deadline:
        return None
    if deadline < today().isoformat():        # already closed — skip
        return None

    value = tender.get("value") or {}
    if isinstance(value.get("amount"), (int, float)) and value.get("amount"):
        cur = value.get("currency") or "ZAR"
        amount = f"{cur} {value['amount']:,.0f}"
    else:
        amount = "Varies per tender"

    docs = tender.get("documents") or []
    doc_url = next((d.get("url") for d in docs if d.get("url")), None)

    bid_id = tender.get("id") or release.get("ocid") or release.get("id") or ""
    entry_id = f"tender-{slugify(buyer or 'gov')}-{slugify(bid_id, 18)}"

    short_desc = re.sub(r"\s+", " ", desc) or f"Government tender issued by {buyer or 'a public body'}."
    if len(short_desc) > 320:
        short_desc = short_desc[:317].rstrip() + "…"

    return {
        "id": entry_id,
        "title": title,
        "funder": buyer or "South African Government (eTenders)",
        "type": "tender",
        "status": "open",
        "deadline": deadline,
        "amount": amount,
        "description": short_desc,
        "eligibility": "Registered service providers / bidders meeting the tender's requirements (CSD registration typically required).",
        "focus_areas": ["Government tender", "Arts & culture", "Service provision"],
        "disciplines": [discipline_for(haystack)],
        "purpose": ["procurement"],
        "eligibility_type": ["organisation"],
        "org_focus": False,
        "tags": ["sa-only"],
        "audiences": [],
        "region": region_for(haystack),
        "how_to_apply": "Download the tender documents and submit a bid via the eTenders portal "
                        f"({PORTAL}). " + (f"Documents: {doc_url}" if doc_url else ""),
        "url": doc_url or PORTAL,
        "date_added": today().isoformat(),
        "_source": "etenders-ocds",   # provenance hint for the routine; strip before saving
    }


def main():
    ap = argparse.ArgumentParser(description="Discover arts/culture tenders from the eTenders OCDS API.")
    ap.add_argument("--date-from", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--date-to", help="YYYY-MM-DD (default: today + --days)")
    ap.add_argument("--days", type=int, default=120, help="window length if --date-to omitted (default 120)")
    ap.add_argument("--page-size", type=int, default=50)
    ap.add_argument("--max-pages", type=int, default=20, help="safety cap on pagination")
    args = ap.parse_args()

    date_from = args.date_from or today().isoformat()
    date_to = args.date_to or (today() + dt.timedelta(days=args.days)).isoformat()

    out, seen, scanned = [], set(), 0
    for page in range(1, args.max_pages + 1):
        try:
            data = fetch_page(date_from, date_to, page, args.page_size)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
            print(f"[fetch_tenders] page {page} failed: {e}", file=sys.stderr)
            break
        releases = data.get("releases") or data.get("data") or []
        if not releases:
            break
        scanned += len(releases)
        for rel in releases:
            entry = to_entry(rel)
            if entry and entry["id"] not in seen:
                seen.add(entry["id"])
                out.append(entry)
        if len(releases) < args.page_size:
            break   # last page

    print(f"[fetch_tenders] scanned {scanned} releases {date_from}..{date_to}; "
          f"{len(out)} arts/culture matches.", file=sys.stderr)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
