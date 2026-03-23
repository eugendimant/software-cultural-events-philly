#!/usr/bin/env python3
"""
Philadelphia Cultural Events Scraper
Fetches events from verified Philadelphia cultural venues and outputs JSON.

Every event must have:
- title (from the page)
- source URL (traceable back to the original page)
- venue name

Events missing required fields are DISCARDED — no guessing, no defaults for titles/dates.
"""

import json
import re
import sys
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seed_events import get_seed_events

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# Scrape report — tracks what was found
REPORT = {"successes": [], "failures": [], "warnings": []}


def safe_get(url, timeout=20, retries=3):
    """Fetch URL with retry logic and exponential backoff. Returns Response or None."""
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.exceptions.HTTPError as e:
            # Don't retry client errors (4xx) except 429 (rate limited)
            if r.status_code == 429:
                wait = min(2 ** (attempt + 1), 30)
                print(f"  [WARN] Rate limited on {url}, retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            msg = f"Failed to fetch {url}: HTTP {r.status_code}"
            print(f"  [WARN] {msg}", file=sys.stderr)
            REPORT["failures"].append(msg)
            return None
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  [WARN] Attempt {attempt + 1} failed for {url}, retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                msg = f"Failed to fetch {url} after {retries} attempts: {e}"
                print(f"  [WARN] {msg}", file=sys.stderr)
                REPORT["failures"].append(msg)
                return None
    return None


def make_id(source_key, title, date_str=""):
    """Generate a deterministic ID from source + title + date."""
    raw = f"{source_key}|{title}|{date_str}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def parse_price(text):
    """Extract price string from text. Returns None if not found."""
    if not text:
        return None
    text = text.strip()
    low = text.lower()
    if low in ("free", "free!", "free admission", "no cover"):
        return "Free"
    m = re.search(r'\$[\d,.]+(?:\s*[-–—]\s*\$[\d,.]+)?', text)
    return m.group(0) if m else None


def clean_text(text):
    """Clean whitespace from extracted text."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()


def find_text(el, selectors):
    """Try multiple CSS selectors, return first match's text or empty string."""
    if not el:
        return ""
    for sel in selectors:
        found = el.select_one(sel)
        if found:
            t = clean_text(found.get_text())
            if t:
                return t
    return ""


def find_link(el, base_url):
    """Find first <a> link in element, resolve relative URLs."""
    if not el:
        return ""
    a = el.select_one("a[href]")
    if a and a.get("href"):
        href = a["href"]
        if href.startswith("http"):
            return href
        return urljoin(base_url, href)
    return ""


def validate_event(ev):
    """Return True only if event has required fields and looks like a real event."""
    title = (ev.get("title") or "").strip()
    if not title or len(title) < 3:
        return False
    if not ev.get("source"):
        return False
    if len(title) > 200:
        return False

    title_low = title.lower()

    # Exact-match junk titles
    skip_exact = {"subscribe", "sign up", "newsletter", "donate", "login",
                  "menu", "search", "home", "about", "contact", "gallery",
                  "facebook", "twitter", "instagram", "youtube",
                  "search form", "no results", "loading", "error"}
    if title_low in skip_exact:
        return False

    # Substring-match: reject titles containing these phrases (UI artifacts)
    skip_phrases = [
        "no upcoming events", "no events", "no results found",
        "search form", "sign up for", "subscribe to", "cookie",
        "privacy policy", "terms of service", "page not found",
        "404", "coming soon", "stay tuned", "under construction",
        "javascript", "enable javascript", "browser",
        "start date", "end date", "e.g.,", "placeholder",
        "select date", "filter by", "sort by", "show all",
        "load more", "view all", "see more", "read more",
        "click here", "learn more", "buy now",
    ]
    if any(phrase in title_low for phrase in skip_phrases):
        return False

    # Reject titles that are mostly non-alpha (form labels, codes, etc.)
    alpha_chars = sum(1 for c in title if c.isalpha())
    if alpha_chars < 3:
        return False

    # Reject if date_display looks like a form label / placeholder
    date_disp = (ev.get("date_display") or "").lower()
    if "start date" in date_disp or "e.g." in date_disp or "placeholder" in date_disp:
        ev["date_display"] = ""  # clear garbage display text

    return True


def parse_date_range(text):
    """Try to extract start/end dates from display text. Returns (start, end, display)."""
    if not text:
        return None, None, ""

    display = clean_text(text)
    today = datetime.now()
    year = today.year

    # Try patterns like "Mar 25 – Apr 6, 2026" or "March 25 - April 6"
    range_pattern = re.compile(
        r'(\w+)\s+(\d{1,2})\s*[-–—]\s*(\w+)\s+(\d{1,2}),?\s*(\d{4})?',
        re.IGNORECASE
    )
    m = range_pattern.search(text)
    if m:
        try:
            y = int(m.group(5)) if m.group(5) else year
            start = datetime.strptime(f"{m.group(1)} {m.group(2)} {y}", "%B %d %Y")
            end = datetime.strptime(f"{m.group(3)} {m.group(4)} {y}", "%B %d %Y")
            return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), display
        except ValueError:
            try:
                start = datetime.strptime(f"{m.group(1)} {m.group(2)} {y}", "%b %d %Y")
                end = datetime.strptime(f"{m.group(3)} {m.group(4)} {y}", "%b %d %Y")
                return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), display
            except ValueError:
                pass

    # Try single date like "March 25, 2026" or "Mar 25"
    single_pattern = re.compile(
        r'(\w+)\s+(\d{1,2}),?\s*(\d{4})?', re.IGNORECASE
    )
    m = single_pattern.search(text)
    if m:
        try:
            y = int(m.group(3)) if m.group(3) else year
            dt = datetime.strptime(f"{m.group(1)} {m.group(2)} {y}", "%B %d %Y")
            ds = dt.strftime("%Y-%m-%d")
            return ds, ds, display
        except ValueError:
            try:
                dt = datetime.strptime(f"{m.group(1)} {m.group(2)} {y}", "%b %d %Y")
                ds = dt.strftime("%Y-%m-%d")
                return ds, ds, display
            except ValueError:
                pass

    # ISO date
    iso = re.search(r'(\d{4}-\d{2}-\d{2})', text)
    if iso:
        return iso.group(1), iso.group(1), display

    return None, None, display


# ---------------------------------------------------------------------------
# SCRAPERS — one per source
# Each returns a list of event dicts. Every event MUST be traceable.
# ---------------------------------------------------------------------------

TITLE_SELECTORS = ["h2", "h3", "h4", "h5", ".title", "[class*='title']", "[class*='Title']",
                   ".event-name", "[class*='name']", "[class*='heading']", "a strong", "a b",
                   "[itemprop='name']", ".summary", "[class*='summary']"]
DATE_SELECTORS = ["time", "[datetime]", ".date", "[class*='date']", "[class*='Date']",
                  ".event-date", "[class*='when']", "[class*='When']", "[class*='schedule']",
                  "[itemprop='startDate']", "[class*='time']", "span.meta"]
VENUE_SELECTORS = [".venue", "[class*='venue']", "[class*='Venue']",
                   "[class*='location']", "[class*='Location']", ".place",
                   "[itemprop='location']", "[class*='where']"]
PRICE_SELECTORS = ["[class*='price']", "[class*='Price']", "[class*='cost']",
                   "[class*='Cost']", "[class*='ticket']", "[class*='Ticket']",
                   "[itemprop='price']", "[itemprop='lowPrice']"]
DESC_SELECTORS = ["[class*='description']", "[class*='Description']", "[class*='desc']",
                  "[class*='synopsis']", "[class*='Synopsis']", "[class*='summary']",
                  "[class*='Summary']", "[class*='excerpt']", "[class*='Excerpt']",
                  "[class*='body']", "[class*='teaser']", "[class*='detail']",
                  "[itemprop='description']", "p"]


def extract_events_generic(soup, url, source_name, venue_default,
                           card_selectors, categories_default=None):
    """Generic event extractor using multiple CSS selector strategies."""
    events = []
    cards = []
    for sel in card_selectors:
        cards = soup.select(sel)
        if len(cards) >= 1:
            break

    for card in cards:
        title = find_text(card, TITLE_SELECTORS)
        if not title:
            continue

        date_text = find_text(card, DATE_SELECTORS)
        venue = find_text(card, VENUE_SELECTORS) or venue_default
        price_text = find_text(card, PRICE_SELECTORS)
        desc_text = find_text(card, DESC_SELECTORS)
        link = find_link(card, url) or url

        date_start, date_end, date_display = parse_date_range(date_text)

        # Clean up description: cap at 300 chars, skip if it's just the title repeated
        desc = None
        if desc_text and desc_text.strip().lower() != title.strip().lower() and len(desc_text) > 10:
            desc = clean_text(desc_text)[:300]

        ev = {
            "id": make_id(source_name, title, date_text),
            "title": title,
            "date_display": date_display or date_text,
            "date_start": date_start,
            "date_end": date_end,
            "time": None,
            "venue": venue,
            "source": source_name,
            "source_url": url,
            "link": link,
            "price": parse_price(price_text),
            "categories": categories_default or categorize(title, venue),
            "description": desc,
        }

        if validate_event(ev):
            events.append(ev)

    return events


def extract_json_ld_events(soup, url, source_name, venue_default):
    """Extract events from JSON-LD structured data (most reliable method)."""
    events = []
    for script in soup.select("script[type='application/ld+json']"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        items = data if isinstance(data, list) else [data]
        # Also handle @graph
        if isinstance(data, dict) and "@graph" in data:
            items = data["@graph"]

        event_types = {"Event", "MusicEvent", "TheaterEvent",
                       "DanceEvent", "Festival", "ComedyEvent",
                       "EducationEvent", "SocialEvent"}
        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type", "")
            # Handle @type as string or list
            if isinstance(item_type, list):
                if not any(t in event_types for t in item_type):
                    continue
            elif item_type not in event_types:
                continue

            title = item.get("name", "")
            if not title:
                continue

            start = item.get("startDate", "")
            end = item.get("endDate", start)
            location = item.get("location", {})
            if isinstance(location, dict):
                venue = location.get("name", venue_default)
            else:
                venue = venue_default

            link = item.get("url", url)
            price = None
            offers = item.get("offers", {})
            if isinstance(offers, dict):
                p = offers.get("price") or offers.get("lowPrice")
                if p:
                    price = f"${p}" if str(p).replace('.', '').isdigit() else str(p)
            elif isinstance(offers, list) and offers:
                p = offers[0].get("price") or offers[0].get("lowPrice")
                if p:
                    price = f"${p}" if str(p).replace('.', '').isdigit() else str(p)

            desc = item.get("description", "")
            image = item.get("image", None)
            if isinstance(image, list):
                image = image[0] if image else None
            if isinstance(image, dict):
                image = image.get("url")

            # Parse dates
            date_start = start[:10] if start and len(start) >= 10 else None
            date_end = end[:10] if end and len(end) >= 10 else None

            ev = {
                "id": make_id(source_name, title, start),
                "title": clean_text(title),
                "date_display": f"{start[:10]} – {end[:10]}" if date_start and date_end and date_start != date_end else (date_start or ""),
                "date_start": date_start,
                "date_end": date_end,
                "time": None,
                "venue": clean_text(venue),
                "source": source_name,
                "source_url": url,
                "link": link,
                "price": price,
                "categories": categorize(title, venue),
                "description": clean_text(desc)[:300] if desc else None,
            }

            if validate_event(ev):
                events.append(ev)

    return events


def extract_microdata_events(soup, url, source_name, venue_default):
    """Extract events from HTML Microdata (itemscope/itemprop attributes)."""
    events = []
    for item in soup.select('[itemtype*="schema.org/Event"], [itemtype*="schema.org/MusicEvent"], '
                            '[itemtype*="schema.org/TheaterEvent"], [itemtype*="schema.org/DanceEvent"]'):
        title_el = item.select_one('[itemprop="name"]')
        title = clean_text(title_el.get_text()) if title_el else ""
        if not title:
            continue

        start_el = item.select_one('[itemprop="startDate"]')
        end_el = item.select_one('[itemprop="endDate"]')
        start_date = (start_el.get("content") or start_el.get("datetime") or
                      clean_text(start_el.get_text())) if start_el else ""
        end_date = (end_el.get("content") or end_el.get("datetime") or
                    clean_text(end_el.get_text())) if end_el else start_date

        location_el = item.select_one('[itemprop="location"] [itemprop="name"]')
        venue = clean_text(location_el.get_text()) if location_el else venue_default

        url_el = item.select_one('[itemprop="url"]')
        link = (url_el.get("href") or url_el.get("content") or "") if url_el else ""
        if link and not link.startswith("http"):
            link = urljoin(url, link)
        link = link or url

        price_el = item.select_one('[itemprop="price"], [itemprop="lowPrice"]')
        price = None
        if price_el:
            p = price_el.get("content") or clean_text(price_el.get_text())
            if p:
                price = f"${p}" if p.replace('.', '').isdigit() else parse_price(p)

        desc_el = item.select_one('[itemprop="description"]')
        desc = clean_text(desc_el.get_text())[:300] if desc_el else None

        date_start = start_date[:10] if start_date and len(start_date) >= 10 else None
        date_end = end_date[:10] if end_date and len(end_date) >= 10 else None

        ev = {
            "id": make_id(source_name, title, start_date),
            "title": title,
            "date_display": f"{date_start} – {date_end}" if date_start and date_end and date_start != date_end else (date_start or ""),
            "date_start": date_start,
            "date_end": date_end,
            "time": None,
            "venue": venue,
            "source": source_name,
            "source_url": url,
            "link": link,
            "price": price,
            "categories": categorize(title, venue),
            "description": desc,
        }
        if validate_event(ev):
            events.append(ev)

    return events


def extract_events_from_links(soup, url, source_name, venue_default, categories_default=None):
    """Last-resort fallback: extract events from links that look event-like."""
    events = []
    event_url_patterns = re.compile(
        r'/(event|show|performance|production|concert|program|ticket)s?/',
        re.IGNORECASE
    )
    seen_links = set()
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        full_url = urljoin(url, href) if not href.startswith("http") else href
        if full_url in seen_links:
            continue
        if not event_url_patterns.search(href):
            continue
        title = clean_text(a.get_text())
        if not title or len(title) < 3 or len(title) > 200:
            continue
        seen_links.add(full_url)

        # Try to find a date near this link
        parent = a.parent
        date_text = find_text(parent, DATE_SELECTORS) if parent else ""
        date_start, date_end, date_display = parse_date_range(date_text)

        ev = {
            "id": make_id(source_name, title, date_text),
            "title": title,
            "date_display": date_display or date_text,
            "date_start": date_start,
            "date_end": date_end,
            "time": None,
            "venue": venue_default,
            "source": source_name,
            "source_url": url,
            "link": full_url,
            "price": None,
            "categories": categories_default or categorize(title, venue_default),
            "description": None,
        }
        if validate_event(ev):
            events.append(ev)

    return events


def scrape_site(url, source_name, venue_default, card_selectors,
                categories_default=None):
    """Scrape a single venue site. Tries JSON-LD first, then HTML, then links."""
    r = safe_get(url)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "lxml")

    # Try JSON-LD first (most reliable)
    events = extract_json_ld_events(soup, url, source_name, venue_default)
    if events:
        REPORT["successes"].append(f"{source_name}: {len(events)} events (JSON-LD)")
        print(f"  {source_name}: {len(events)} events (via JSON-LD)")
        return events

    # Try Microdata (schema.org itemscope/itemprop)
    events = extract_microdata_events(soup, url, source_name, venue_default)
    if events:
        REPORT["successes"].append(f"{source_name}: {len(events)} events (Microdata)")
        print(f"  {source_name}: {len(events)} events (via Microdata)")
        return events

    # Fall back to HTML card scraping
    events = extract_events_generic(
        soup, url, source_name, venue_default,
        card_selectors, categories_default
    )
    if events:
        REPORT["successes"].append(f"{source_name}: {len(events)} events (HTML)")
        print(f"  {source_name}: {len(events)} events (via HTML)")
        return events

    # Last resort: extract from event-like links
    events = extract_events_from_links(
        soup, url, source_name, venue_default, categories_default
    )
    if events:
        REPORT["successes"].append(f"{source_name}: {len(events)} events (links)")
        print(f"  {source_name}: {len(events)} events (via link extraction)")
        return events

    msg = f"{source_name}: 0 events found at {url}"
    REPORT["warnings"].append(msg)
    print(f"  [WARN] {msg}")
    return events


# ---------------------------------------------------------------------------
# Source definitions — each is a real, verified Philadelphia venue/org
# ---------------------------------------------------------------------------

SOURCES = [
    {
        "name": "Ensemble Arts Philly",
        "url": "https://www.ensembleartsphilly.org/tickets-and-events",
        "venue": "Kimmel Cultural Campus",
        "cards": ["article", ".event-card", ".event-item",
                  "[class*='event']", "[class*='Event']", ".card"],
        "covers": "Classical, jazz, ballet, Broadway, theater, dance",
        "venues_list": ["Kimmel Center", "Academy of Music", "Miller Theater"],
    },
    {
        "name": "Philadelphia Orchestra",
        "url": "https://philorch.ensembleartsphilly.org/tickets-and-events/events",
        "venue": "Verizon Hall, Kimmel Center",
        "cards": ["article", ".event-card", ".event-item",
                  "[class*='event']", "[class*='Event']", ".performance",
                  "[class*='concert']"],
        "categories": ["classical"],
        "covers": "Classical concerts, orchestral performances",
        "venues_list": ["Verizon Hall"],
    },
    {
        "name": "Theatre Philadelphia",
        "url": "https://theatrephiladelphia.org/whats-on-stage",
        "venue": "Various Theaters",
        "cards": ["article", ".show-card", ".show-item", "[class*='show']",
                  ".views-row", ".node--type-show", "[class*='event']"],
        "covers": "All theater across Greater Philadelphia (aggregator)",
        "venues_list": ["Various"],
    },
    {
        "name": "Penn Live Arts",
        "url": "https://pennlivearts.org/events/",
        "venue": "Annenberg Center",
        "cards": ["article", ".event-card", "[class*='event']",
                  ".performance-item", ".views-row", ".card"],
        "covers": "Dance, music, jazz, classical, world, theater",
        "venues_list": ["Annenberg Center"],
    },
    {
        "name": "Opera Philadelphia",
        "url": "https://www.operaphila.org/whats-on/events/",
        "venue": "Academy of Music",
        "cards": ["article", ".event-card", "[class*='event']",
                  "[class*='Event']", ".views-row", ".card"],
        "categories": ["opera", "classical"],
        "covers": "Opera, vocal performances",
        "venues_list": ["Academy of Music", "Various"],
    },
    {
        "name": "Walnut Street Theatre",
        "url": "https://www.walnutstreettheatre.org/season/mainstage.php",
        "venue": "Walnut Street Theatre",
        "cards": ["article", ".show", "[class*='show']",
                  "[class*='production']", ".season-item", "table tr",
                  "[class*='event']"],
        "covers": "Musicals, plays",
        "venues_list": ["Walnut Street Theatre"],
    },
    {
        "name": "FringeArts",
        "url": "https://fringearts.com/programs/",
        "venue": "FringeArts",
        "cards": ["article", ".program", "[class*='program']",
                  "[class*='event']", ".views-row", ".card"],
        "covers": "Contemporary performance, experimental theater, dance",
        "venues_list": ["FringeArts"],
    },
    {
        "name": "Philadelphia Ballet",
        "url": "https://philadelphiaballet.org/performances/",
        "venue": "Academy of Music",
        "cards": ["article", "[class*='performance']", "[class*='show']",
                  "[class*='event']", "[class*='season']", ".card"],
        "categories": ["ballet", "dance"],
        "covers": "Ballet, dance",
        "venues_list": ["Academy of Music", "Merriam Theater"],
    },
    {
        "name": "Arden Theatre",
        "url": "https://ardentheatre.org/productions/",
        "venue": "Arden Theatre",
        "cards": ["article", "[class*='production']", "[class*='show']",
                  "[class*='event']", ".card"],
        "covers": "Theater, musicals, children's theater",
        "venues_list": ["Arden Theatre"],
    },
    {
        "name": "Chris' Jazz Cafe",
        "url": "https://www.chrisjazzcafe.com/events",
        "venue": "Chris' Jazz Cafe",
        "cards": ["article", "[class*='event']", "[class*='Event']",
                  ".sqs-block", ".summary-item", ".eventlist-event"],
        "categories": ["jazz"],
        "covers": "Jazz concerts",
        "venues_list": ["Chris' Jazz Cafe"],
    },
    {
        "name": "South Jazz Kitchen",
        "url": "https://www.southjazzkitchen.com/jazz-club/",
        "venue": "South Jazz Kitchen",
        "cards": ["article", "[class*='event']", "[class*='show']",
                  ".sqs-block", ".summary-item"],
        "categories": ["jazz"],
        "covers": "Jazz, dinner shows",
        "venues_list": ["South Jazz Kitchen"],
    },
    {
        "name": "World Cafe Live",
        "url": "https://worldcafelive.org/events/",
        "venue": "World Cafe Live",
        "cards": ["article", "[class*='event']", "[class*='Event']",
                  ".tribe-events-calendar-list__event", ".card"],
        "covers": "Concerts — jazz, folk, rock, world music",
        "venues_list": ["World Cafe Live"],
    },
    {
        "name": "City Winery",
        "url": "https://citywinery.com/pages/events/philadelphia",
        "venue": "City Winery Philadelphia",
        "cards": ["article", "[class*='event']", "[class*='Event']", ".card"],
        "covers": "Jazz, R&B, rock, comedy",
        "venues_list": ["City Winery Philadelphia"],
    },
    {
        "name": "PhiladelphiaDANCE.org",
        "url": "https://philadelphiadance.org/calendar/",
        "venue": "Various",
        "cards": ["article", "[class*='event']",
                  ".tribe-events-calendar-list__event",
                  ".type-tribe_events", ".card"],
        "categories": ["dance"],
        "covers": "Dance events (community aggregator)",
        "venues_list": ["Various"],
    },
    # Aggregator sources — broader coverage
    {
        "name": "Greater Phila. Cultural Alliance",
        "url": "https://www.philaculture.org/events-calendar",
        "venue": "Various",
        "cards": ["article", "[class*='event']", "[class*='Event']",
                  ".views-row", ".node", ".card",
                  ".tribe-events-calendar-list__event", "li.event"],
        "covers": "All Philadelphia cultural events (regional aggregator)",
        "venues_list": ["Various"],
    },
    {
        "name": "The Wilma Theater",
        "url": "https://www.wilmatheater.org/whats-on/",
        "venue": "The Wilma Theater",
        "cards": ["article", "[class*='production']", "[class*='show']",
                  "[class*='event']", "[class*='season']", ".card"],
        "covers": "Contemporary theater, premieres",
        "venues_list": ["The Wilma Theater"],
    },
    # ── Additional sources (added 2026-03-23) ──
    {
        "name": "BalletX",
        "url": "https://www.balletx.org/season-and-tickets/",
        "venue": "Various",
        "cards": ["article", "[class*='event']", "[class*='season']",
                  "[class*='performance']", ".card", "[class*='show']"],
        "categories": ["ballet", "dance"],
        "covers": "Contemporary ballet, dance",
        "venues_list": ["Various"],
    },
    {
        "name": "Philadelphia Theatre Company",
        "url": "https://www.philatheatreco.org/",
        "venue": "Suzanne Roberts Theatre",
        "cards": ["article", "[class*='show']", "[class*='production']",
                  "[class*='event']", ".card"],
        "covers": "Contemporary theater, world premieres",
        "venues_list": ["Suzanne Roberts Theatre"],
    },
    {
        "name": "Visit Philadelphia Events",
        "url": "https://www.visitphilly.com/things-to-do/events/",
        "venue": "Various",
        "cards": ["article", "[class*='event']", "[class*='card']",
                  ".views-row", "[class*='listing']", ".card"],
        "covers": "All Philadelphia events (tourism aggregator)",
        "venues_list": ["Various"],
    },
    {
        "name": "Philly Fun Guide",
        "url": "https://phillyfunguide.com/",
        "venue": "Various",
        "cards": ["article", "[class*='event']", "[class*='show']",
                  ".views-row", ".card", "[class*='listing']"],
        "covers": "All Philadelphia performing arts (TKTS discount aggregator)",
        "venues_list": ["Various"],
    },
]


# ---------------------------------------------------------------------------
# CATEGORIZATION
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS = {
    "musical": ["musical", "broadway", "hamilton", "wicked", "phantom",
                "les mis", "west side story", "cats ", "rent ", "chicago ",
                "cabaret", "hadestown", "mj the musical", "moulin rouge",
                "dear evan hansen", "six the musical"],
    "theater": ["play", "theatre", "theater", "drama", "comedy", "tragedy",
                "shakespeare", "monologue", "one-man", "one-woman",
                "staged reading", "production"],
    "dance": ["dance", "dancing", "choreograph", "modern dance",
              "contemporary dance", "hip hop dance", "tap dance", "flamenco"],
    "ballet": ["ballet", "nutcracker", "swan lake", "giselle",
               "sleeping beauty", "pas de deux", "pointe"],
    "jazz": ["jazz", "bebop", "swing", "big band", "jazz trio",
             "jazz quartet", "blue note", "jazz cafe", "jazz kitchen"],
    "classical": ["orchestra", "symphony", "philharmonic", "chamber",
                  "concerto", "sonata", "quartet", "recital", "classical",
                  "violin", "cello", "piano concert", "organ recital",
                  "chopin", "beethoven", "mozart", "bach ", "brahms"],
    "opera": ["opera", "soprano", "tenor", "baritone", "aria", "libretto"],
}

VENUE_CATEGORIES = {
    "walnut street theatre": ["theater", "musical"],
    "arden theatre": ["theater"],
    "fringearts": ["theater", "dance"],
    "chris' jazz cafe": ["jazz"],
    "south jazz kitchen": ["jazz"],
    "penn live arts": ["dance", "concert"],
    "annenberg center": ["dance", "concert"],
    "philadelphia ballet": ["ballet", "dance"],
    "academy of music": ["classical", "ballet", "opera"],
    "verizon hall": ["classical"],
    "kimmel": ["classical", "concert"],
}


def categorize(text, venue=""):
    """Categorize event based on title and venue keywords."""
    text_lower = (text or "").lower()
    venue_lower = (venue or "").lower()
    cats = set()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            cats.add(cat)
    for venue_name, venue_cats in VENUE_CATEGORIES.items():
        if venue_name in venue_lower:
            cats.update(venue_cats)
    return sorted(cats) if cats else ["performance"]


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("Philadelphia Cultural Events Scraper")
    print("=" * 50)
    print(f"Started: {datetime.utcnow().isoformat()}Z")
    print()

    all_events = []
    for i, src in enumerate(SOURCES):
        print(f"Scraping: {src['name']}")
        try:
            events = scrape_site(
                url=src["url"],
                source_name=src["name"],
                venue_default=src["venue"],
                card_selectors=src["cards"],
                categories_default=src.get("categories"),
            )
            all_events.extend(events)
        except Exception as e:
            msg = f"{src['name']}: ERROR {e}"
            print(f"  [ERROR] {msg}", file=sys.stderr)
            REPORT["failures"].append(msg)
        # Brief delay between sources to avoid rate limiting
        if i < len(SOURCES) - 1:
            time.sleep(1)

    # Merge in seed events if scraping yielded few results
    scraped_count = len(all_events)
    if scraped_count < 5:
        print(f"\nOnly {scraped_count} scraped events — merging seed data...")
        seed = get_seed_events()
        # Filter seed events to only include future/current events
        today = datetime.now().strftime("%Y-%m-%d")
        seed = [e for e in seed if (e.get("date_end") or e.get("date_start", "")) >= today]
        all_events.extend(seed)
        REPORT["successes"].append(f"Seed data: {len(seed)} verified events added")
        print(f"  Added {len(seed)} seed events (verified from public sources)")

    # Deduplicate by source + normalized title (same show at different venues is kept)
    seen = set()
    unique_events = []
    for ev in all_events:
        norm_title = re.sub(r'\s+', ' ', ev["title"].lower().strip())
        key = (ev.get("source", ""), norm_title)
        if key not in seen:
            seen.add(key)
            unique_events.append(ev)

    # Sort by date
    unique_events.sort(key=lambda e: e.get("date_start") or "9999-99-99")

    # Write events — preserve previous data if this scrape found nothing
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "events.json"

    if not unique_events and REPORT["failures"]:
        # Don't overwrite good data with empty results on failure
        print(f"\nNo events scraped and {len(REPORT['failures'])} failures — "
              f"preserving existing {out_path}")
    else:
        output = {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "total_events": len(unique_events),
            "sources": sorted({e["source"] for e in unique_events}),
            "scrape_report": {
                "successes": REPORT["successes"],
                "failures": REPORT["failures"],
                "warnings": REPORT["warnings"],
            },
            "events": unique_events,
        }
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nWrote {len(unique_events)} verified events to {out_path}")

    # Write sources metadata
    sources_meta = {
        "sources": [
            {
                "name": s["name"],
                "url": s["url"],
                "covers": s.get("covers", ""),
                "venues": s.get("venues_list", []),
            }
            for s in SOURCES
        ]
    }
    with open(OUTPUT_DIR / "sources.json", "w") as f:
        json.dump(sources_meta, f, indent=2)

    # Print report
    print(f"\n{'=' * 50}")
    print(f"SCRAPE REPORT")
    print(f"{'=' * 50}")
    print(f"Total events: {len(unique_events)}")
    print(f"Sources scraped: {len(REPORT['successes'])}")
    print(f"Sources failed: {len(REPORT['failures'])}")
    if REPORT["warnings"]:
        print(f"Warnings:")
        for w in REPORT["warnings"]:
            print(f"  - {w}")
    if REPORT["failures"]:
        print(f"Failures:")
        for f in REPORT["failures"]:
            print(f"  - {f}")

    # Exit with error if ALL sources failed (likely a network issue)
    if not unique_events and len(REPORT["failures"]) == len(SOURCES):
        print("\nERROR: All sources failed. Check network connectivity.",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
