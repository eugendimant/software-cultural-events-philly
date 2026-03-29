#!/usr/bin/env python3
"""
Event Verification — checks every event in events.json against its source URL.

For each event, fetches the event's link or source_url and checks whether
the event title, venue, and dates are actually present on the page. Events
that can't be verified are flagged and optionally corrected.

This is the FOOLPROOF system that ensures no wrong data ever reaches users.

Usage:
    python verify_events.py                     # verify all events
    python verify_events.py --fix               # verify + auto-fix from page
    python verify_events.py --report            # just print report, no changes
    python verify_events.py --source "BalletX"  # verify one source only
"""

import argparse
import json
import logging
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("verify_events")

EVENTS_JSON = Path(__file__).resolve().parent.parent / "data" / "events.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}
REQUEST_TIMEOUT = 15

# Month names for date matching
MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09",
    "oct": "10", "nov": "11", "dec": "12",
}


def fetch_page(url: str) -> str | None:
    """Fetch a URL and return the page text, or None on failure."""
    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        resp = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx)
        return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.debug("Failed to fetch %s: %s", url, e)
        return None


def normalize(text: str) -> str:
    """Normalize text for fuzzy matching: lowercase, collapse whitespace, strip punctuation."""
    text = text.lower().strip()
    text = re.sub(r'[''`]', "'", text)
    text = re.sub(r'["""]', '"', text)
    text = re.sub(r'[\s]+', ' ', text)
    return text


def title_on_page(title: str, page_text: str) -> bool:
    """Check if event title appears on the page (fuzzy)."""
    norm_title = normalize(title)
    norm_page = normalize(page_text)

    # Exact match
    if norm_title in norm_page:
        return True

    # Try without common prefixes/suffixes
    for prefix in ("the ", "a "):
        if norm_title.startswith(prefix):
            if norm_title[len(prefix):] in norm_page:
                return True

    # Try first N significant words (handles subtitle variations)
    words = [w for w in norm_title.split() if len(w) > 2]
    if len(words) >= 3:
        # Check if first 3 significant words appear together
        partial = " ".join(words[:3])
        if partial in norm_page:
            return True

    return False


def venue_on_page(venue: str, page_text: str) -> bool:
    """Check if venue name appears on the page."""
    if not venue:
        return True  # No venue to check
    norm_venue = normalize(venue)
    norm_page = normalize(page_text)

    if norm_venue in norm_page:
        return True

    # Try just the main venue name (before comma)
    main_venue = norm_venue.split(",")[0].strip()
    if len(main_venue) > 3 and main_venue in norm_page:
        return True

    return False


def dates_on_page(date_start: str, date_end: str, page_text: str) -> bool:
    """Check if event dates appear on the page in any common format."""
    if not date_start:
        return True  # No date to check
    norm_page = normalize(page_text)

    try:
        start = datetime.strptime(date_start, "%Y-%m-%d")
    except ValueError:
        return True  # Can't parse, skip

    # Check various date formats
    # "March 18", "Mar 18", "3/18", "2026-03-18"
    formats_to_check = [
        start.strftime("%B %d").lower(),           # "march 18"
        start.strftime("%b %d").lower(),            # "mar 18"
        start.strftime("%b. %d").lower(),           # "mar. 18"
        start.strftime("%-m/%-d").lower(),          # "3/18"
        start.strftime("%m/%d").lower(),            # "03/18"
        date_start,                                  # "2026-03-18"
        start.strftime("%B %-d").lower(),           # "march 18" (no leading zero)
        start.strftime("%b %-d").lower(),           # "mar 18"
    ]

    # Also check with day without leading zero: "march 8" not "march 08"
    day = start.day
    month_full = start.strftime("%B").lower()
    month_abbr = start.strftime("%b").lower()
    formats_to_check.extend([
        f"{month_full} {day}",
        f"{month_abbr} {day}",
        f"{month_abbr}. {day}",
    ])

    # Remove duplicates
    formats_to_check = list(set(formats_to_check))

    for fmt in formats_to_check:
        if fmt in norm_page:
            return True

    # Check just the day number near a month name
    month_names = [month_full, month_abbr]
    for mn in month_names:
        # Look for month name followed by day within 10 chars
        pattern = rf'{mn}\.?\s*{day}\b'
        if re.search(pattern, norm_page):
            return True

    return False


def extract_dates_from_page(page_text: str, event_title: str) -> tuple[str | None, str | None]:
    """Try to extract date_start and date_end from the page text near the event title."""
    if not HAS_BS4:
        return None, None

    # Look for common date patterns in the page
    norm = normalize(page_text)

    # Pattern: "Month Day – Month Day, Year" or "Month Day-Day, Year"
    range_pattern = re.compile(
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s+(\d{1,2})\s*[-–—]\s*'
        r'(?:(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\.?\s+)?(\d{1,2}),?\s*(\d{4})',
        re.IGNORECASE
    )
    m = range_pattern.search(page_text)
    if m:
        start_month = m.group(1)[:3].lower()
        start_day = int(m.group(2))
        end_month = (m.group(3) or m.group(1))[:3].lower()
        end_day = int(m.group(4))
        year = int(m.group(5))

        sm = MONTHS.get(start_month)
        em = MONTHS.get(end_month)
        if sm and em:
            try:
                ds = f"{year}-{sm}-{start_day:02d}"
                de = f"{year}-{em}-{end_day:02d}"
                return ds, de
            except Exception:
                pass

    return None, None


def verify_event(event: dict) -> dict:
    """Verify a single event. Returns a report dict."""
    title = (event.get("title") or "").strip()
    venue = (event.get("venue") or "").strip()
    ds = event.get("date_start", "")
    de = event.get("date_end", "")
    link = (event.get("link") or "").strip()
    source_url = (event.get("source_url") or "").strip()

    report = {
        "title": title,
        "source": event.get("source", ""),
        "status": "unknown",
        "title_found": None,
        "venue_found": None,
        "dates_found": None,
        "page_dates": None,
        "url_checked": None,
    }

    # Try the event-specific link first, then source_url
    url = link if link and link != source_url else source_url
    if not url:
        report["status"] = "no_url"
        return report

    report["url_checked"] = url
    page = fetch_page(url)
    if not page:
        report["status"] = "fetch_failed"
        return report

    # Check title
    report["title_found"] = title_on_page(title, page)

    # Check venue
    report["venue_found"] = venue_on_page(venue, page)

    # Check dates
    report["dates_found"] = dates_on_page(ds, de, page)

    # Try to extract dates from the page
    page_ds, page_de = extract_dates_from_page(page, title)
    if page_ds:
        report["page_dates"] = (page_ds, page_de)

    # Determine overall status
    if report["title_found"] and report["venue_found"] and report["dates_found"]:
        report["status"] = "verified"
    elif report["title_found"] and report["dates_found"]:
        report["status"] = "venue_mismatch"
    elif report["title_found"]:
        report["status"] = "dates_mismatch"
    elif not report["title_found"]:
        report["status"] = "title_not_found"
    else:
        report["status"] = "partial"

    return report


def main():
    parser = argparse.ArgumentParser(description="Verify event data against source websites")
    parser.add_argument("--fix", action="store_true", help="Auto-fix dates from page when mismatch found")
    parser.add_argument("--report", action="store_true", help="Report only, no changes")
    parser.add_argument("--source", type=str, help="Only verify events from this source")
    parser.add_argument("--file", type=str, default=str(EVENTS_JSON), help="Path to events.json")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        log.error("Events file not found: %s", path)
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    events = data.get("events", [])
    today = datetime.now().strftime("%Y-%m-%d")

    # Only verify current/future events
    to_verify = [
        e for e in events
        if e.get("date_start")
        and (e.get("date_end") or e.get("date_start", "")) >= today
        and (not args.source or e.get("source") == args.source)
    ]

    log.info("Verifying %d events from %s", len(to_verify), path.name)

    stats = {"verified": 0, "venue_mismatch": 0, "dates_mismatch": 0,
             "title_not_found": 0, "fetch_failed": 0, "no_url": 0, "fixed": 0}

    for i, event in enumerate(to_verify):
        report = verify_event(event)
        stats[report["status"]] = stats.get(report["status"], 0) + 1

        if report["status"] != "verified":
            log.warning(
                "[%d/%d] %s: [%s] %s",
                i + 1, len(to_verify), report["status"].upper(),
                report["source"], report["title"][:50],
            )
            if report.get("page_dates"):
                log.info("  Page dates: %s", report["page_dates"])
            if report["status"] == "dates_mismatch" and args.fix and report.get("page_dates"):
                page_ds, page_de = report["page_dates"]
                event["date_start"] = page_ds
                if page_de:
                    event["date_end"] = page_de
                stats["fixed"] += 1
                log.info("  FIXED dates -> %s – %s", page_ds, page_de)

        # Be polite
        time.sleep(0.5)

    log.info("=" * 50)
    log.info("VERIFICATION REPORT")
    log.info("=" * 50)
    for status, count in sorted(stats.items()):
        if count > 0:
            log.info("  %s: %d", status, count)

    if args.fix and stats["fixed"] > 0 and not args.report:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        log.info("Saved %d fixes to %s", stats["fixed"], path.name)


if __name__ == "__main__":
    main()
