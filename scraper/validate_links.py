#!/usr/bin/env python3
"""
Link Validator — checks all ticket URLs in events.json and fixes broken ones.

Run this script after scraping to ensure no broken links are served.
It performs HTTP HEAD requests on every ticket link and:
  - Replaces 404/410 links with the event's source_url (venue listing page)
  - Follows redirects and updates the link to the final destination
  - Logs all fixes for auditing

Usage:
    python validate_links.py                    # validate + fix
    python validate_links.py --dry-run          # report only, no changes
    python validate_links.py --iterations 3     # run multiple passes

Designed to be called from CI, cron, or the scraper pipeline.
"""

import argparse
import json
import logging
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("validate_links")

EVENTS_JSON = Path(__file__).resolve().parent.parent / "data" / "events.json"

# Timeout per request (seconds)
REQUEST_TIMEOUT = 12

# Status codes that mean "page gone, replace the link"
BROKEN_CODES = {404, 410, 403, 500, 502, 503}

# User-Agent to avoid bot blocks
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}


def _ssl_context():
    ctx = ssl.create_default_context()
    return ctx


def check_url(url: str) -> tuple[int, str]:
    """Check a URL via HEAD (fallback to GET). Returns (status_code, final_url).

    Returns (0, url) on network/timeout errors (ambiguous — don't replace).
    Returns (status_code, final_url) on HTTP responses.
    """
    ctx = _ssl_context()
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx)
            return resp.getcode(), resp.url
        except urllib.error.HTTPError as e:
            return e.code, url
        except Exception:
            if method == "GET":
                return 0, url  # network error — ambiguous
            continue  # try GET
    return 0, url


def validate_and_fix(events: list[dict], dry_run: bool = False) -> dict:
    """Validate all event links. Returns stats dict."""
    stats = {"checked": 0, "ok": 0, "fixed": 0, "ambiguous": 0, "no_link": 0}
    total = len(events)

    for i, event in enumerate(events):
        link = (event.get("link") or "").strip()
        source_url = (event.get("source_url") or "").strip()
        title = (event.get("title") or "")[:60]

        if not link or link == "#":
            stats["no_link"] += 1
            continue

        stats["checked"] += 1
        status, final_url = check_url(link)

        if status == 0:
            # Network error — can't determine, skip
            stats["ambiguous"] += 1
            log.debug("[%d/%d] AMBIGUOUS %s — %s", i + 1, total, title, link)
            continue

        if status in BROKEN_CODES:
            fallback = source_url or "#"
            log.warning(
                "[%d/%d] BROKEN (%d) %s — %s → %s",
                i + 1, total, status, title, link, fallback,
            )
            if not dry_run:
                event["link"] = fallback
            stats["fixed"] += 1
        elif final_url != link and final_url.startswith("http"):
            # Redirect — update to final URL
            log.info(
                "[%d/%d] REDIRECT %s — %s → %s",
                i + 1, total, title, link, final_url,
            )
            if not dry_run:
                event["link"] = final_url
            stats["fixed"] += 1
        else:
            stats["ok"] += 1
            log.debug("[%d/%d] OK %s", i + 1, total, title)

        # Be polite — small delay between requests
        time.sleep(0.3)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Validate event ticket links")
    parser.add_argument("--dry-run", action="store_true", help="Report only, no changes")
    parser.add_argument("--iterations", type=int, default=1, help="Number of validation passes")
    parser.add_argument("--file", type=str, default=str(EVENTS_JSON), help="Path to events.json")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        log.error("Events file not found: %s", path)
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    events = data.get("events", [])
    log.info("Loaded %d events from %s", len(events), path.name)

    for iteration in range(1, args.iterations + 1):
        log.info("=== Iteration %d/%d ===", iteration, args.iterations)
        stats = validate_and_fix(events, dry_run=args.dry_run)
        log.info(
            "Results: %d checked, %d ok, %d fixed, %d ambiguous, %d no-link",
            stats["checked"], stats["ok"], stats["fixed"],
            stats["ambiguous"], stats["no_link"],
        )
        if stats["fixed"] == 0:
            log.info("No fixes needed — stopping early.")
            break

    if not args.dry_run and any(
        validate_and_fix.__code__.co_varnames  # just checking we ran
    ):
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        log.info("Saved updated events to %s", path.name)
    elif args.dry_run:
        log.info("Dry run — no changes written.")


if __name__ == "__main__":
    main()
