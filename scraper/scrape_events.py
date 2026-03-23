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


def parse_time_from_iso(iso_str):
    """Extract a human-readable time from an ISO datetime string like '2026-03-24T20:00:00'.
    Returns e.g. '8:00 PM' or None."""
    if not iso_str or 'T' not in iso_str:
        return None
    try:
        # Handle various ISO formats: 2026-03-24T20:00:00, 2026-03-24T20:00:00-05:00, etc.
        time_part = iso_str.split('T')[1]
        # Strip timezone info
        time_part = re.sub(r'[Z+-]\d{0,2}:?\d{0,2}$', '', time_part)
        # Parse hours and minutes
        parts = time_part.split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        # Skip midnight (00:00) — usually means "no time specified"
        if hour == 0 and minute == 0:
            return None
        # Format as 12-hour time
        period = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        if minute == 0:
            return f"{display_hour}:00 {period}"
        return f"{display_hour}:{minute:02d} {period}"
    except (ValueError, IndexError):
        return None


def parse_time_from_text(text):
    """Extract a time string from free text like '8:00 PM', '7:30pm', 'Doors at 7 PM', etc.
    Returns e.g. '8:00 PM' or None."""
    if not text:
        return None
    # Match patterns like "8:00 PM", "7:30pm", "8 PM", "8:00 p.m."
    m = re.search(
        r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm|a\.m\.|p\.m\.)',
        text
    )
    if m:
        hour, minute, period = m.group(1), m.group(2), m.group(3).upper().replace('.', '')
        return f"{int(hour)}:{minute} {period}"
    # Match "8 PM" or "8pm" (no minutes)
    m = re.search(r'(\d{1,2})\s*(AM|PM|am|pm|a\.m\.|p\.m\.)', text)
    if m:
        hour, period = m.group(1), m.group(2).upper().replace('.', '')
        return f"{int(hour)}:00 {period}"
    return None


def slugify(text):
    """Convert text to URL-friendly slug: 'Lang Lang and Yannick' -> 'lang-lang-and-yannick'."""
    text = (text or "").lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text


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


# ---------------------------------------------------------------------------
# DETAIL PAGE ENRICHMENT
# Follows event links to detail pages to extract rich descriptions, times,
# prices, and direct ticket links that aren't available on listing pages.
# ---------------------------------------------------------------------------

# CSS selectors for detail page content
DETAIL_DESC_SELECTORS = [
    "[itemprop='description']",
    "[class*='event-description']", "[class*='event-detail']",
    "[class*='production-description']", "[class*='show-description']",
    "[class*='about']", "[class*='About']",
    "[class*='synopsis']", "[class*='Synopsis']",
    "[class*='description']", "[class*='Description']",
    "[class*='body-text']", "[class*='content-body']",
    "[class*='entry-content']",
    "article p", "main p", ".content p",
]

DETAIL_TIME_SELECTORS = [
    "[class*='showtime']", "[class*='show-time']",
    "[class*='event-time']", "[class*='performance-time']",
    "[class*='start-time']", "[class*='curtain']",
    "[class*='doors']", "[class*='begins']",
    "time[datetime]", "[datetime]",
    "[itemprop='startDate']",
    "[class*='time']", "[class*='Time']",
    "[class*='date-time']", "[class*='datetime']",
]

DETAIL_PRICE_SELECTORS = [
    "[itemprop='price']", "[itemprop='lowPrice']",
    "[class*='price']", "[class*='Price']",
    "[class*='ticket-price']", "[class*='cost']",
    "[class*='admission']",
    "[class*='starting-at']", "[class*='from-price']",
]

DETAIL_TICKET_SELECTORS = [
    "a[href*='ticket']", "a[href*='buy']", "a[href*='purchase']",
    "a[href*='checkout']", "a[href*='order']",
    "a[class*='ticket']", "a[class*='buy']",
    "[class*='ticket'] a", "[class*='buy'] a",
    "a[class*='cta']", "a[class*='action']",
]


def scrape_detail_page(url):
    """Fetch an event detail page and extract rich content.
    Returns dict with keys: description, time, price, ticket_url (all may be None).
    """
    result = {"description": None, "time": None, "price": None, "ticket_url": None}

    r = safe_get(url, timeout=15, retries=2)
    if not r:
        return result

    soup = BeautifulSoup(r.text, "lxml")

    # 1. Try JSON-LD first — most reliable source
    for script in soup.select("script[type='application/ld+json']"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        if isinstance(data, dict) and "@graph" in data:
            items = data["@graph"]
        event_types = {"Event", "MusicEvent", "TheaterEvent",
                       "DanceEvent", "Festival", "ComedyEvent"}
        for item in items:
            if not isinstance(item, dict):
                continue
            item_type = item.get("@type", "")
            if isinstance(item_type, list):
                if not any(t in event_types for t in item_type):
                    continue
            elif item_type not in event_types:
                continue

            desc = item.get("description", "")
            if desc and len(desc) > 20:
                result["description"] = clean_text(desc)[:800]

            start = item.get("startDate", "")
            if start and not result["time"]:
                result["time"] = parse_time_from_iso(start)

            offers = item.get("offers", {})
            if isinstance(offers, dict):
                p = offers.get("price") or offers.get("lowPrice")
                if p:
                    result["price"] = f"${p}" if str(p).replace('.', '').isdigit() else str(p)
                ticket_link = offers.get("url")
                if ticket_link:
                    result["ticket_url"] = ticket_link
            elif isinstance(offers, list) and offers:
                p = offers[0].get("price") or offers[0].get("lowPrice")
                if p:
                    result["price"] = f"${p}" if str(p).replace('.', '').isdigit() else str(p)
                ticket_link = offers[0].get("url")
                if ticket_link:
                    result["ticket_url"] = ticket_link

    # 2. Try meta tags (og:description, meta description)
    if not result["description"]:
        for meta in soup.select('meta[property="og:description"], meta[name="description"]'):
            content = meta.get("content", "").strip()
            if content and len(content) > 30:
                result["description"] = clean_text(content)[:800]
                break

    # 3. Try HTML selectors for description
    if not result["description"]:
        for sel in DETAIL_DESC_SELECTORS:
            els = soup.select(sel)
            for el in els:
                text = clean_text(el.get_text())
                # Skip very short text or navigation/boilerplate
                if len(text) > 50 and not any(skip in text.lower() for skip in
                    ["cookie", "privacy", "subscribe", "sign up", "newsletter"]):
                    result["description"] = text[:800]
                    break
            if result["description"]:
                break

    # 4. Try HTML selectors for time
    if not result["time"]:
        # Check datetime attributes first
        for sel in ["time[datetime]", "[datetime]", "[itemprop='startDate']"]:
            el = soup.select_one(sel)
            if el:
                dt_attr = el.get("datetime") or el.get("content") or ""
                t = parse_time_from_iso(dt_attr)
                if t:
                    result["time"] = t
                    break
        # Then check text content
        if not result["time"]:
            for sel in DETAIL_TIME_SELECTORS:
                els = soup.select(sel)
                for el in els:
                    text = el.get_text()
                    t = parse_time_from_text(text)
                    if t:
                        result["time"] = t
                        break
                if result["time"]:
                    break
        # Also check full page text for common time patterns like "7:30pm" near date
        if not result["time"]:
            page_text = soup.get_text()
            t = parse_time_from_text(page_text[:5000])  # Only check first part of page
            if t:
                result["time"] = t

    # 5. Try HTML selectors for price
    if not result["price"]:
        for sel in DETAIL_PRICE_SELECTORS:
            els = soup.select(sel)
            for el in els:
                text = el.get_text().strip()
                p = parse_price(text)
                if p:
                    result["price"] = p
                    break
            if result["price"]:
                break
        # Also check page text for price patterns
        if not result["price"]:
            page_text = soup.get_text()
            # Look for "Starting at $XX" or "From $XX" or "Tickets: $XX"
            price_match = re.search(
                r'(?:starting\s+(?:at|from)|from|tickets?\s*:?\s*(?:from)?)\s*\$[\d,.]+',
                page_text, re.IGNORECASE
            )
            if price_match:
                result["price"] = parse_price(price_match.group())

    # 6. Try to find direct ticket link
    if not result["ticket_url"]:
        for sel in DETAIL_TICKET_SELECTORS:
            el = soup.select_one(sel)
            if el:
                href = el.get("href", "")
                if href and href.startswith("http"):
                    result["ticket_url"] = href
                    break
                elif href:
                    result["ticket_url"] = urljoin(url, href)
                    break

    return result


def enrich_events(events, max_detail_fetches=40):
    """Enrich events by fetching their detail pages for missing data.
    Only fetches detail pages for events that need enrichment and have a usable link.
    """
    enriched = 0
    for ev in events:
        if enriched >= max_detail_fetches:
            print(f"  [INFO] Reached max detail page fetches ({max_detail_fetches})")
            break

        link = ev.get("link", "")
        source_url = ev.get("source_url", "")

        # Skip if link is same as source_url (generic listing page) — nothing new to learn
        # unless we can guess a better URL
        needs_enrichment = (
            not ev.get("description")
            or not ev.get("time")
            or not ev.get("price")
            or link == source_url  # link points to generic listing page
        )

        if not needs_enrichment:
            continue

        # If link is the same as source_url, try to discover the detail page URL
        detail_url = link if link != source_url else None
        if not detail_url:
            detail_url = guess_detail_url(ev)
        if not detail_url:
            continue

        print(f"    Enriching: {ev.get('title', '?')[:50]} from {detail_url[:80]}")
        detail = scrape_detail_page(detail_url)
        enriched += 1

        # Merge enrichment data — only fill in missing fields
        if detail["description"] and not ev.get("description"):
            ev["description"] = detail["description"]
        elif detail["description"] and ev.get("description") and len(detail["description"]) > len(ev["description"]) * 1.5:
            # Use detail page description if it's substantially longer
            ev["description"] = detail["description"]
        if detail["time"] and not ev.get("time"):
            ev["time"] = detail["time"]
        if detail["price"] and not ev.get("price"):
            ev["price"] = detail["price"]
        # Update the event link to point to the actual detail page (not the listing)
        if link == source_url and detail_url:
            ev["link"] = detail_url

        # Small delay to be polite
        time.sleep(0.5)

    print(f"  Enriched {enriched} events from detail pages")
    return events


# ---------------------------------------------------------------------------
# VENUE-SPECIFIC URL PATTERNS — used to guess detail page URLs
# ---------------------------------------------------------------------------

# Maps source name -> function that generates a detail page URL from event data
def _ensemble_arts_url(ev):
    """Guess Ensemble Arts Philly detail page URL from event title and venue."""
    slug = slugify(ev.get("title", ""))
    if not slug:
        return None
    venue = (ev.get("venue") or "").lower()
    # Determine the organization path
    if "orchestra" in (ev.get("source") or "").lower() or "orchestra" in venue:
        return f"https://www.ensembleartsphilly.org/tickets-and-events/philadelphia-orchestra/2025-26-season/{slug}"
    # Broadway/musical at Academy or Forrest
    cats = ev.get("categories", [])
    if "musical" in cats and ("academy" in venue or "forrest" in venue):
        return f"https://www.ensembleartsphilly.org/tickets-and-events/broadway/2025-26-season/{slug}"
    # Jazz events at Perelman
    if "jazz" in cats or "perelman" in venue:
        return f"https://www.ensembleartsphilly.org/tickets-and-events/jazz/2025-26-season/{slug}"
    # Default: try the main events path
    return f"https://www.ensembleartsphilly.org/tickets-and-events/events/{slug}"


def _phila_orchestra_url(ev):
    slug = slugify(ev.get("title", ""))
    return f"https://www.ensembleartsphilly.org/tickets-and-events/philadelphia-orchestra/2025-26-season/{slug}" if slug else None


def _penn_live_arts_url(ev):
    slug = slugify(ev.get("title", ""))
    return f"https://pennlivearts.org/event/{slug}" if slug else None


def _arden_url(ev):
    slug = slugify(ev.get("title", ""))
    return f"https://ardentheatre.org/productions/{slug}/" if slug else None


def _wilma_url(ev):
    slug = slugify(ev.get("title", ""))
    return f"https://www.wilmatheater.org/whats-on/{slug}/" if slug else None


def _opera_phila_url(ev):
    slug = slugify(ev.get("title", ""))
    return f"https://www.operaphila.org/whats-on/events/{slug}/" if slug else None


def _fringearts_url(ev):
    slug = slugify(ev.get("title", ""))
    return f"https://fringearts.com/event/{slug}/" if slug else None


def _walnut_street_url(ev):
    slug = slugify(ev.get("title", ""))
    return f"https://www.walnutstreettheatre.org/season/{slug}" if slug else None


def _phila_theatre_co_url(ev):
    slug = slugify(ev.get("title", ""))
    return f"https://www.philatheatreco.org/{slug}" if slug else None


def _phila_ballet_url(ev):
    slug = slugify(ev.get("title", ""))
    return f"https://philadelphiaballet.org/performances/{slug}/" if slug else None


def _balletx_url(ev):
    slug = slugify(ev.get("title", ""))
    return f"https://www.balletx.org/seasons/{slug}/" if slug else None


_VENUE_URL_GUESSERS = {
    "Ensemble Arts Philly": _ensemble_arts_url,
    "Philadelphia Orchestra": _phila_orchestra_url,
    "Penn Live Arts": _penn_live_arts_url,
    "Arden Theatre": _arden_url,
    "The Wilma Theater": _wilma_url,
    "Opera Philadelphia": _opera_phila_url,
    "FringeArts": _fringearts_url,
    "Walnut Street Theatre": _walnut_street_url,
    "Philadelphia Theatre Company": _phila_theatre_co_url,
    "Philadelphia Ballet": _phila_ballet_url,
    "BalletX": _balletx_url,
}


def guess_detail_url(ev):
    """Try to construct a detail page URL for this event based on venue URL patterns."""
    source = ev.get("source", "")
    guesser = _VENUE_URL_GUESSERS.get(source)
    if guesser:
        return guesser(ev)
    return None


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
TIME_SELECTORS = ["[class*='time']", "[class*='Time']", ".event-time",
                  "[class*='showtime']", "[class*='start-time']", "[class*='doors']",
                  "time", "[datetime]", "[itemprop='startDate']"]
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

        # Extract time: try dedicated time selectors, then parse from date text
        time_text = find_text(card, TIME_SELECTORS)
        event_time = parse_time_from_text(time_text)
        if not event_time:
            event_time = parse_time_from_text(date_text)
        if not event_time:
            # Check for datetime attributes on time elements
            for sel in ["time[datetime]", "[datetime]", "[itemprop='startDate']"]:
                el = card.select_one(sel)
                if el:
                    dt_attr = el.get("datetime") or el.get("content") or ""
                    event_time = parse_time_from_iso(dt_attr)
                    if event_time:
                        break

        # Clean up description: cap at 500 chars, skip if it's just the title repeated
        desc = None
        if desc_text and desc_text.strip().lower() != title.strip().lower() and len(desc_text) > 10:
            desc = clean_text(desc_text)[:500]

        ev = {
            "id": make_id(source_name, title, date_text),
            "title": title,
            "date_display": date_display or date_text,
            "date_start": date_start,
            "date_end": date_end,
            "time": event_time,
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


def extract_squarespace_events(url, source_name, venue_default,
                                categories_default=None):
    """Extract events from Squarespace JSON API (?format=json).
    Squarespace sites expose a JSON endpoint with full event data including
    titles, descriptions, dates, URLs, and more. This is the most reliable
    method for Squarespace-based venues like Chris' Jazz Cafe.
    Returns list of event dicts, or empty list if not a Squarespace site.
    """
    json_url = url.rstrip("/") + "?format=json"
    events = []
    try:
        r = SESSION.get(json_url, timeout=15,
                        headers={**HEADERS, "Accept": "application/json"})
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception:
        return []

    # Squarespace returns events under various keys
    items = []
    if isinstance(data, dict):
        # Try known Squarespace response structures
        items = data.get("items") or data.get("upcoming") or data.get("events") or []
        # Also check nested "collection" -> "items"
        if not items and "collection" in data:
            items = data["collection"].get("items", [])
        # Some Squarespace sites return past/upcoming split
        if not items and "past" in data:
            items = (data.get("upcoming") or []) + (data.get("past") or [])
    elif isinstance(data, list):
        items = data

    base_url = url.rsplit("/", 1)[0] if "/" in url else url
    site_root = "/".join(url.split("/")[:3])  # e.g., https://www.chrisjazzcafe.com

    for item in items:
        if not isinstance(item, dict):
            continue

        title = item.get("title", "").strip()
        if not title:
            continue

        # Build detail page URL from fullUrl or urlId
        full_url = item.get("fullUrl") or item.get("sourceUrl") or ""
        if full_url and not full_url.startswith("http"):
            full_url = site_root + full_url
        item_url = full_url or url

        # Parse dates (Squarespace uses millisecond timestamps)
        start_ts = item.get("startDate")
        end_ts = item.get("endDate")
        date_start = date_end = event_time = None
        if isinstance(start_ts, (int, float)) and start_ts > 1000000000:
            # Millisecond timestamp
            if start_ts > 1e12:
                start_ts = start_ts / 1000
            try:
                dt = datetime.fromtimestamp(start_ts)
                date_start = dt.strftime("%Y-%m-%d")
                h, m = dt.hour, dt.minute
                if h != 0 or m != 0:
                    period = "AM" if h < 12 else "PM"
                    dh = h if h <= 12 else h - 12
                    if dh == 0:
                        dh = 12
                    event_time = f"{dh}:{m:02d} {period}"
            except (ValueError, OSError):
                pass
        elif isinstance(start_ts, str):
            date_start = start_ts[:10] if len(start_ts) >= 10 else None
            event_time = parse_time_from_iso(start_ts)

        if isinstance(end_ts, (int, float)) and end_ts > 1000000000:
            if end_ts > 1e12:
                end_ts = end_ts / 1000
            try:
                date_end = datetime.fromtimestamp(end_ts).strftime("%Y-%m-%d")
            except (ValueError, OSError):
                date_end = date_start
        elif isinstance(end_ts, str):
            date_end = end_ts[:10] if len(end_ts) >= 10 else date_start
        else:
            date_end = date_start

        # Description: prefer excerpt, fall back to body text
        desc = ""
        excerpt = item.get("excerpt") or item.get("asExcerpt") or ""
        body = item.get("body") or ""
        if excerpt:
            desc = clean_text(BeautifulSoup(excerpt, "lxml").get_text())[:800]
        elif body:
            desc = clean_text(BeautifulSoup(body, "lxml").get_text())[:800]

        # Price: try structured data or parse from body/excerpt
        price = None
        struct = item.get("structuredContent") or {}
        if isinstance(struct, dict):
            price_val = struct.get("ticketPrice") or struct.get("price")
            if price_val:
                price = parse_price(str(price_val))
        if not price and (desc or body):
            price_text = desc or clean_text(BeautifulSoup(body, "lxml").get_text())
            price = parse_price(price_text)

        # Date display
        date_display = ""
        if date_start and date_end and date_start != date_end:
            date_display = f"{date_start} – {date_end}"
        elif date_start:
            date_display = date_start

        ev = {
            "id": make_id(source_name, title, str(start_ts or "")),
            "title": clean_text(title),
            "date_display": date_display,
            "date_start": date_start,
            "date_end": date_end,
            "time": event_time,
            "venue": venue_default,
            "source": source_name,
            "source_url": url,
            "link": item_url,
            "price": price,
            "categories": categories_default or categorize(title, venue_default),
            "description": desc if desc and len(desc) > 20 else None,
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

            # Parse dates and times from ISO datetimes
            date_start = start[:10] if start and len(start) >= 10 else None
            date_end = end[:10] if end and len(end) >= 10 else None
            event_time = parse_time_from_iso(start)

            ev = {
                "id": make_id(source_name, title, start),
                "title": clean_text(title),
                "date_display": f"{start[:10]} – {end[:10]}" if date_start and date_end and date_start != date_end else (date_start or ""),
                "date_start": date_start,
                "date_end": date_end,
                "time": event_time,
                "venue": clean_text(venue),
                "source": source_name,
                "source_url": url,
                "link": link,
                "price": price,
                "categories": categorize(title, venue),
                "description": clean_text(desc)[:500] if desc else None,
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
        desc = clean_text(desc_el.get_text())[:500] if desc_el else None

        date_start = start_date[:10] if start_date and len(start_date) >= 10 else None
        date_end = end_date[:10] if end_date and len(end_date) >= 10 else None
        event_time = parse_time_from_iso(start_date) or parse_time_from_text(start_date)

        ev = {
            "id": make_id(source_name, title, start_date),
            "title": title,
            "date_display": f"{date_start} – {date_end}" if date_start and date_end and date_start != date_end else (date_start or ""),
            "date_start": date_start,
            "date_end": date_end,
            "time": event_time,
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


def discover_event_links(soup, url):
    """Scan a listing page for links that look like individual event detail pages.
    Returns a dict mapping normalized title -> detail page URL.
    """
    event_url_patterns = re.compile(
        r'/(event|show|performance|production|concert|program|ticket|season|whats-on)s?/',
        re.IGNORECASE
    )
    # Also match Squarespace-style numeric URLs like /events/131523 or /shows/363632
    numeric_url_patterns = re.compile(
        r'/(event|show)s?/\d+', re.IGNORECASE
    )
    discovered = {}
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        full_url = urljoin(url, href) if not href.startswith("http") else href
        # Only consider links that look like event detail pages (not the listing page itself)
        if full_url == url or full_url.rstrip("/") == url.rstrip("/"):
            continue
        if (not event_url_patterns.search(href) and
                not numeric_url_patterns.search(href) and
                href.count("/") < 3):
            continue
        title = clean_text(a.get_text())
        if title and len(title) >= 3 and len(title) <= 200:
            norm = re.sub(r'\s+', ' ', title.lower().strip())
            discovered[norm] = full_url
    return discovered


def scrape_site(url, source_name, venue_default, card_selectors,
                categories_default=None, squarespace=False):
    """Scrape a single venue site. Tries JSON-LD first, then HTML, then links.
    After extracting events, discovers detail page links from the listing page.
    If squarespace=True, tries the Squarespace JSON API first.
    """
    # For Squarespace sites, try JSON API first (most reliable for these sites)
    if squarespace:
        events = extract_squarespace_events(
            url, source_name, venue_default, categories_default
        )
        if events:
            REPORT["successes"].append(f"{source_name}: {len(events)} events (Squarespace JSON)")
            print(f"  {source_name}: {len(events)} events (via Squarespace JSON)")
            return events

    r = safe_get(url)
    if not r:
        return []

    soup = BeautifulSoup(r.text, "lxml")

    # Discover per-event links from the listing page upfront
    discovered_links = discover_event_links(soup, url)

    # Try JSON-LD first (most reliable)
    events = extract_json_ld_events(soup, url, source_name, venue_default)
    if events:
        REPORT["successes"].append(f"{source_name}: {len(events)} events (JSON-LD)")
        print(f"  {source_name}: {len(events)} events (via JSON-LD)")
    else:
        # Try Microdata (schema.org itemscope/itemprop)
        events = extract_microdata_events(soup, url, source_name, venue_default)
        if events:
            REPORT["successes"].append(f"{source_name}: {len(events)} events (Microdata)")
            print(f"  {source_name}: {len(events)} events (via Microdata)")
        else:
            # Fall back to HTML card scraping
            events = extract_events_generic(
                soup, url, source_name, venue_default,
                card_selectors, categories_default
            )
            if events:
                REPORT["successes"].append(f"{source_name}: {len(events)} events (HTML)")
                print(f"  {source_name}: {len(events)} events (via HTML)")
            else:
                # Last resort: extract from event-like links
                events = extract_events_from_links(
                    soup, url, source_name, venue_default, categories_default
                )
                if events:
                    REPORT["successes"].append(f"{source_name}: {len(events)} events (links)")
                    print(f"  {source_name}: {len(events)} events (via link extraction)")
                else:
                    msg = f"{source_name}: 0 events found at {url}"
                    REPORT["warnings"].append(msg)
                    print(f"  [WARN] {msg}")

    # Match discovered detail page links to events that only have the generic listing URL
    if discovered_links:
        for ev in events:
            if ev.get("link") == url or not ev.get("link"):
                norm_title = re.sub(r'\s+', ' ', ev["title"].lower().strip())
                # Try exact match first
                if norm_title in discovered_links:
                    ev["link"] = discovered_links[norm_title]
                    continue
                # Try partial match (title is substring of link text or vice versa)
                for link_title, link_url in discovered_links.items():
                    if norm_title in link_title or link_title in norm_title:
                        ev["link"] = link_url
                        break
                    # Also check if the slug of the title appears in the URL
                    slug = slugify(ev["title"])
                    if slug and slug in link_url.lower():
                        ev["link"] = link_url
                        break

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
        "squarespace": True,
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
                squarespace=src.get("squarespace", False),
            )
            all_events.extend(events)
        except Exception as e:
            msg = f"{src['name']}: ERROR {e}"
            print(f"  [ERROR] {msg}", file=sys.stderr)
            REPORT["failures"].append(msg)
        # Brief delay between sources to avoid rate limiting
        if i < len(SOURCES) - 1:
            time.sleep(1)

    # Always merge seed events — they have verified descriptions and rich metadata
    scraped_count = len(all_events)
    seed = get_seed_events()
    today = datetime.now().strftime("%Y-%m-%d")
    seed = [e for e in seed if (e.get("date_end") or e.get("date_start", "")) >= today]
    all_events.extend(seed)
    REPORT["successes"].append(f"Seed data: {len(seed)} verified events merged")
    print(f"\n  Merged {len(seed)} seed events (verified descriptions + metadata)")

    # Enrich events by fetching detail pages for missing descriptions/times/prices
    print("\n  Enriching events from detail pages...")
    all_events = enrich_events(all_events, max_detail_fetches=50)

    # Deduplicate by source + normalized title — keep event with richest data
    seen = {}  # key -> index in unique_events
    unique_events = []
    for ev in all_events:
        norm_title = re.sub(r'\s+', ' ', ev["title"].lower().strip())
        key = (ev.get("source", ""), norm_title)
        if key not in seen:
            seen[key] = len(unique_events)
            unique_events.append(ev)
        else:
            # Merge: for each field, prefer the non-empty value
            existing = unique_events[seen[key]]
            for field in ("description", "price", "time", "link", "source_url",
                          "date_start", "date_end", "date_display", "venue"):
                new_val = ev.get(field)
                old_val = existing.get(field)
                if new_val and (not old_val or len(str(new_val)) > len(str(old_val))):
                    existing[field] = new_val
            # Merge categories
            old_cats = set(existing.get("categories") or [])
            new_cats = set(ev.get("categories") or [])
            if new_cats - old_cats:
                existing["categories"] = list(old_cats | new_cats)

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
