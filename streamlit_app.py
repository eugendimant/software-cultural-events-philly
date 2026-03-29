import streamlit as st
import json
import csv
import io
from datetime import datetime, timedelta
from pathlib import Path
import urllib.parse
from collections import Counter
import html as _html

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PhillyCulture — Philadelphia Arts & Culture",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Category colors ──────────────────────────────────────────────────────────
CAT_COLORS = {
    "musical": "#ff6b9d",
    "theater": "#ffa44f",
    "dance": "#4fd1c5",
    "ballet": "#f687b3",
    "jazz": "#63b3ed",
    "classical": "#d6a0ff",
    "opera": "#fc8181",
    "concert": "#68d391",
    "exhibition": "#f6ad55",
    "lecture": "#76e4f7",
    "science": "#9ae6b4",
    "performance": "#a0aec0",
}

CAT_ICONS = {
    "musical": "🎵", "theater": "🎭", "dance": "💃", "ballet": "🩰",
    "jazz": "🎷", "classical": "🎻", "opera": "🎤", "concert": "🎶",
    "exhibition": "🖼️", "lecture": "🎓", "science": "🔬",
    "performance": "🎪",
}

CATEGORIES = ["all", "musical", "theater", "dance", "ballet", "jazz", "classical", "opera", "concert", "exhibition", "lecture", "science", "performance"]


# ── Load seed events as fallback ─────────────────────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).parent / "scraper"))
try:
    from seed_events import get_seed_events
    FALLBACK_EVENTS = get_seed_events()
except Exception:
    FALLBACK_EVENTS = []


# ── Event sanitization (last line of defense) ────────────────────────────────
_JUNK_PHRASES = [
    "no upcoming events", "no events", "search form", "no results",
    "sign up for", "subscribe to", "cookie", "privacy policy",
    "page not found", "404", "coming soon", "start date", "e.g.,",
    "placeholder", "select date", "filter by", "sort by",
    "javascript", "enable javascript", "load more", "click here",
]

# Single-word titles that are instruments, genres, nav elements — NOT real events.
# Scrapers sometimes extract these from page headers, nav menus, or section labels.
_JUNK_EXACT_TITLES = {
    # Instruments
    "trumpet", "piano", "guitar", "drums", "bass", "violin",
    "saxophone", "flute", "cello", "clarinet", "trombone",
    "percussion", "vocals", "voice", "organ", "harp",
    # Genres / generic music words
    "jazz", "classical", "orchestra", "choir", "ensemble",
    "concert", "recital", "performance", "show", "event",
    # UI / navigation
    "view event", "buy tickets", "read more", "list view",
    "calendar view", "all events", "upcoming events", "past events",
    "description", "biography", "bio", "details", "info",
    "tickets", "pricing", "schedule", "dates", "times",
    "venue", "location", "directions", "parking",
    "food & drink", "food and drink", "merch", "merchandise",
    "online streaming", "pro studio services",
    "subscribe", "sign up", "newsletter", "donate", "login",
    "menu", "search", "home", "about", "contact", "gallery",
    # Museum nav/section labels that scrapers might extract
    "exhibitions", "exhibits", "exhibit", "exhibition",
    "programs", "events", "calendar", "on view", "plan your visit",
    "membership", "support", "education", "collections",
}

def _is_valid_event(event):
    """Filter out scraper artifacts and junk entries at display time.

    This is the LAST LINE OF DEFENSE. If an event doesn't have the minimum
    required data to display correctly, it gets rejected here.
    """
    if not isinstance(event, dict):
        return False
    title = (event.get("title") or "").strip()
    if not title or len(title) < 3:
        return False
    title_low = title.lower().strip()

    # ── REQUIRED DATA: must have a date to be shown ──
    # Events without dates look broken and confuse users.
    if not event.get("date_start"):
        return False

    # ── PRIVATE/CLOSED events should never appear ──
    if "closed" in title_low and ("private" in title_low or "event" in title_low):
        return False
    if "cancelled" in title_low or "canceled" in title_low:
        return False

    # Reject exact-match junk titles (instruments, nav items, etc.)
    if title_low in _JUNK_EXACT_TITLES:
        return False
    if any(phrase in title_low for phrase in _JUNK_PHRASES):
        return False
    # Must have at least a plausible title (some alpha characters)
    if sum(1 for c in title if c.isalpha()) < 3:
        return False
    # Reject date-like titles (e.g., "March 29", "April 5, 2026")
    if _re.match(r'^(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(,?\s*\d{4})?$', title, _re.IGNORECASE):
        return False
    if _re.match(r'^\d{1,2}/\d{1,2}(/\d{2,4})?$', title):
        return False
    if _re.match(r'^\d+$', title):
        return False
    # Reject titles that are just a day of the week (sometimes scraped from calendars)
    if title_low in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                     'saturday', 'sunday', 'today', 'tomorrow', 'date', 'time'):
        return False
    # Reject very short titles that are likely page artifacts
    if len(title) < 5 and not any(c.isupper() for c in title):
        return False
    # Reject titles starting with "Tickets" (nav artifacts)
    if title_low.startswith('tickets'):
        return False
    return True

def _deduplicate_events(events):
    """Remove duplicate events from the same source.

    When two events from the same source have very similar titles (one is a
    substring of the other), keep the one with more complete data (dates, venue).
    """
    kept = {}  # (source, normalized_title) -> event
    result = []

    def _norm(title):
        t = _re.sub(r'[^a-z0-9 ]', '', (title or '').lower()).strip()
        return _re.sub(r'\s+', ' ', t)

    def _completeness(e):
        """Score how complete an event's data is."""
        score = 0
        if e.get("date_start"):
            score += 3
        if e.get("venue"):
            score += 2
        if e.get("description"):
            score += 1
        if e.get("price"):
            score += 1
        return score

    for event in events:
        source = event.get("source", "")
        norm = _norm(event.get("title", ""))
        if not norm:
            result.append(event)
            continue

        # Check for substring matches against already-kept events
        is_dupe = False
        for (ks, kn), kept_ev in list(kept.items()):
            if ks != source:
                continue
            if len(kn) < 8 or len(norm) < 8:
                continue
            if kn in norm or norm in kn:
                # Duplicate — keep the more complete one
                if _completeness(event) > _completeness(kept_ev):
                    # Replace the existing one
                    result.remove(kept_ev)
                    result.append(event)
                    kept[(ks, kn)] = event
                    # Also index under the new norm
                    kept[(source, norm)] = event
                is_dupe = True
                break

        if not is_dupe:
            result.append(event)
            kept[(source, norm)] = event

    return result


def _sanitize_event(event):
    """Clean up event fields: replace None with defaults, strip garbage display text.
    Also rebuilds date_display from date_start/date_end to ensure consistency."""
    if not isinstance(event, dict):
        return event
    # Clean garbage date_display
    dd = (event.get("date_display") or "")
    if "start date" in dd.lower() or "e.g." in dd.lower() or "{{" in dd:
        event["date_display"] = ""

    # Rebuild date_display from date_start/date_end to ensure consistency.
    # This prevents stale date_display text from contradicting the actual dates.
    ds = event.get("date_start")
    de = event.get("date_end")
    if ds:
        try:
            from datetime import datetime as _dt
            start = _dt.strptime(ds, "%Y-%m-%d")
            fmt_s = start.strftime("%b %d, %Y") if not de or ds == de else start.strftime("%b %d")
            if de and de != ds:
                end = _dt.strptime(de, "%Y-%m-%d")
                fmt_e = end.strftime("%b %d, %Y")
                event["date_display"] = f"{fmt_s} – {fmt_e}"
            else:
                event["date_display"] = start.strftime("%b %d, %Y")
        except (ValueError, TypeError):
            pass  # Keep existing date_display if parsing fails

    return event


import re as _re

def _normalize_title(title):
    """Normalize a title for fuzzy matching."""
    return _re.sub(r'[^a-z0-9]+', ' ', (title or "").lower()).strip()


def _build_description_lookup():
    """Build a title -> description lookup from seed events."""
    lookup = {}
    for e in FALLBACK_EVENTS:
        desc = e.get("description", "")
        if desc and len(desc) > 30:
            key = _normalize_title(e.get("title", ""))
            if key:
                lookup[key] = desc
    return lookup

_SEED_DESC_LOOKUP = _build_description_lookup()


def _build_seed_lookup():
    """Build title -> (description, link, source) lookup from seed events."""
    lookup = {}
    for e in FALLBACK_EVENTS:
        key = _normalize_title(e.get("title", ""))
        if not key:
            continue
        desc = e.get("description", "")
        link = e.get("link", "")
        source_url = e.get("source_url", "")
        source = e.get("source", "")
        lookup[key] = {
            "description": desc if desc and len(desc) > 30 else None,
            "link": link if link and link != source_url else None,
            "source": source,
        }
    return lookup

_SEED_LOOKUP = _build_seed_lookup()


def _enrich_descriptions(events):
    """Fill in missing descriptions and fix generic links from seed data.

    This is the last line of defense — runs at display time to ensure
    every event tile has useful content regardless of scraper output.
    """
    for event in events:
        desc = (event.get("description") or "").strip()
        link = (event.get("link") or "").strip()
        source_url = (event.get("source_url") or "").strip()
        ev_source = event.get("source", "")
        link_is_generic = not link or link == source_url
        needs_desc = not desc or len(desc) < 40

        norm = _normalize_title(event.get("title", ""))

        if needs_desc or link_is_generic:
            # Strategy 1: Exact match against seed data
            seed = _SEED_LOOKUP.get(norm)
            if seed:
                if needs_desc and seed["description"]:
                    event["description"] = seed["description"]
                    needs_desc = False
                if link_is_generic and seed["link"]:
                    event["link"] = seed["link"]
                    link_is_generic = False

            # NO fuzzy/partial matching — only exact title matches are safe.
            # Fuzzy matching caused wrong descriptions and links to be assigned
            # to the wrong events (e.g., "Symphony No. 5" matching a different concert).

        # NO URL GUESSING: if we don't have a verified link from the
        # scraper or seed data, keep the source listing page URL.
        # Guessing URLs from title slugs produced broken/wrong links.

    return events


def _final_quality_gate(events):
    """LAST LINE OF DEFENSE: reject any event that would look broken on the site.

    This runs after ALL other processing. An event that reaches here must have
    at minimum: a title, a date, and a venue. If any of these are missing,
    the event is dropped — it's better to show fewer events than broken ones.

    Also sanitizes venue names, titles, and catches remaining data corruption.
    """
    result = []
    for event in events:
        title = (event.get("title") or "").strip()
        venue = (event.get("venue") or "").strip()
        ds = event.get("date_start")
        link = (event.get("link") or "").strip()

        # Must have title + date
        if not title or not ds:
            continue

        # ── Venue sanitization ──
        # Fix "12:00 p.m. | Academy of Music" -> extract time, keep venue
        m = _re.match(r'^(\d{1,2}:\d{2}\s*[ap]\.?m\.?)\s*\|\s*(.+)$', venue, _re.IGNORECASE)
        if m:
            time_raw = m.group(1).strip()
            venue = m.group(2).strip()
            if not event.get("time"):
                event["time"] = _re.sub(r'\.', '', time_raw).upper().strip()
        # Also catch "8:00 p.m. Academy of Music" (without pipe separator)
        m2 = _re.match(r'^(\d{1,2}:\d{2}\s*[ap]\.?m\.?)\s+([A-Z].+)$', venue, _re.IGNORECASE)
        if m2 and not m:
            time_raw = m2.group(1).strip()
            venue = m2.group(2).strip()
            if not event.get("time"):
                event["time"] = _re.sub(r'\.', '', time_raw).upper().strip()
        # Remove junk text concatenated with venue names
        venue = _re.sub(r'(Check Back for Availability|Best Availability|Limited Availability|Sold Out|Buy Tickets|Get Tickets|On Sale).*', '', venue, flags=_re.IGNORECASE).strip()
        # If venue still starts with a time, it's corrupt — clear it
        if _re.match(r'^\d{1,2}:\d{2}', venue):
            venue = ""
        # Fix common capitalization inconsistencies
        _venue_fixes = {
            "Academy Of Music": "Academy of Music",
        }
        venue = _venue_fixes.get(venue, venue)
        # Fix truncated venue names (Kimmel Cente -> Kimmel Center)
        for trunc, full in [("Cente", "Center"), (", Kimmel C", ", Kimmel Center"),
                             ("Penn Live Ar", "Penn Live Arts")]:
            if venue.endswith(trunc):
                venue = venue[:-len(trunc)] + full
        event["venue"] = venue

        # ── Title sanitization ──
        # Fix ALL-CAPS titles
        if title == title.upper() and len(title) > 10:
            title = title.title()
            # Fix common small words
            for old, new in [(' The ', ' the '), (' And ', ' and '), (' For ', ' for '),
                             (' Of ', ' of '), (' In ', ' in '), (' At ', ' at ')]:
                title = title.replace(old, new)
            # But capitalize first word
            title = title[0].upper() + title[1:]
            event["title"] = title

        # Truncate very long titles at 80 chars
        if len(title) > 80:
            event["title"] = title[:77].rsplit(' ', 1)[0] + '...'

        # Must have a link (at minimum the source listing page)
        if not link:
            source_url = (event.get("source_url") or "").strip()
            if source_url:
                event["link"] = source_url
            else:
                continue

        # If venue is missing, show source name as venue context
        if not venue:
            source = (event.get("source") or "").strip()
            if source:
                event["venue"] = source
            else:
                event["venue"] = "Philadelphia"

        # Ensure date_display is populated
        if not event.get("date_display"):
            event["date_display"] = ds

        result.append(event)

    return result


def _sanitize_links(events):
    """Runtime link health check — catches malformed or suspicious URLs.

    This is the self-correcting safety net that runs every time events load.
    It catches issues that slip past the scraper and enrichment stages:
      - Malformed URLs (missing scheme, empty after trim)
      - Links that point to a different venue's domain
      - Auto-generated links with known-bad patterns
    Broken links fall back to source_url (the venue's listing page).
    """
    # Known domain -> source mapping for cross-venue detection
    _domain_source = {
        "chrisjazzcafe.com": "Chris' Jazz Cafe",
        "ensembleartsphilly.org": ("Ensemble Arts Philly", "Philadelphia Orchestra"),
        "ardentheatre.org": "Arden Theatre",
        "wilmatheater.org": "The Wilma Theater",
        "operaphila.org": "Opera Philadelphia",
        "fringearts.com": "FringeArts",
        "pennlivearts.org": "Penn Live Arts",
        "walnutstreettheatre.org": "Walnut Street Theatre",
        "philatheatreco.org": "Philadelphia Theatre Company",
    }

    for event in events:
        link = (event.get("link") or "").strip()
        source_url = (event.get("source_url") or "").strip()
        source = event.get("source", "")

        if not link or link == "#":
            continue

        # Check 1: Must be a valid HTTP(S) URL
        if not link.startswith(("http://", "https://")):
            event["link"] = source_url or ""
            continue

        # Check 2: Link domain should match the event's source
        try:
            from urllib.parse import urlparse
            domain = urlparse(link).netloc.lower().replace("www.", "")
        except Exception:
            event["link"] = source_url or ""
            continue

        for known_domain, expected_sources in _domain_source.items():
            if known_domain in domain:
                if isinstance(expected_sources, str):
                    expected_sources = (expected_sources,)
                if source and source not in expected_sources:
                    # Link points to wrong venue — reset
                    event["link"] = source_url or ""
                break

    return events


def _validate_dates(events):
    """Check event dates for obvious errors and clear bad data.

    Catches:
      - date_end before date_start
      - Dates more than 2 years in the future (likely parsing errors)
      - date_start in the far past for events that aren't exhibitions
    """
    from datetime import datetime as _dt, timedelta
    today = _dt.now().date()
    max_future = today + timedelta(days=730)  # 2 years

    for event in events:
        ds = event.get("date_start")
        de = event.get("date_end")
        if not ds:
            continue
        try:
            start = _dt.strptime(ds, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            event["date_start"] = None
            event["date_end"] = None
            event["date_display"] = ""
            continue

        end = None
        if de:
            try:
                end = _dt.strptime(de, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                event["date_end"] = ds  # default to start

        # End before start — clearly wrong
        if end and end < start:
            event["date_end"] = ds

        # Dates more than 2 years in the future — likely parsing error
        if start > max_future:
            event["date_start"] = None
            event["date_end"] = None
            event["date_display"] = ""

    return events


def _validate_venue_source_consistency(events):
    """Check that event venues are plausible for their source.

    Some sources perform at specific known venues. If an event's venue
    doesn't match any known venue for that source, set it to None (N/A)
    rather than showing wrong information.
    """
    # Map of source -> set of known venue substrings (lowercase)
    _source_venues = {
        "Chris' Jazz Cafe": {"chris", "jazz cafe"},
        "South Jazz Kitchen": {"south jazz"},
        "Walnut Street Theatre": {"walnut"},
        "Arden Theatre": {"arden"},
        "The Wilma Theater": {"wilma"},
        "FringeArts": {"fringe"},
        "Philadelphia Museum of Art": {"museum of art", "philamuseum"},
        "The Franklin Institute": {"franklin"},
        "Penn Museum": {"penn museum"},
        "Academy of Natural Sciences": {"natural sciences", "ansp"},
        "Mütter Museum": {"mütter", "mutter"},
    }
    # These sources perform at VARIOUS venues — don't validate venue
    _multi_venue_sources = {
        "Ensemble Arts Philly", "Philadelphia Orchestra", "Opera Philadelphia",
        "Penn Live Arts", "Philadelphia Ballet", "BalletX",
        "Theatre Philadelphia", "PhiladelphiaDANCE.org",
        "Greater Phila. Cultural Alliance", "Visit Philadelphia Events",
        "Profs and Pints", "Science on Tap", "Sofar Sounds Philadelphia",
        "City Winery", "World Cafe Live", "Philly Fun Guide",
    }

    for event in events:
        source = event.get("source", "")
        venue = (event.get("venue") or "").strip()
        if not venue or source in _multi_venue_sources:
            continue
        known = _source_venues.get(source)
        if known:
            venue_low = venue.lower()
            if not any(k in venue_low for k in known):
                # Venue doesn't match source — likely wrong data
                event["venue"] = None  # Will display as N/A

    return events


def _fix_cross_venue_contamination(events):
    """Detect and remove descriptions/links that belong to a different venue.
    This cleans up bad data from previous scraper runs with buggy partial matching.
    E.g., a Kimmel Center event titled 'Trumpet' that wrongly got a Chris' Jazz Cafe
    description about 'Trumpeter James McGovern'.
    """
    # Map of venue keywords -> venue identifier
    venue_markers = {
        "chris' jazz": "chris_jazz",
        "chris's jazz": "chris_jazz",
        "chris jazz": "chris_jazz",
        "chrisjazzcafe": "chris_jazz",
        "south jazz kitchen": "south_jazz",
        "world cafe live": "world_cafe",
        "kimmel": "kimmel", "marian anderson": "kimmel",
        "academy of music": "academy", "forrest theatre": "forrest",
        "arden theatre": "arden", "wilma theater": "wilma",
        "fringearts": "fringearts", "fringe arts": "fringearts",
        "penn live": "pennlive", "annenberg": "pennlive",
    }

    def _venue_id(text):
        # Normalize apostrophes and lowercase
        text_lower = (text or "").lower().replace("\u2019", "'")
        for marker, vid in venue_markers.items():
            if marker in text_lower:
                return vid
        return None

    for event in events:
        desc = event.get("description") or ""
        venue = event.get("venue") or ""
        link = event.get("link") or ""
        source_url = event.get("source_url") or ""

        ev_venue_id = _venue_id(venue) or _venue_id(event.get("source", ""))
        if not ev_venue_id:
            continue

        # Check if description mentions a DIFFERENT venue
        desc_venue_id = _venue_id(desc)
        if desc_venue_id and desc_venue_id != ev_venue_id:
            event["description"] = None  # Strip contaminated description

        # Check if link points to a DIFFERENT venue's website
        link_venue_id = _venue_id(link)
        if link_venue_id and link_venue_id != ev_venue_id:
            event["link"] = source_url or ""  # Reset to source URL

    return events


# ── Load events ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_events():
    json_path = Path(__file__).parent / "data" / "events.json"
    try:
        with open(json_path) as f:
            data = json.load(f)
        events = data.get("events", [])
        if len(events) == 0:
            raise ValueError("Empty events")
    except Exception:
        data = {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "sources": sorted({e.get("source", "") for e in FALLBACK_EVENTS if e.get("source")}),
            "events": list(FALLBACK_EVENTS),
            "scrape_report": {"successes": ["Using seed data"], "failures": [], "warnings": []},
        }
    # Merge seed events with scraped data.
    # CRITICAL: Seed data has been manually verified and is authoritative.
    # When both scraped and seed data exist for the same event, seed data
    # OVERRIDES scraped data for dates, venues, and prices — because the
    # scraper frequently produces garbage (wrong venues, wrong dates,
    # time-embedded-in-venue, etc.) while seed data is hand-verified.
    if FALLBACK_EVENTS:
        existing = {}  # (source, norm_title) -> event
        for e in data.get("events", []):
            norm = _re.sub(r'\s+', ' ', e.get("title", "").lower().strip())
            existing[(e.get("source", ""), norm)] = e
        today = datetime.now().strftime("%Y-%m-%d")
        for seed_ev in FALLBACK_EVENTS:
            norm = _re.sub(r'\s+', ' ', seed_ev.get("title", "").lower().strip())
            key = (seed_ev.get("source", ""), norm)
            end = seed_ev.get("date_end") or seed_ev.get("date_start", "")
            if key not in existing and end >= today:
                # New event from seed — add it
                data["events"].append(seed_ev)
                existing[key] = seed_ev
            elif key in existing:
                # Event exists in both scraped and seed data.
                # Seed data is authoritative — override scraped data.
                scraped = existing[key]
                if seed_ev.get("date_start"):
                    scraped["date_start"] = seed_ev["date_start"]
                if seed_ev.get("date_end"):
                    scraped["date_end"] = seed_ev["date_end"]
                if seed_ev.get("venue"):
                    scraped["venue"] = seed_ev["venue"]
                if seed_ev.get("description"):
                    scraped["description"] = seed_ev["description"]
                if seed_ev.get("price"):
                    scraped["price"] = seed_ev["price"]
                if seed_ev.get("time"):
                    scraped["time"] = seed_ev["time"]
                if seed_ev.get("link"):
                    scraped["link"] = seed_ev["link"]
        # Update sources list
        data["sources"] = sorted({e.get("source", "") for e in data["events"] if e.get("source")})
    # Sanitize: filter junk, clean fields
    data["events"] = [_sanitize_event(e) for e in data.get("events", []) if _is_valid_event(e)]
    # Deduplicate: remove variant titles from same source, prefer dated versions
    data["events"] = _deduplicate_events(data["events"])
    # Validate dates: catch obviously wrong dates
    data["events"] = _validate_dates(data["events"])
    # Fix cross-venue contamination (bad data from previous scraper runs)
    data["events"] = _fix_cross_venue_contamination(data["events"])
    # Validate venue-source consistency (catch wrong venue assignments)
    data["events"] = _validate_venue_source_consistency(data["events"])
    # Enrich: fill missing descriptions from seed data
    data["events"] = _enrich_descriptions(data["events"])
    # Sanitize links: catch malformed URLs and fall back gracefully
    data["events"] = _sanitize_links(data["events"])
    # FINAL QUALITY GATE: last line of defense — catch anything that slipped through
    data["events"] = _final_quality_gate(data["events"])
    return data


# ── Helpers ──────────────────────────────────────────────────────────────────
def _s(event, key, default=""):
    """Safely get a string field from an event, never returning None."""
    val = event.get(key)
    return val if val is not None else default


def _h(text):
    """HTML-escape text for safe embedding in unsafe_allow_html markup."""
    return _html.escape(str(text)) if text else ""


def _cats(event):
    """Safely get categories list from an event, never returning None."""
    val = event.get("categories")
    return val if isinstance(val, list) else []


def _parse_date(date_str):
    """Parse a YYYY-MM-DD string to a date object, or None on failure."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _event_dates(event):
    """Return (start_date, end_date) as date objects. end defaults to start."""
    start = _parse_date(_s(event, "date_start"))
    end = _parse_date(_s(event, "date_end")) or start
    return start, end


def get_month_key(iso_str):
    if not iso_str:
        return "Unknown"
    try:
        return datetime.strptime(iso_str, "%Y-%m-%d").strftime("%B %Y")
    except Exception:
        return "Unknown"


def effective_month_key(event):
    """For month grouping: ongoing events (start in the past) group under current month."""
    start_str = _s(event, "date_start")
    if not start_str:
        return "Unknown"
    try:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        if start_dt < today.replace(day=1):
            # Event started before this month — check if it's still ongoing
            end_str = _s(event, "date_end") or start_str
            end_dt = datetime.strptime(end_str, "%Y-%m-%d").date()
            if end_dt >= today:
                return today.strftime("%B %Y")
        return start_dt.strftime("%B %Y")
    except Exception:
        return "Unknown"


def today_str():
    return datetime.now().strftime("%Y-%m-%d")


def is_past(event):
    _start, end = _event_dates(event)
    if end is None:
        return False
    return end < datetime.now().date()


def is_current_or_future(event):
    return not is_past(event)


def is_this_week(event):
    start, end = _event_dates(event)
    if start is None:
        return False
    today = datetime.now().date()
    end_of_week = today + timedelta(days=(6 - today.weekday()))
    return start <= end_of_week and end >= today


def is_this_weekend(event):
    start, end = _event_dates(event)
    if start is None:
        return False
    today = datetime.now().date()
    weekday = today.weekday()
    if weekday <= 4:  # Mon-Fri: look ahead to this Friday
        friday = today + timedelta(days=(4 - weekday))
    else:  # Sat-Sun: look back to this Friday
        friday = today - timedelta(days=(weekday - 4))
    sunday = friday + timedelta(days=2)
    return start <= sunday and end >= friday


def is_happening_now(event):
    start, end = _event_dates(event)
    if start is None:
        return False
    today = datetime.now().date()
    return start <= today <= end


def _is_this_month(event):
    """Check if event overlaps with the current calendar month."""
    start, end = _event_dates(event)
    if start is None:
        return False
    today = datetime.now().date()
    month_start = today.replace(day=1)
    # Last day of month
    if today.month == 12:
        month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return start <= month_end and end >= month_start


def is_free(event):
    price = _s(event, "price").lower().strip()
    return price in ("free", "$0", "0", "$0.00") or price.startswith("free")


def days_until(event):
    start, end = _event_dates(event)
    if start is None:
        return ""
    today = datetime.now().date()
    delta = (start - today).days
    if delta < 0:
        if end >= today:
            return "Today"
        return "Past"
    elif delta == 0:
        return "Today"
    elif delta == 1:
        return "Tomorrow"
    elif delta < 7:
        return f"In {delta} days"
    else:
        return f"In {delta // 7}w"


def gcal_url(event):
    start_raw = _s(event, "date_start")
    if not start_raw:
        return "#"
    start_str = start_raw.replace("-", "")
    end_raw = _s(event, "date_end") or start_raw
    try:
        end_dt = datetime.strptime(end_raw, "%Y-%m-%d") + timedelta(days=1)
        end_str = end_dt.strftime("%Y%m%d")
    except Exception:
        end_str = start_str
    params = urllib.parse.urlencode({
        "action": "TEMPLATE",
        "text": _s(event, "title"),
        "dates": f"{start_str}/{end_str}",
        "details": _s(event, "description"),
        "location": _s(event, "venue"),
    })
    return f"https://calendar.google.com/calendar/render?{params}"


def maps_url(event):
    venue = _s(event, "venue")
    if not venue:
        return "#"
    return f"https://www.google.com/maps/search/{urllib.parse.quote(venue + ' Philadelphia PA')}"


def share_url(event):
    """Generate a mailto: link to share event details with someone."""
    title = _s(event, "title")
    venue = _s(event, "venue")
    dates = _s(event, "date_display")
    link = _s(event, "link")
    desc = _s(event, "description")
    body = f"{title}\n{venue}\n{dates}\n\n{desc}\n\nTickets: {link}"
    params = urllib.parse.urlencode({
        "subject": f"Check out: {title} in Philly!",
        "body": body,
    }, quote_via=urllib.parse.quote)
    return f"mailto:?{params}"


def event_description(event, max_sentences=2):
    """Get event description, truncated to max_sentences. Only uses scraped/verified data."""
    desc = _s(event, "description").strip()

    if not desc or len(desc) < 20:
        # No verified description available — do NOT fabricate one.
        # Show a minimal factual stub using only verified metadata.
        title = _s(event, "title")
        venue = _s(event, "venue")
        if venue:
            desc = f"{title} at {venue}."
        else:
            desc = title

    # Truncate to max_sentences
    sentences = _re.split(r'(?<=[.!?])\s+', desc)
    if len(sentences) > max_sentences:
        desc = " ".join(sentences[:max_sentences])
        if not desc.endswith((".", "!", "?")):
            desc += "."
    return desc


def category_badge_html(cat):
    color = CAT_COLORS.get(cat, "#a0aec0")
    icon = CAT_ICONS.get(cat, "")
    return f'<span style="background:{color}22;color:{color};padding:3px 12px;border-radius:12px;font-size:0.78rem;font-weight:600;margin-right:4px;text-transform:capitalize;">{icon} {cat}</span>'


def urgency_badge(event):
    label = days_until(event)
    if not label or label == "Past":
        return ""
    if label in ("Today", "Now"):
        return f'<span style="background:#ff6b9d22;color:#ff6b9d;padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:700;margin-left:8px">🔴 {label}</span>'
    elif label == "Tomorrow":
        return f'<span style="background:#ffa44f22;color:#ffa44f;padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:700;margin-left:8px">🟠 {label}</span>'
    else:
        return f'<span style="background:#4fd1c522;color:#4fd1c5;padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;margin-left:8px">{label}</span>'


def events_to_csv(events):
    """Convert list of events to CSV string for download/export."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Title", "Venue", "Start Date", "End Date", "Date Display", "Time",
                      "Price", "Categories", "Description", "Tickets URL", "Source"])
    for e in events:
        writer.writerow([
            _s(e, "title"),
            _s(e, "venue"),
            _s(e, "date_start"),
            _s(e, "date_end"),
            _s(e, "date_display"),
            _s(e, "time"),
            _s(e, "price"),
            ", ".join(_cats(e)),
            _s(e, "description"),
            _s(e, "link"),
            _s(e, "source"),
        ])
    return output.getvalue()


# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@300;400;500;600;700&display=swap');

.stApp { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

/* Hide default Streamlit elements for cleaner look */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
div[data-testid="stDecoration"] {display: none;}

.main-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.6rem;
    margin-bottom: -0.3rem;
    line-height: 1.2;
    letter-spacing: -0.02em;
}
.main-title .highlight {
    background: linear-gradient(135deg, #7c6aff, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.subtitle {
    color: #8888a0;
    font-size: 0.78rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 1rem;
    font-weight: 400;
}

/* Stats — glassmorphism */
.stat-box {
    background: rgba(22, 22, 31, 0.7);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(124, 106, 255, 0.12);
    border-radius: 16px;
    padding: 0.9rem 1rem;
    text-align: center;
    transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.stat-box:hover {
    border-color: rgba(124, 106, 255, 0.3);
    transform: translateY(-1px);
    box-shadow: 0 8px 24px rgba(124, 106, 255, 0.1);
}
.stat-value {
    font-size: 1.7rem;
    font-weight: 700;
    background: linear-gradient(135deg, #7c6aff, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.2;
}
.stat-label {
    font-size: 0.68rem;
    color: #8888a0;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 500;
}

/* Event cards — Apple-quality glassmorphism */
.event-card {
    background: rgba(22, 22, 31, 0.65);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    padding: 0.9rem 1.1rem 0.7rem;
    margin-bottom: 0.25rem;
    transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    display: flex;
    flex-direction: column;
}
.event-card:hover {
    border-color: rgba(124, 106, 255, 0.25);
    box-shadow: 0 8px 32px rgba(124, 106, 255, 0.08);
    transform: translateY(-2px);
}
.event-card-past {
    background: rgba(18, 18, 26, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.03);
    border-radius: 14px;
    padding: 0.8rem 1.2rem;
    margin-bottom: 0.3rem;
    opacity: 0.6;
    transition: opacity 0.2s;
}
.event-card-past:hover { opacity: 0.8; }
.event-title {
    font-size: 0.98rem;
    font-weight: 600;
    color: #f0f0f8;
    margin-bottom: 0.15rem;
    letter-spacing: -0.01em;
    line-height: 1.3;
}
.event-meta {
    color: #8888a0;
    font-size: 0.82rem;
    margin-bottom: 0.2rem;
}
.event-venue { color: #a78bfa; font-weight: 500; font-size: 0.82rem; }
.event-datetime {
    color: #9999b0;
    font-size: 0.78rem;
    font-weight: 500;
    margin: 0.2rem 0;
    padding: 0;
}
.event-desc {
    color: #c0c0d4;
    font-size: 0.82rem;
    line-height: 1.55;
    margin-top: 0.35rem;
    margin-bottom: 0.3rem;
    flex: 1;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
    max-height: 4.1em;
}
.event-footer {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    align-items: center;
    margin-top: auto;
    padding-top: 0.5rem;
}
.price-tag {
    background: rgba(104, 211, 145, 0.12);
    color: #68d391;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}
/* Info pills — compact metadata tags */
.info-pill {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.06);
    color: #9999b0;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 500;
    white-space: nowrap;
}
.price-pill {
    background: rgba(104, 211, 145, 0.08);
    border-color: rgba(104, 211, 145, 0.15);
    color: #68d391;
}
/* Compact action icons row inside card */
.card-actions {
    display: flex;
    gap: 1px;
    margin-top: 0.4rem;
    padding-top: 0.35rem;
    border-top: 1px solid rgba(255, 255, 255, 0.04);
}
.card-actions a {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 3px;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.68rem;
    font-weight: 500;
    color: #6e6e88;
    text-decoration: none;
    background: transparent;
    border: 1px solid transparent;
    transition: all 0.2s ease;
    white-space: nowrap;
}
.card-actions a:hover {
    color: #a78bfa;
    background: rgba(124, 106, 255, 0.08);
    border-color: rgba(124, 106, 255, 0.12);
}
.card-actions a:first-child {
    color: #a78bfa;
    font-weight: 600;
}
.month-header {
    font-family: 'Playfair Display', serif;
    font-size: 1.4rem;
    color: #f0f0f8;
    margin-top: 2rem;
    margin-bottom: 0.8rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    letter-spacing: -0.01em;
}

/* Spotlight — gradient glass */
.spotlight-card {
    background: linear-gradient(135deg, rgba(26, 26, 46, 0.8), rgba(22, 33, 62, 0.8));
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(124, 106, 255, 0.2);
    border-radius: 18px;
    padding: 1.2rem 1.4rem;
    height: 100%;
    transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.spotlight-card:hover {
    border-color: rgba(124, 106, 255, 0.4);
    box-shadow: 0 12px 40px rgba(124, 106, 255, 0.12);
    transform: translateY(-3px);
    cursor: pointer;
}
.spotlight-label {
    color: #a78bfa;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    margin-bottom: 0.5rem;
}

/* Coming up next — compact card grid */
.coming-up-card {
    background: rgba(18, 18, 26, 0.6);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 0.75rem 0.9rem;
    transition: all 0.25s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    height: 100%;
    display: flex;
    flex-direction: column;
}
.coming-up-card:hover {
    border-color: rgba(124, 106, 255, 0.25);
    background: rgba(22, 22, 36, 0.85);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(124, 106, 255, 0.08);
}
.coming-up-date-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(124, 106, 255, 0.1);
    color: #a78bfa;
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 600;
    margin-bottom: 0.4rem;
    width: fit-content;
}
.coming-up-title {
    font-weight: 600;
    color: #f0f0f8;
    font-size: 0.88rem;
    line-height: 1.3;
    margin-bottom: 0.25rem;
}
.coming-up-venue {
    color: #a78bfa;
    font-size: 0.76rem;
    font-weight: 500;
}
.coming-up-meta {
    color: #6e6e88;
    font-size: 0.72rem;
    margin-top: auto;
    padding-top: 0.35rem;
}

/* Category chip used in filter bar */
.cat-chip {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    margin-right: 4px;
    margin-bottom: 4px;
}
/* Category chip row — horizontal scroll on overflow */
.chip-row {
    display: flex;
    gap: 4px;
    overflow-x: auto;
    padding-bottom: 4px;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
}
.chip-row::-webkit-scrollbar { display: none; }

div[data-testid="stHorizontalBlock"] > div { padding: 0 0.3rem; }

/* Streamlit button styling — Apple-like */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 500 !important;
    font-size: 0.75rem !important;
    padding: 0.35rem 0.5rem !important;
    transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    letter-spacing: 0.01em !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(124, 106, 255, 0.15) !important;
}

/* Make link buttons match */
.stLinkButton > a {
    font-size: 0.75rem !important;
    padding: 0.35rem 0.5rem !important;
    border-radius: 12px !important;
    transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    white-space: nowrap !important;
}
.stLinkButton > a:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(124, 106, 255, 0.12) !important;
}

/* Selectbox styling */
.stSelectbox > div > div {
    border-radius: 12px !important;
}

/* Text input */
.stTextInput > div > div > input {
    border-radius: 12px !important;
}

/* Past events section */
.past-label {
    color: #55556a;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
}

/* Export section */
.export-section {
    background: rgba(22, 22, 31, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 1rem 1.3rem;
    margin-bottom: 1rem;
}

/* Download button */
.stDownloadButton > button {
    border-radius: 12px !important;
}

/* Expander */
.streamlit-expanderHeader {
    border-radius: 14px !important;
}
</style>
""", unsafe_allow_html=True)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    data = load_events()
    all_events = data.get("events", [])
    sources = data.get("sources", [])
    last_updated = data.get("last_updated", "")

    # ── Split into current and past events ────────────────────────────────
    current_events = [e for e in all_events if is_current_or_future(e)]
    past_events = [e for e in all_events if is_past(e)]
    past_events.sort(key=lambda e: _s(e, "date_start"), reverse=True)

    # ── Initialize session state ────────────────────────────────────────
    if "selected_ids" not in st.session_state:
        st.session_state.selected_ids = set()
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    if "active_category" not in st.session_state:
        st.session_state.active_category = "all"

    # ── Header ───────────────────────────────────────────────────────────
    col_title, col_spacer, col_s1, col_s2, col_s3, col_refresh = st.columns([4, 0.5, 1, 1, 1, 1])
    with col_title:
        st.markdown('<div class="main-title">Philly<span class="highlight">Culture</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle">Your guide to Philadelphia\'s arts &amp; culture</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.85rem;color:#a0aec0;margin-top:2px">Created by <a href="https://eugendimant.github.io/" target="_blank" style="color:#4fd1c5;text-decoration:none">Dr. Eugen Dimant</a></div>', unsafe_allow_html=True)
    with col_s1:
        st.markdown(f'<div class="stat-box"><div class="stat-value">{len(current_events)}</div><div class="stat-label">Events</div></div>', unsafe_allow_html=True)
    with col_s2:
        now_playing = sum(1 for e in current_events if is_happening_now(e)
                         and (e.get("venue") or "").strip())
        st.markdown(f'<div class="stat-box"><div class="stat-value">{now_playing}</div><div class="stat-label">Happening Today</div></div>', unsafe_allow_html=True)
    with col_s3:
        st.markdown(f'<div class="stat-box"><div class="stat-value">{len(sources)}</div><div class="stat-label">Sources</div></div>', unsafe_allow_html=True)
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.session_state.last_refresh = datetime.now()
            st.rerun()

    # ── Last refreshed line ──────────────────────────────────────────────
    refresh_str = st.session_state.last_refresh.strftime("%b %d, %Y at %I:%M %p")
    st.caption(f"Last refreshed: {refresh_str}")

    st.divider()

    # ── Search bar (full width, prominent) ──────────────────────────────
    search = st.text_input("Search", placeholder="🔍  Search events, venues, artists...", label_visibility="collapsed")

    # ── Compact filter row: venue, when, sort ────────────────────────────
    col_venue, col_time, col_sort = st.columns([2, 2, 1])

    with col_venue:
        # Build venue list — sanitize to ensure no corrupted entries
        all_venues = set()
        for e in current_events:
            v = _s(e, "venue").strip()
            if not v:
                continue
            # Skip venues that look corrupted (time embedded, junk text)
            if _re.match(r'^\d{1,2}:\d{2}', v):
                continue  # Time-as-venue corruption
            if 'p.m.' in v.lower() or 'a.m.' in v.lower():
                continue
            if 'check back' in v.lower() or 'availability' in v.lower():
                continue
            if len(v) < 3:
                continue
            all_venues.add(v)
        all_venues = sorted(all_venues)
        venue_filter = st.selectbox(
            "Venue",
            ["all"] + all_venues,
            format_func=lambda x: "📍 All Venues" if x == "all" else x,
            label_visibility="collapsed",
        )

    with col_time:
        time_filter = st.selectbox(
            "Time",
            ["all", "today", "this_week", "this_weekend", "this_month", "free"],
            format_func=lambda x: {
                "all": "📅 All Dates",
                "today": "📌 Today",
                "this_week": "📅 This Week",
                "this_weekend": "🎉 This Weekend",
                "this_month": "📅 This Month",
                "free": "🆓 Free Events",
            }.get(x, x),
            label_visibility="collapsed",
        )

    with col_sort:
        sort_by = st.selectbox(
            "Sort",
            ["date", "name", "venue"],
            format_func=lambda x: {"date": "↕ Date", "name": "↕ Name", "venue": "↕ Venue"}.get(x, x),
            label_visibility="collapsed",
        )

    # ── Category chips (the primary way to filter by category) ────────
    all_cats = []
    for e in current_events:
        all_cats.extend(_cats(e))
    cat_counts = Counter(all_cats)
    if cat_counts:
        visible_cats = [c for c in ["theater", "musical", "jazz", "classical", "ballet", "dance", "opera", "concert", "exhibition", "lecture", "science", "performance"] if cat_counts.get(c, 0) > 0]
        all_chips = ["all"] + visible_cats
        # Use two rows if more than 8 chips to prevent overflow
        row_size = max(6, (len(all_chips) + 1) // 2) if len(all_chips) > 8 else len(all_chips)
        row1 = all_chips[:row_size]
        row2 = all_chips[row_size:]
        chip_cols = st.columns(len(row1))
        for i, cat in enumerate(row1):
            with chip_cols[i]:
                if cat == "all":
                    label = "All"
                else:
                    icon = CAT_ICONS.get(cat, "")
                    count = cat_counts[cat]
                    label = f"{icon} {cat.capitalize()} {count}"
                btn_type = "primary" if st.session_state.active_category == cat else "secondary"
                if st.button(label, use_container_width=True, type=btn_type, key=f"chip_{cat}"):
                    st.session_state.active_category = cat
                    st.rerun()
        if row2:
            chip_cols2 = st.columns(len(row2))
            for i, cat in enumerate(row2):
                with chip_cols2[i]:
                    icon = CAT_ICONS.get(cat, "")
                    count = cat_counts[cat]
                    label = f"{icon} {cat.capitalize()} {count}"
                    btn_type = "primary" if st.session_state.active_category == cat else "secondary"
                    if st.button(label, use_container_width=True, type=btn_type, key=f"chip_{cat}"):
                        st.session_state.active_category = cat
                        st.rerun()

    # ── Apply filters (only to current/future events) ─────────────────────
    filtered = list(current_events)

    active_cat = st.session_state.active_category
    if active_cat != "all":
        filtered = [e for e in filtered if active_cat in _cats(e)]

    if venue_filter != "all":
        filtered = [e for e in filtered if _s(e, "venue") == venue_filter]

    if time_filter == "today":
        filtered = [e for e in filtered if is_happening_now(e)]
    elif time_filter == "this_week":
        filtered = [e for e in filtered if is_this_week(e)]
    elif time_filter == "this_weekend":
        filtered = [e for e in filtered if is_this_weekend(e)]
    elif time_filter == "this_month":
        filtered = [e for e in filtered if _is_this_month(e)]
    elif time_filter == "free":
        filtered = [e for e in filtered if is_free(e)]

    if search:
        q = search.lower()
        filtered = [
            e for e in filtered
            if q in _s(e, "title").lower()
            or q in _s(e, "venue").lower()
            or q in _s(e, "description").lower()
            or q in _s(e, "source").lower()
            or any(q in c for c in _cats(e))
        ]

    if sort_by == "name":
        filtered.sort(key=lambda e: _s(e, "title").lower())
    elif sort_by == "venue":
        filtered.sort(key=lambda e: _s(e, "venue").lower())
    else:
        def _sort_date(e):
            """Ongoing events (start in past, end in future) sort by today's date, tiebreak by end date."""
            s = _s(e, "date_start", "9999")
            today = today_str()
            end = _s(e, "date_end") or s
            if s < today and end >= today:
                return (today, end)  # ongoing — sort with today's events, earlier end first
            return (s, end)
        filtered.sort(key=_sort_date)

    # ── Spotlight: What's Happening Today ──────────────────────────────────
    # Only show events with a real description and venue — no half-baked cards
    tonight = [e for e in filtered if is_happening_now(e)
               and (e.get("description") or "").strip()
               and (e.get("venue") or "").strip()]
    if tonight:
        st.markdown("#### 🔴 Happening Today")
        num_cols = min(len(tonight), 4)
        cols = st.columns(num_cols if num_cols >= 2 else 2)
        for i, event in enumerate(tonight[:4]):
            with cols[i % num_cols]:
                cats = _cats(event)
                badge = category_badge_html(cats[0]) if cats else ""
                price_html = f' · {_h(_s(event, "price"))}' if _s(event, "price") else ""
                link = _s(event, "link") or _s(event, "source_url") or "#"
                date_disp = _s(event, "date_display") or _s(event, "date_start", "")
                spot_desc = event_description(event, max_sentences=2)
                st.markdown(f"""
                <a href="{link}" target="_blank" rel="noopener" style="text-decoration:none;color:inherit;display:block">
                <div class="spotlight-card">
                    <div class="spotlight-label">Happening Today</div>
                    <div class="event-title" style="font-size:1rem">{_h(_s(event, 'title'))}</div>
                    <div style="color:#8888a0;font-size:0.78rem;margin:0.2rem 0">
                        <span class="event-venue">{_h(_s(event, 'venue')) or 'N/A'}</span> · {_h(date_disp) or 'N/A'}{price_html}
                    </div>
                    <div class="event-desc" style="font-size:0.8rem;margin-top:0.3rem;-webkit-line-clamp:2;max-height:2.7em">{spot_desc}</div>
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-top:0.5rem">
                        {badge}
                        <span style="font-size:0.75rem;color:#a78bfa;font-weight:500">Get Tickets →</span>
                    </div>
                </div>
                </a>
                """, unsafe_allow_html=True)
        st.markdown("")

    # ── Coming Up Next section ────────────────────────────────────────────
    # Only show events with dates and venue for the "coming up" feature
    upcoming = [e for e in filtered if not is_happening_now(e)
                and e.get("date_start") and (e.get("venue") or "").strip()]
    upcoming.sort(key=lambda e: _s(e, "date_start", "9999"))
    next_up = upcoming[:3]
    if next_up:
        st.markdown("#### Coming Up Next")
        cols = st.columns(3)
        for i, event in enumerate(next_up):
            with cols[i]:
                urg = urgency_badge(event)
                link = _s(event, "link") or _s(event, "source_url")
                time_str = _s(event, "time")
                price_str = _s(event, "price")
                date_disp = _s(event, "date_display") or _s(event, "date_start", "")
                venue = _s(event, "venue")
                # Bottom meta line
                meta_parts = []
                if time_str:
                    meta_parts.append(_h(time_str))
                if price_str:
                    meta_parts.append(_h(price_str))
                meta_html = " · ".join(meta_parts) if meta_parts else ""
                wrapper_open = f'<a href="{link}" target="_blank" rel="noopener" style="text-decoration:none;color:inherit;display:block">' if link else ''
                wrapper_close = '</a>' if link else ''
                st.markdown(f"""
                {wrapper_open}
                <div class="coming-up-card">
                    <div class="coming-up-date-badge">{_h(date_disp) or 'N/A'} {urg}</div>
                    <div class="coming-up-title">{_h(_s(event, 'title'))}</div>
                    <div class="coming-up-venue">{_h(venue) if venue else 'N/A'}</div>
                    {'<div class="coming-up-meta">' + meta_html + '</div>' if meta_html else ''}
                </div>
                {wrapper_close}
                """, unsafe_allow_html=True)
        st.markdown("")

    st.divider()

    # ── Export bar (for selected events) ──────────────────────────────────
    selected_count = len(st.session_state.selected_ids)
    export_col1, export_col2, export_col3, export_col4 = st.columns([2, 1, 1, 1])
    with export_col1:
        st.caption(f"Showing {len(filtered)} of {len(current_events)} events  |  {selected_count} selected for export")
    with export_col2:
        if st.button("☑️ Select All Visible", use_container_width=True):
            for e in filtered:
                st.session_state.selected_ids.add(_s(e, "id"))
            st.rerun()
    with export_col3:
        if st.button("⬜ Clear Selection", use_container_width=True):
            st.session_state.selected_ids.clear()
            st.rerun()
    with export_col4:
        if selected_count > 0:
            selected_events = [e for e in all_events if _s(e, "id") in st.session_state.selected_ids]
            csv_data = events_to_csv(selected_events)
            st.download_button(
                "📥 Export CSV",
                csv_data,
                file_name="philly_culture_events.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.download_button(
                "📥 Export All CSV",
                events_to_csv(filtered),
                file_name="philly_culture_all_events.csv",
                mime="text/csv",
                use_container_width=True,
            )

    # ── Event listing grouped by month ───────────────────────────────────
    if not filtered:
        # Build a summary of active filters for the empty state message
        active_filters = []
        if active_cat != "all":
            active_filters.append(f"category <strong>{_h(active_cat)}</strong>")
        if venue_filter != "all":
            active_filters.append(f"venue <strong>{_h(venue_filter)}</strong>")
        if time_filter != "all":
            time_labels = {"today": "Today", "this_week": "This Week", "this_weekend": "This Weekend", "this_month": "This Month", "free": "Free"}
            active_filters.append(f"<strong>{time_labels.get(time_filter, time_filter)}</strong>")
        if search:
            active_filters.append(f'search "<strong>{_h(search)}</strong>"')
        filter_summary = " + ".join(active_filters) if active_filters else "your current filters"
        st.markdown(f"""
        <div style="text-align:center;padding:3rem;color:#8888a0">
            <div style="font-size:3rem;margin-bottom:1rem">🔍</div>
            <h3 style="color:#e8e8f0;margin-bottom:0.5rem">No events match your filters</h3>
            <p>No results for {filter_summary}.</p>
            <p style="font-size:0.85rem">There are <strong>{len(current_events)}</strong> upcoming events total — try broadening your filters.</p>
        </div>
        """, unsafe_allow_html=True)
        if active_cat != "all" or venue_filter != "all" or time_filter != "all" or search:
            if st.button("Clear All Filters", type="primary"):
                st.session_state.active_category = "all"
                st.rerun()
    else:
        current_month = None
        # Render all events in a consistent 2-column grid
        col_idx = 0
        cols = None
        for event in filtered:
            month = effective_month_key(event)
            if month != current_month:
                # New month header — force new row
                current_month = month
                col_idx = 0
                cols = None
                st.markdown(f'<div class="month-header">{month}</div>', unsafe_allow_html=True)

            # Start new 2-column row when needed
            if col_idx % 2 == 0:
                cols = st.columns(2)

            with cols[col_idx % 2]:
                _render_event_card(event, st)
            col_idx += 1

    # ── Past Events Archive ───────────────────────────────────────────────
    if past_events:
        st.divider()
        with st.expander(f"📜 Past Events Archive ({len(past_events)} events)", expanded=False):
            st.caption("These events have already ended. Kept for reference.")
            for event in past_events:
                badges = "".join(category_badge_html(c) for c in _cats(event))
                price_html = f'<span class="price-tag">{_h(_s(event, "price"))}</span>' if _s(event, "price") else ""
                date_disp = _s(event, "date_display") or _s(event, "date_start", "")
                st.markdown(f"""
                <div class="event-card-past">
                    <div style="font-size:1rem;font-weight:600;color:#8888a0">{_h(_s(event, 'title'))}</div>
                    <div class="event-meta">
                        <span style="color:#6a6a8a">{_h(_s(event, 'venue')) or 'N/A'}</span> · {_h(date_disp) or 'N/A'}
                        {' · ' + price_html if _s(event, 'price') else ''}
                    </div>
                    <div style="margin-top:0.3rem">{badges}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── Sidebar: Analytics + Venue Explorer ───────────────────────────────
    with st.sidebar:
        st.markdown("### 📊 Analytics")
        st.markdown(f"**{len(current_events)}** upcoming · **{len(past_events)}** archived · **{len(sources)}** sources")
        st.markdown("")

        # Category breakdown
        st.markdown("**By Category**")
        for cat in sorted(cat_counts.keys(), key=lambda c: -cat_counts.get(c, 0)):
            color = CAT_COLORS.get(cat, "#a0aec0")
            icon = CAT_ICONS.get(cat, "")
            pct = cat_counts[cat] / max(len(current_events), 1) * 100
            st.markdown(
                f'<div style="margin-bottom:6px">'
                f'<span style="color:{color}">{icon} {cat.capitalize()}</span> '
                f'<span style="color:#8888a0">— {cat_counts[cat]} events</span>'
                f'<div style="background:#23233080;border-radius:4px;height:6px;margin-top:3px">'
                f'<div style="background:{color};width:{pct}%;height:100%;border-radius:4px"></div>'
                f'</div></div>',
                unsafe_allow_html=True
            )

        st.markdown("")
        st.markdown("**Top Venues**")
        venue_counts = Counter(_s(e, "venue", "Unknown") for e in current_events)
        for venue, count in venue_counts.most_common(8):
            # Skip corrupted venue entries in sidebar too
            if _re.match(r'^\d{1,2}:\d{2}', venue) or 'p.m.' in venue.lower():
                continue
            st.markdown(f'<div style="color:#e8e8f0;font-size:0.9rem">{_h(venue)} <span style="color:#7c6aff;font-weight:600">({count})</span></div>', unsafe_allow_html=True)

        st.markdown("")
        st.markdown("**Monthly Distribution**")
        month_counts = Counter(get_month_key(_s(e, "date_start")) for e in current_events)
        def _month_sort_key(m):
            try:
                return datetime.strptime(m, "%B %Y")
            except Exception:
                return datetime.max
        for month in sorted(month_counts.keys(), key=_month_sort_key):
            count = month_counts[month]
            bar_w = count / max(month_counts.values(), 1) * 100
            st.markdown(
                f'<div style="margin-bottom:4px">'
                f'<span style="color:#e8e8f0;font-size:0.85rem">{month}</span> '
                f'<span style="color:#7c6aff;font-weight:600">{count}</span>'
                f'<div style="background:#23233080;border-radius:3px;height:5px;margin-top:2px">'
                f'<div style="background:#7c6aff;width:{bar_w}%;height:100%;border-radius:3px"></div>'
                f'</div></div>',
                unsafe_allow_html=True
            )

        st.markdown("")
        st.markdown("**Data Sources**")
        for source in sorted(sources):
            src_count = sum(1 for e in current_events if _s(e, "source") == source)
            st.markdown(f'<div style="color:#8888a0;font-size:0.85rem">• {_h(source)} <span style="color:#7c6aff">({src_count})</span></div>', unsafe_allow_html=True)

    # ── Footer ───────────────────────────────────────────────────────────
    st.divider()
    st.markdown(f"""
    <div style="text-align:center;color:#55556a;padding:1rem;font-size:0.85rem">
        <strong>PhillyCulture</strong> — Aggregating {len(sources)} Philadelphia performing arts sources<br>
        Data from verified public event listings. Not affiliated with any venue.
    </div>
    """, unsafe_allow_html=True)


def _render_event_card(event, st_ctx):
    """Render a single event card — compact, Apple-quality design."""
    eid = _s(event, "id")
    cats = _cats(event)
    # Show only first category badge to save space
    badge_html = category_badge_html(cats[0]) if cats else ""
    price = _s(event, "price")
    time_str = _s(event, "time")
    urg = urgency_badge(event)
    desc = event_description(event)
    link = _s(event, "link") or _s(event, "source_url")
    venue = _s(event, "venue")
    date_disp = _s(event, "date_display") or _s(event, "date_start", "")

    # Build compact meta line: venue · date · time
    # Show "N/A" for missing venue/date — never leave blank or guess
    meta_parts = []
    meta_parts.append(f'<span class="event-venue">{_h(venue) if venue else "N/A"}</span>')
    if date_disp:
        meta_parts.append(_h(date_disp))
    if time_str:
        meta_parts.append(_h(time_str))
    meta_line = " · ".join(meta_parts)

    # Price tag (separate for visual emphasis)
    price_html = ""
    if price:
        price_html = f'<span class="price-tag" style="margin-left:6px">{_h(price)}</span>'

    # Action links — compact
    action_links = []
    if link:
        action_links.append(f'<a href="{link}" target="_blank">Tickets</a>')
    action_links.append(f'<a href="{gcal_url(event)}" target="_blank">Cal</a>')
    action_links.append(f'<a href="{maps_url(event)}" target="_blank">Map</a>')
    action_links.append(f'<a href="{share_url(event)}" target="_blank">Share</a>')
    actions_html = "".join(action_links)

    st_ctx.markdown(f"""
    <div class="event-card">
        <div class="event-title">{_h(_s(event, 'title'))}{urg}</div>
        <div class="event-datetime">{meta_line}{price_html}</div>
        <div class="event-desc">{_h(desc)}</div>
        <div style="display:flex;align-items:center;justify-content:space-between;margin-top:auto">
            <div>{badge_html}</div>
            <div class="card-actions" style="border:0;margin:0;padding:0">{actions_html}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Select button (needs Streamlit interactivity)
    is_selected = eid in st.session_state.selected_ids
    sel_label = "✅ Selected" if is_selected else "☐ Select"
    if st_ctx.button(sel_label, key=f"sel_{eid}", use_container_width=True):
        if is_selected:
            st.session_state.selected_ids.discard(eid)
        else:
            st.session_state.selected_ids.add(eid)
        st.rerun()


if __name__ == "__main__":
    main()
