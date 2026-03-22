#!/usr/bin/env python3
"""
Philadelphia Cultural Events Scraper
Fetches events from verified Philadelphia cultural venues and outputs JSON.
"""

import json
import re
import sys
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def safe_get(url, timeout=20):
    try:
        r = SESSION.get(url, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  [WARN] Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def make_id(venue, title, date_str):
    raw = f"{venue}|{title}|{date_str}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def parse_price(text):
    if not text:
        return None
    m = re.search(r'\$[\d,.]+(?:\s*[-–]\s*\$[\d,.]+)?', text)
    return m.group(0) if m else None


# ---------------------------------------------------------------------------
# SCRAPERS — one per source
# ---------------------------------------------------------------------------

def scrape_ensemble_arts():
    """Ensemble Arts Philly — Kimmel Center, Academy of Music, Miller Theater."""
    events = []
    url = "https://www.ensembleartsphilly.org/tickets-and-events"
    r = safe_get(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    for card in soup.select("article, .event-card, .event-item, [class*='event'], [class*='Event']"):
        title_el = card.select_one("h2, h3, h4, .title, [class*='title'], [class*='Title']")
        date_el = card.select_one("time, .date, [class*='date'], [class*='Date']")
        venue_el = card.select_one(".venue, [class*='venue'], [class*='Venue'], [class*='location']")
        link_el = card.select_one("a[href]")
        price_el = card.select_one("[class*='price'], [class*='Price']")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = date_el.get_text(strip=True) if date_el else ""
        venue = venue_el.get_text(strip=True) if venue_el else "Kimmel Cultural Campus"
        link = urljoin(url, link_el["href"]) if link_el else url
        price = parse_price(price_el.get_text(strip=True)) if price_el else None
        events.append({
            "id": make_id("ensemble_arts", title, date_str),
            "title": title,
            "date_display": date_str,
            "venue": venue,
            "source": "Ensemble Arts Philly",
            "source_url": url,
            "link": link,
            "price": price,
            "categories": categorize(title, venue),
            "image": None,
        })
    print(f"  Ensemble Arts: {len(events)} events")
    return events


def scrape_philorch():
    """Philadelphia Orchestra."""
    events = []
    url = "https://philorch.ensembleartsphilly.org/tickets-and-events/events"
    r = safe_get(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    for card in soup.select("article, .event-card, .event-item, [class*='event'], [class*='Event'], .performance, [class*='concert']"):
        title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
        date_el = card.select_one("time, .date, [class*='date']")
        link_el = card.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = date_el.get_text(strip=True) if date_el else ""
        link = urljoin(url, link_el["href"]) if link_el else url
        events.append({
            "id": make_id("philorch", title, date_str),
            "title": title,
            "date_display": date_str,
            "venue": "Verizon Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": url,
            "link": link,
            "price": None,
            "categories": ["classical"],
            "image": None,
        })
    print(f"  Philadelphia Orchestra: {len(events)} events")
    return events


def scrape_theatre_philly():
    """Theatre Philadelphia — aggregator for all theater."""
    events = []
    url = "https://theatrephiladelphia.org/whats-on-stage"
    r = safe_get(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    for card in soup.select("article, .show-card, .show-item, [class*='show'], .views-row, .node--type-show"):
        title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
        date_el = card.select_one(".date, [class*='date'], .field--name-field-dates")
        venue_el = card.select_one(".venue, [class*='venue'], .field--name-field-venue, [class*='company']")
        link_el = card.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = date_el.get_text(strip=True) if date_el else ""
        venue = venue_el.get_text(strip=True) if venue_el else ""
        link = urljoin(url, link_el["href"]) if link_el else url
        events.append({
            "id": make_id("theatre_philly", title, date_str),
            "title": title,
            "date_display": date_str,
            "venue": venue,
            "source": "Theatre Philadelphia",
            "source_url": url,
            "link": link,
            "price": None,
            "categories": categorize(title, venue),
            "image": None,
        })
    print(f"  Theatre Philadelphia: {len(events)} events")
    return events


def scrape_penn_live_arts():
    """Penn Live Arts — dance, music, theater at UPenn."""
    events = []
    url = "https://pennlivearts.org/events/"
    r = safe_get(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    for card in soup.select("article, .event-card, [class*='event'], .performance-item, .views-row"):
        title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
        date_el = card.select_one("time, .date, [class*='date']")
        link_el = card.select_one("a[href]")
        genre_el = card.select_one("[class*='genre'], [class*='category'], [class*='type']")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = date_el.get_text(strip=True) if date_el else ""
        link = urljoin(url, link_el["href"]) if link_el else url
        genre_hint = genre_el.get_text(strip=True) if genre_el else ""
        events.append({
            "id": make_id("penn_live", title, date_str),
            "title": title,
            "date_display": date_str,
            "venue": "Penn Live Arts",
            "source": "Penn Live Arts",
            "source_url": url,
            "link": link,
            "price": None,
            "categories": categorize(title + " " + genre_hint, "Penn Live Arts"),
            "image": None,
        })
    print(f"  Penn Live Arts: {len(events)} events")
    return events


def scrape_opera_phila():
    """Opera Philadelphia."""
    events = []
    url = "https://www.operaphila.org/whats-on/events/"
    r = safe_get(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    for card in soup.select("article, .event-card, [class*='event'], [class*='Event'], .views-row"):
        title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
        date_el = card.select_one("time, .date, [class*='date']")
        venue_el = card.select_one(".venue, [class*='venue']")
        link_el = card.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = date_el.get_text(strip=True) if date_el else ""
        venue = venue_el.get_text(strip=True) if venue_el else "Academy of Music"
        link = urljoin(url, link_el["href"]) if link_el else url
        events.append({
            "id": make_id("opera_phila", title, date_str),
            "title": title,
            "date_display": date_str,
            "venue": venue,
            "source": "Opera Philadelphia",
            "source_url": url,
            "link": link,
            "price": None,
            "categories": ["opera", "classical"],
            "image": None,
        })
    print(f"  Opera Philadelphia: {len(events)} events")
    return events


def scrape_walnut_street():
    """Walnut Street Theatre."""
    events = []
    url = "https://www.walnutstreettheatre.org/season/mainstage.2026.php"
    r = safe_get(url)
    if not r:
        # Try alternate URL pattern
        r = safe_get("https://www.walnutstreettheatre.org/season/calendar.php")
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    for card in soup.select("article, .show, [class*='show'], [class*='production'], .season-item, table tr"):
        title_el = card.select_one("h2, h3, h4, .title, [class*='title'], a strong, a b")
        date_el = card.select_one(".date, [class*='date'], .run-dates, td:nth-child(2)")
        link_el = card.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = date_el.get_text(strip=True) if date_el else ""
        link = urljoin(url, link_el["href"]) if link_el else url
        events.append({
            "id": make_id("walnut", title, date_str),
            "title": title,
            "date_display": date_str,
            "venue": "Walnut Street Theatre",
            "source": "Walnut Street Theatre",
            "source_url": url,
            "link": link,
            "price": None,
            "categories": categorize(title, "Walnut Street Theatre"),
            "image": None,
        })
    print(f"  Walnut Street Theatre: {len(events)} events")
    return events


def scrape_fringe_arts():
    """FringeArts — contemporary performance."""
    events = []
    url = "https://fringearts.com/programs/"
    r = safe_get(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    for card in soup.select("article, .program, [class*='program'], [class*='event'], .views-row"):
        title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
        date_el = card.select_one("time, .date, [class*='date']")
        link_el = card.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = date_el.get_text(strip=True) if date_el else ""
        link = urljoin(url, link_el["href"]) if link_el else url
        events.append({
            "id": make_id("fringearts", title, date_str),
            "title": title,
            "date_display": date_str,
            "venue": "FringeArts",
            "source": "FringeArts",
            "source_url": url,
            "link": link,
            "price": None,
            "categories": categorize(title, "FringeArts"),
            "image": None,
        })
    print(f"  FringeArts: {len(events)} events")
    return events


def scrape_phila_ballet():
    """Philadelphia Ballet."""
    events = []
    url = "https://philadelphiaballet.org/"
    r = safe_get(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    for card in soup.select("article, [class*='performance'], [class*='show'], [class*='event'], [class*='season']"):
        title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
        date_el = card.select_one("time, .date, [class*='date']")
        link_el = card.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = date_el.get_text(strip=True) if date_el else ""
        link = urljoin(url, link_el["href"]) if link_el else url
        events.append({
            "id": make_id("phila_ballet", title, date_str),
            "title": title,
            "date_display": date_str,
            "venue": "Academy of Music / Merriam Theater",
            "source": "Philadelphia Ballet",
            "source_url": url,
            "link": link,
            "price": None,
            "categories": ["ballet", "dance"],
            "image": None,
        })
    print(f"  Philadelphia Ballet: {len(events)} events")
    return events


def scrape_arden_theatre():
    """Arden Theatre Company."""
    events = []
    url = "https://ardentheatre.org/productions/"
    r = safe_get(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    for card in soup.select("article, [class*='production'], [class*='show'], [class*='event']"):
        title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
        date_el = card.select_one("time, .date, [class*='date']")
        link_el = card.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = date_el.get_text(strip=True) if date_el else ""
        link = urljoin(url, link_el["href"]) if link_el else url
        events.append({
            "id": make_id("arden", title, date_str),
            "title": title,
            "date_display": date_str,
            "venue": "Arden Theatre",
            "source": "Arden Theatre",
            "source_url": url,
            "link": link,
            "price": None,
            "categories": categorize(title, "Arden Theatre"),
            "image": None,
        })
    print(f"  Arden Theatre: {len(events)} events")
    return events


def scrape_chris_jazz():
    """Chris' Jazz Cafe."""
    events = []
    url = "https://www.chrisjazzcafe.com/events"
    r = safe_get(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    for card in soup.select("article, [class*='event'], [class*='Event'], .sqs-block, .summary-item"):
        title_el = card.select_one("h2, h3, h4, .title, [class*='title'], .summary-title")
        date_el = card.select_one("time, .date, [class*='date'], .summary-metadata-item")
        link_el = card.select_one("a[href]")
        price_el = card.select_one("[class*='price'], [class*='Price']")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = date_el.get_text(strip=True) if date_el else ""
        link = urljoin(url, link_el["href"]) if link_el else url
        price = parse_price(price_el.get_text(strip=True)) if price_el else None
        events.append({
            "id": make_id("chris_jazz", title, date_str),
            "title": title,
            "date_display": date_str,
            "venue": "Chris' Jazz Cafe",
            "source": "Chris' Jazz Cafe",
            "source_url": url,
            "link": link,
            "price": price,
            "categories": ["jazz"],
            "image": None,
        })
    print(f"  Chris' Jazz Cafe: {len(events)} events")
    return events


def scrape_south_jazz():
    """South Jazz Kitchen."""
    events = []
    url = "https://www.southjazzkitchen.com/jazz-club/"
    r = safe_get(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    for card in soup.select("article, [class*='event'], [class*='show'], .sqs-block"):
        title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
        date_el = card.select_one("time, .date, [class*='date']")
        link_el = card.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = date_el.get_text(strip=True) if date_el else ""
        link = urljoin(url, link_el["href"]) if link_el else url
        events.append({
            "id": make_id("south_jazz", title, date_str),
            "title": title,
            "date_display": date_str,
            "venue": "South Jazz Kitchen",
            "source": "South Jazz Kitchen",
            "source_url": url,
            "link": link,
            "price": None,
            "categories": ["jazz"],
            "image": None,
        })
    print(f"  South Jazz Kitchen: {len(events)} events")
    return events


def scrape_world_cafe():
    """World Cafe Live."""
    events = []
    url = "https://worldcafelive.org/events/"
    r = safe_get(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    for card in soup.select("article, [class*='event'], [class*='Event'], .tribe-events-calendar-list__event"):
        title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
        date_el = card.select_one("time, .date, [class*='date']")
        link_el = card.select_one("a[href]")
        price_el = card.select_one("[class*='price'], [class*='cost']")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = date_el.get_text(strip=True) if date_el else ""
        link = urljoin(url, link_el["href"]) if link_el else url
        price = parse_price(price_el.get_text(strip=True)) if price_el else None
        cats = categorize(title, "World Cafe Live")
        if not cats:
            cats = ["concert"]
        events.append({
            "id": make_id("world_cafe", title, date_str),
            "title": title,
            "date_display": date_str,
            "venue": "World Cafe Live",
            "source": "World Cafe Live",
            "source_url": url,
            "link": link,
            "price": price,
            "categories": cats,
            "image": None,
        })
    print(f"  World Cafe Live: {len(events)} events")
    return events


def scrape_city_winery():
    """City Winery Philadelphia."""
    events = []
    url = "https://citywinery.com/pages/events/philadelphia"
    r = safe_get(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    # City Winery uses Shopify — try JSON-LD first
    for script in soup.select("script[type='application/ld+json']"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data:
                    if item.get("@type") == "Event":
                        events.append({
                            "id": make_id("city_winery", item.get("name", ""), item.get("startDate", "")),
                            "title": item.get("name", ""),
                            "date_display": item.get("startDate", ""),
                            "venue": "City Winery Philadelphia",
                            "source": "City Winery",
                            "source_url": url,
                            "link": item.get("url", url),
                            "price": parse_price(str(item.get("offers", {}))),
                            "categories": categorize(item.get("name", ""), "City Winery"),
                            "image": None,
                        })
        except json.JSONDecodeError:
            pass
    # Fallback to HTML parsing
    if not events:
        for card in soup.select("article, [class*='event'], [class*='Event']"):
            title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
            date_el = card.select_one("time, .date, [class*='date']")
            link_el = card.select_one("a[href]")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            date_str = date_el.get_text(strip=True) if date_el else ""
            link = urljoin(url, link_el["href"]) if link_el else url
            events.append({
                "id": make_id("city_winery", title, date_str),
                "title": title,
                "date_display": date_str,
                "venue": "City Winery Philadelphia",
                "source": "City Winery",
                "source_url": url,
                "link": link,
                "price": None,
                "categories": categorize(title, "City Winery"),
                "image": None,
            })
    print(f"  City Winery: {len(events)} events")
    return events


def scrape_phila_dance():
    """PhiladelphiaDANCE.org — dance aggregator."""
    events = []
    url = "https://philadelphiadance.org/calendar/"
    r = safe_get(url)
    if not r:
        return events
    soup = BeautifulSoup(r.text, "lxml")
    for card in soup.select("article, [class*='event'], .tribe-events-calendar-list__event, .type-tribe_events"):
        title_el = card.select_one("h2, h3, h4, .title, [class*='title']")
        date_el = card.select_one("time, .date, [class*='date']")
        venue_el = card.select_one(".venue, [class*='venue']")
        link_el = card.select_one("a[href]")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        date_str = date_el.get_text(strip=True) if date_el else ""
        venue = venue_el.get_text(strip=True) if venue_el else ""
        link = urljoin(url, link_el["href"]) if link_el else url
        events.append({
            "id": make_id("phila_dance", title, date_str),
            "title": title,
            "date_display": date_str,
            "venue": venue,
            "source": "PhiladelphiaDANCE.org",
            "source_url": url,
            "link": link,
            "price": None,
            "categories": ["dance"],
            "image": None,
        })
    print(f"  PhiladelphiaDANCE.org: {len(events)} events")
    return events


# ---------------------------------------------------------------------------
# CATEGORIZATION
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS = {
    "musical": ["musical", "broadway", "hamilton", "wicked", "phantom", "les mis",
                 "west side story", "cats ", "rent ", "chicago ", "cabaret"],
    "theater": ["play", "theatre", "theater", "drama", "comedy", "tragedy",
                "shakespeare", "monologue", "one-man", "one-woman", "staged reading"],
    "dance": ["dance", "dancing", "choreograph", "modern dance", "contemporary dance",
              "hip hop dance", "tap dance", "flamenco"],
    "ballet": ["ballet", "nutcracker", "swan lake", "giselle", "sleeping beauty",
               "pas de deux", "pointe"],
    "jazz": ["jazz", "bebop", "swing", "big band", "jazz trio", "jazz quartet",
             "blue note", "jazz cafe", "jazz kitchen"],
    "classical": ["orchestra", "symphony", "philharmonic", "chamber", "concerto",
                  "sonata", "quartet", "recital", "classical", "violin", "cello",
                  "piano concert", "organ recital", "chopin", "beethoven", "mozart",
                  "bach ", "brahms"],
    "opera": ["opera", "soprano", "tenor", "baritone", "aria", "libretto"],
}

VENUE_CATEGORIES = {
    "Walnut Street Theatre": ["theater", "musical"],
    "Arden Theatre": ["theater"],
    "FringeArts": ["theater", "dance"],
    "Chris' Jazz Cafe": ["jazz"],
    "South Jazz Kitchen": ["jazz"],
    "Penn Live Arts": ["dance", "concert"],
    "Philadelphia Ballet": ["ballet", "dance"],
    "Academy of Music": ["classical", "ballet", "opera"],
}


def categorize(text, venue=""):
    text_lower = (text or "").lower()
    venue_lower = (venue or "").lower()
    cats = set()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            cats.add(cat)
    for venue_name, venue_cats in VENUE_CATEGORIES.items():
        if venue_name.lower() in venue_lower:
            cats.update(venue_cats)
    return sorted(cats) if cats else ["performance"]


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

ALL_SCRAPERS = [
    scrape_ensemble_arts,
    scrape_philorch,
    scrape_theatre_philly,
    scrape_penn_live_arts,
    scrape_opera_phila,
    scrape_walnut_street,
    scrape_fringe_arts,
    scrape_phila_ballet,
    scrape_arden_theatre,
    scrape_chris_jazz,
    scrape_south_jazz,
    scrape_world_cafe,
    scrape_city_winery,
    scrape_phila_dance,
]


def main():
    print("🎭 Philadelphia Cultural Events Scraper")
    print("=" * 50)
    all_events = []
    for scraper in ALL_SCRAPERS:
        name = scraper.__doc__.split("—")[0].strip() if scraper.__doc__ else scraper.__name__
        print(f"\nScraping: {name}")
        try:
            events = scraper()
            all_events.extend(events)
        except Exception as e:
            print(f"  [ERROR] {e}", file=sys.stderr)

    # Deduplicate by title similarity
    seen = set()
    unique_events = []
    for ev in all_events:
        key = re.sub(r'\s+', ' ', ev["title"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique_events.append(ev)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "total_events": len(unique_events),
        "sources": list({e["source"] for e in unique_events}),
        "events": unique_events,
    }
    out_path = OUTPUT_DIR / "events.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n✅ Wrote {len(unique_events)} events to {out_path}")

    # Also write a sources metadata file
    sources_meta = {
        "sources": [
            {"name": "Ensemble Arts Philly", "url": "https://www.ensembleartsphilly.org/tickets-and-events", "covers": "Classical, jazz, ballet, Broadway, theater, dance", "venues": ["Kimmel Center", "Academy of Music", "Miller Theater"]},
            {"name": "Philadelphia Orchestra", "url": "https://philorch.ensembleartsphilly.org/tickets-and-events/events", "covers": "Classical concerts, orchestral performances", "venues": ["Verizon Hall"]},
            {"name": "Theatre Philadelphia", "url": "https://theatrephiladelphia.org/whats-on-stage", "covers": "All theater across Greater Philadelphia (aggregator)", "venues": ["Various"]},
            {"name": "Penn Live Arts", "url": "https://pennlivearts.org/events/", "covers": "Dance, music, jazz, classical, world, theater", "venues": ["Annenberg Center"]},
            {"name": "Opera Philadelphia", "url": "https://www.operaphila.org/whats-on/events/", "covers": "Opera, vocal performances", "venues": ["Academy of Music", "Various"]},
            {"name": "Walnut Street Theatre", "url": "https://www.walnutstreettheatre.org/season/mainstage.2026.php", "covers": "Musicals, plays", "venues": ["Walnut Street Theatre"]},
            {"name": "FringeArts", "url": "https://fringearts.com/programs/", "covers": "Contemporary performance, experimental theater, dance", "venues": ["FringeArts"]},
            {"name": "Philadelphia Ballet", "url": "https://philadelphiaballet.org/", "covers": "Ballet, dance", "venues": ["Academy of Music", "Merriam Theater"]},
            {"name": "Arden Theatre", "url": "https://ardentheatre.org/productions/", "covers": "Theater, musicals, children's theater", "venues": ["Arden Theatre"]},
            {"name": "Chris' Jazz Cafe", "url": "https://www.chrisjazzcafe.com/events", "covers": "Jazz concerts", "venues": ["Chris' Jazz Cafe"]},
            {"name": "South Jazz Kitchen", "url": "https://www.southjazzkitchen.com/jazz-club/", "covers": "Jazz, dinner shows", "venues": ["South Jazz Kitchen"]},
            {"name": "World Cafe Live", "url": "https://worldcafelive.org/events/", "covers": "Concerts — jazz, folk, rock, world music", "venues": ["World Cafe Live"]},
            {"name": "City Winery", "url": "https://citywinery.com/pages/events/philadelphia", "covers": "Jazz, R&B, rock, comedy", "venues": ["City Winery Philadelphia"]},
            {"name": "PhiladelphiaDANCE.org", "url": "https://philadelphiadance.org/calendar/", "covers": "Dance events (community aggregator)", "venues": ["Various"]},
        ]
    }
    with open(OUTPUT_DIR / "sources.json", "w") as f:
        json.dump(sources_meta, f, indent=2)
    print(f"✅ Wrote sources metadata to {OUTPUT_DIR / 'sources.json'}")


if __name__ == "__main__":
    main()
