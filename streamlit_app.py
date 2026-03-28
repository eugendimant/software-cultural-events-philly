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
    """Filter out scraper artifacts and junk entries at display time."""
    if not isinstance(event, dict):
        return False
    title = (event.get("title") or "").strip()
    if not title or len(title) < 3:
        return False
    title_low = title.lower().strip()
    # Reject exact-match junk titles (instruments, nav items, etc.)
    if title_low in _JUNK_EXACT_TITLES:
        return False
    if any(phrase in title_low for phrase in _JUNK_PHRASES):
        return False
    # Must have at least a plausible title (some alpha characters)
    if sum(1 for c in title if c.isalpha()) < 3:
        return False
    return True

def _sanitize_event(event):
    """Clean up event fields: replace None with defaults, strip garbage display text."""
    if not isinstance(event, dict):
        return event
    # Clean garbage date_display
    dd = (event.get("date_display") or "")
    if "start date" in dd.lower() or "e.g." in dd.lower():
        event["date_display"] = ""
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

            # Strategy 2: Partial match — but ONLY if:
            #   - The shorter string is at least 60% of the longer string's length
            #   - The event and seed are from the same source
            #   This prevents "Trumpet" matching "Trumpeter James McGovern..."
            if needs_desc or link_is_generic:
                for seed_key, seed_data in _SEED_LOOKUP.items():
                    if len(seed_key) < 10 or len(norm) < 10:
                        continue
                    # Check substring match
                    if not (seed_key in norm or norm in seed_key):
                        continue
                    # Require similar length (prevent short words matching long titles)
                    shorter = min(len(norm), len(seed_key))
                    longer = max(len(norm), len(seed_key))
                    if shorter < longer * 0.6:
                        continue
                    # Require same source to prevent cross-venue contamination
                    if seed_data["source"] and ev_source and seed_data["source"] != ev_source:
                        continue
                    if needs_desc and seed_data["description"]:
                        event["description"] = seed_data["description"]
                        needs_desc = False
                    if link_is_generic and seed_data["link"]:
                        event["link"] = seed_data["link"]
                        link_is_generic = False
                    break

        # Strategy 3: For events that STILL have generic links, try
        # to enrich the link from known seed events for the same source
        if link_is_generic:
            source = event.get("source", "")
            # For venues where we know the URL pattern includes the event title,
            # try to construct a plausible direct link
            title_slug = _re.sub(r'[^a-z0-9]+', '-', (event.get("title") or "").lower()).strip('-')
            if title_slug and source == "Ensemble Arts Philly":
                event["link"] = f"https://www.ensembleartsphilly.org/tickets-and-events/events/{title_slug}"
            elif title_slug and source == "Philadelphia Orchestra":
                event["link"] = f"https://www.ensembleartsphilly.org/tickets-and-events/philadelphia-orchestra/2025-26-season/{title_slug}"
            elif title_slug and source == "Penn Live Arts":
                event["link"] = f"https://pennlivearts.org/event/{title_slug}"
            elif title_slug and source == "Arden Theatre":
                event["link"] = f"https://ardentheatre.org/productions/{title_slug}/"
            elif title_slug and source == "The Wilma Theater":
                event["link"] = f"https://www.wilmatheater.org/whats-on/{title_slug}/"
            elif title_slug and source == "Opera Philadelphia":
                event["link"] = f"https://www.operaphila.org/whats-on/events/{title_slug}/"
            elif title_slug and source == "FringeArts":
                event["link"] = f"https://fringearts.com/event/{title_slug}/"
            elif title_slug and source == "Walnut Street Theatre":
                event["link"] = f"https://www.walnutstreettheatre.org/season/{title_slug}"
            elif title_slug and source == "Philadelphia Theatre Company":
                event["link"] = f"https://www.philatheatreco.org/{title_slug}"
            # Note: Chris' Jazz Cafe uses numeric IDs — can't guess URLs from titles.
            # Those events keep the listing page URL (best we can do without the JSON API).

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
    # Always merge seed events so curated exhibition/lecture/science data appears
    # even if the scraper hasn't been re-run yet
    if FALLBACK_EVENTS:
        existing_keys = set()
        for e in data.get("events", []):
            norm = _re.sub(r'\s+', ' ', e.get("title", "").lower().strip())
            existing_keys.add((e.get("source", ""), norm))
        today = datetime.now().strftime("%Y-%m-%d")
        for seed_ev in FALLBACK_EVENTS:
            norm = _re.sub(r'\s+', ' ', seed_ev.get("title", "").lower().strip())
            key = (seed_ev.get("source", ""), norm)
            end = seed_ev.get("date_end") or seed_ev.get("date_start", "")
            if key not in existing_keys and end >= today:
                data["events"].append(seed_ev)
                existing_keys.add(key)
        # Update sources list
        data["sources"] = sorted({e.get("source", "") for e in data["events"] if e.get("source")})
    # Sanitize: filter junk, clean fields
    data["events"] = [_sanitize_event(e) for e in data.get("events", []) if _is_valid_event(e)]
    # Fix cross-venue contamination (bad data from previous scraper runs)
    data["events"] = _fix_cross_venue_contamination(data["events"])
    # Enrich: fill missing descriptions from seed data
    data["events"] = _enrich_descriptions(data["events"])
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
        # No description was scraped — build a richer fallback from event metadata
        title = _s(event, "title")
        venue = _s(event, "venue")
        source = _s(event, "source")
        cats = _cats(event)
        price = _s(event, "price")
        time_str = _s(event, "time")
        primary_cat = cats[0] if cats else ""

        # Try to extract performer info from the title
        # Common patterns: "Artist Name and His/Her Quintet", "Pianist Name Trio"
        performer = ""
        title_parts = title.split(":")
        if len(title_parts) > 1:
            performer = title_parts[0].strip()

        cat_labels = {
            "jazz": "Live jazz", "classical": "Classical music",
            "musical": "Musical theater", "theater": "Live theater",
            "ballet": "Ballet", "dance": "Dance performance",
            "opera": "Opera", "concert": "Live concert",
            "exhibition": "Exhibition", "lecture": "Lecture",
            "science": "Science event",
            "performance": "Live performance",
        }
        cat_label = cat_labels.get(primary_cat, "Live performance")

        # Build a richer description based on venue context
        venue_lower = venue.lower()
        if "chris" in venue_lower and "jazz" in venue_lower:
            desc = f"{title} — live jazz at Chris' Jazz Cafe, Philadelphia's premier jazz club at 1421 Sansom Street."
            if time_str:
                desc += f" Show at {time_str}."
            if price:
                desc += f" {'Free admission' if price.lower() == 'free' else f'Tickets from {price}'}."
        elif "south jazz" in venue_lower:
            desc = f"{title} — live jazz and dinner at South Jazz Kitchen."
            if time_str:
                desc += f" Show at {time_str}."
        elif "world cafe" in venue_lower:
            desc = f"{title} at World Cafe Live — Philadelphia's eclectic live music venue."
            if time_str:
                desc += f" Doors at {time_str}."
        elif "city winery" in venue_lower:
            desc = f"{title} at City Winery Philadelphia — intimate live music with wine and dining."
        elif "kimmel" in venue_lower or "marian anderson" in venue_lower:
            desc = f"{cat_label} at the Kimmel Cultural Campus."
            if performer:
                desc = f"{performer} performs at the Kimmel Cultural Campus."
        elif "academy of music" in venue_lower:
            desc = f"{cat_label} at the historic Academy of Music."
        elif "philadelphia museum of art" in venue_lower or "philamuseum" in venue_lower:
            desc = f"{title} at the Philadelphia Museum of Art."
        elif "barnes" in venue_lower:
            desc = f"{title} at the Barnes Foundation — home to one of the world's greatest collections of Impressionist and Post-Impressionist art."
        elif "franklin institute" in venue_lower:
            desc = f"{title} at The Franklin Institute — Philadelphia's premier science museum."
        elif "penn museum" in venue_lower:
            desc = f"{title} at the Penn Museum — world-renowned archaeology and anthropology collections."
        elif "academy of natural" in venue_lower or "ansp" in venue_lower:
            desc = f"{title} at the Academy of Natural Sciences — America's oldest natural history museum."
        elif "mutter" in venue_lower or "mütter" in venue_lower:
            desc = f"{title} at the Mütter Museum — Philadelphia's museum of medical history."
        elif "science history" in venue_lower:
            desc = f"{title} at the Science History Institute — exploring the history of science and its impact."
        elif "national mechanics" in venue_lower:
            desc = f"{title} at National Mechanics bar in Old City."
        elif "sofar" in venue_lower:
            desc = f"{title} — an intimate Sofar Sounds concert at a secret Philadelphia venue, revealed the day before the show."
        else:
            desc = f"{cat_label} at {venue}." if venue else f"{cat_label} in Philadelphia."
            if time_str:
                desc += f" Show at {time_str}."

        if price and "ticket" not in desc.lower():
            if price.lower() == "free":
                desc += " Free admission."
            else:
                desc += f" Tickets from {price}."

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
        now_playing = sum(1 for e in current_events if is_happening_now(e))
        st.markdown(f'<div class="stat-box"><div class="stat-value">{now_playing}</div><div class="stat-label">Now Playing</div></div>', unsafe_allow_html=True)
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
        all_venues = sorted({_s(e, "venue") for e in current_events if _s(e, "venue")})
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

    # ── Spotlight: What's Happening Now ───────────────────────────────────
    tonight = [e for e in filtered if is_happening_now(e)]
    if tonight:
        st.markdown("#### 🔴 Happening Now")
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
                    <div class="spotlight-label">Now Playing</div>
                    <div class="event-title" style="font-size:1rem">{_h(_s(event, 'title'))}</div>
                    <div style="color:#8888a0;font-size:0.78rem;margin:0.2rem 0">
                        <span class="event-venue">{_h(_s(event, 'venue'))}</span> · {_h(date_disp)}{price_html}
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
    upcoming = [e for e in filtered if not is_happening_now(e)]
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
                    <div class="coming-up-date-badge">{_h(date_disp)} {urg}</div>
                    <div class="coming-up-title">{_h(_s(event, 'title'))}</div>
                    <div class="coming-up-venue">{_h(venue)}</div>
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
                        <span style="color:#6a6a8a">{_h(_s(event, 'venue'))}</span> · {_h(date_disp)}
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
            st.markdown(f'<div style="color:#e8e8f0;font-size:0.9rem">{venue} <span style="color:#7c6aff;font-weight:600">({count})</span></div>', unsafe_allow_html=True)

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
            st.markdown(f'<div style="color:#8888a0;font-size:0.85rem">• {source} <span style="color:#7c6aff">({src_count})</span></div>', unsafe_allow_html=True)

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
    meta_parts = []
    if venue:
        meta_parts.append(f'<span class="event-venue">{_h(venue)}</span>')
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
