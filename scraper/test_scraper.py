#!/usr/bin/env python3
"""Tests for the Philadelphia Cultural Events Scraper core functions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scrape_events import (
    clean_text, parse_price, parse_date_range, validate_event,
    categorize, make_id, extract_json_ld_events, extract_events_generic,
    extract_microdata_events, extract_events_from_links,
    TITLE_SELECTORS, DATE_SELECTORS,
)
from seed_events import get_seed_events
from bs4 import BeautifulSoup

import unittest


class TestCleanText(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(clean_text("  hello   world  "), "hello world")

    def test_none(self):
        self.assertEqual(clean_text(None), "")

    def test_newlines(self):
        self.assertEqual(clean_text("line1\n  line2\t line3"), "line1 line2 line3")


class TestParsePrice(unittest.TestCase):
    def test_free(self):
        self.assertEqual(parse_price("Free"), "Free")
        self.assertEqual(parse_price("free!"), "Free")
        self.assertEqual(parse_price("FREE ADMISSION"), "Free")
        self.assertEqual(parse_price("No Cover"), "Free")

    def test_single_price(self):
        self.assertEqual(parse_price("$25"), "$25")
        self.assertEqual(parse_price("Tickets: $45.00"), "$45.00")

    def test_range(self):
        self.assertEqual(parse_price("$25 – $75"), "$25 – $75")
        self.assertEqual(parse_price("$37 - $70"), "$37 - $70")

    def test_none(self):
        self.assertIsNone(parse_price(None))
        self.assertIsNone(parse_price(""))
        self.assertIsNone(parse_price("See website"))


class TestParseDateRange(unittest.TestCase):
    def test_range_with_year(self):
        s, e, d = parse_date_range("March 5 – March 15, 2026")
        self.assertEqual(s, "2026-03-05")
        self.assertEqual(e, "2026-03-15")

    def test_range_short_month(self):
        s, e, d = parse_date_range("Mar 20 - Apr 5, 2026")
        self.assertEqual(s, "2026-03-20")
        self.assertEqual(e, "2026-04-05")

    def test_single_date(self):
        s, e, d = parse_date_range("March 21, 2026")
        self.assertEqual(s, "2026-03-21")
        self.assertEqual(e, "2026-03-21")

    def test_iso_date(self):
        s, e, d = parse_date_range("2026-04-17")
        self.assertEqual(s, "2026-04-17")

    def test_empty(self):
        s, e, d = parse_date_range("")
        self.assertIsNone(s)
        self.assertIsNone(e)

    def test_none(self):
        s, e, d = parse_date_range(None)
        self.assertIsNone(s)


class TestValidateEvent(unittest.TestCase):
    def test_valid(self):
        ev = {"title": "Hamilton", "source": "Ensemble Arts"}
        self.assertTrue(validate_event(ev))

    def test_no_title(self):
        self.assertFalse(validate_event({"title": "", "source": "x"}))

    def test_no_source(self):
        self.assertFalse(validate_event({"title": "Hamilton", "source": ""}))

    def test_nav_item(self):
        self.assertFalse(validate_event({"title": "Subscribe", "source": "x"}))
        self.assertFalse(validate_event({"title": "Menu", "source": "x"}))

    def test_too_long(self):
        self.assertFalse(validate_event({"title": "x" * 201, "source": "x"}))

    def test_short_title(self):
        self.assertFalse(validate_event({"title": "A", "source": "x"}))


class TestCategorize(unittest.TestCase):
    def test_musical(self):
        cats = categorize("Hamilton: The Musical")
        self.assertIn("musical", cats)

    def test_jazz(self):
        cats = categorize("Jazz Night at the Cafe")
        self.assertIn("jazz", cats)

    def test_venue_categories(self):
        cats = categorize("Some Event", "Chris' Jazz Cafe")
        self.assertIn("jazz", cats)

    def test_default(self):
        cats = categorize("Unknown Event")
        self.assertEqual(cats, ["performance"])


class TestMakeId(unittest.TestCase):
    def test_deterministic(self):
        id1 = make_id("source", "title", "2026-03-21")
        id2 = make_id("source", "title", "2026-03-21")
        self.assertEqual(id1, id2)

    def test_different(self):
        id1 = make_id("src1", "title")
        id2 = make_id("src2", "title")
        self.assertNotEqual(id1, id2)


class TestJsonLdExtraction(unittest.TestCase):
    def test_basic_event(self):
        html = """<html><head><script type="application/ld+json">
        {"@type": "Event", "name": "Test Concert", "startDate": "2026-04-01",
         "endDate": "2026-04-01", "location": {"name": "Test Venue"},
         "url": "https://example.com/event"}
        </script></head><body></body></html>"""
        soup = BeautifulSoup(html, "lxml")
        events = extract_json_ld_events(soup, "https://example.com", "Test Source", "Default Venue")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["title"], "Test Concert")
        self.assertEqual(events[0]["venue"], "Test Venue")
        self.assertEqual(events[0]["date_start"], "2026-04-01")

    def test_array_type(self):
        html = """<html><head><script type="application/ld+json">
        {"@type": ["Event", "MusicEvent"], "name": "Jazz Night",
         "startDate": "2026-04-10"}
        </script></head><body></body></html>"""
        soup = BeautifulSoup(html, "lxml")
        events = extract_json_ld_events(soup, "https://example.com", "Src", "Venue")
        self.assertEqual(len(events), 1)

    def test_graph(self):
        html = """<html><head><script type="application/ld+json">
        {"@graph": [{"@type": "Event", "name": "Show A", "startDate": "2026-05-01"},
                     {"@type": "Event", "name": "Show B", "startDate": "2026-05-02"}]}
        </script></head><body></body></html>"""
        soup = BeautifulSoup(html, "lxml")
        events = extract_json_ld_events(soup, "https://example.com", "Src", "Venue")
        self.assertEqual(len(events), 2)

    def test_non_event(self):
        html = """<html><head><script type="application/ld+json">
        {"@type": "Organization", "name": "Some Org"}
        </script></head><body></body></html>"""
        soup = BeautifulSoup(html, "lxml")
        events = extract_json_ld_events(soup, "https://example.com", "Src", "Venue")
        self.assertEqual(len(events), 0)


class TestMicrodataExtraction(unittest.TestCase):
    def test_basic(self):
        html = """<html><body>
        <div itemscope itemtype="https://schema.org/Event">
          <span itemprop="name">Microdata Event</span>
          <time itemprop="startDate" datetime="2026-05-01">May 1</time>
          <span itemprop="location" itemscope><span itemprop="name">My Venue</span></span>
        </div></body></html>"""
        soup = BeautifulSoup(html, "lxml")
        events = extract_microdata_events(soup, "https://example.com", "Src", "Default")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["title"], "Microdata Event")
        self.assertEqual(events[0]["date_start"], "2026-05-01")


class TestLinkExtraction(unittest.TestCase):
    def test_event_links(self):
        html = """<html><body>
        <a href="/events/concert-2026">Great Concert</a>
        <a href="/about">About Us</a>
        <a href="/shows/hamilton/">Hamilton</a>
        </body></html>"""
        soup = BeautifulSoup(html, "lxml")
        events = extract_events_from_links(soup, "https://example.com", "Src", "Venue")
        titles = [e["title"] for e in events]
        self.assertIn("Great Concert", titles)
        self.assertNotIn("About Us", titles)


class TestHtmlExtraction(unittest.TestCase):
    def test_basic_cards(self):
        html = """<html><body>
        <article><h3>Spring Gala</h3><time>March 30, 2026</time></article>
        <article><h3>Summer Festival</h3><time>June 15, 2026</time></article>
        </body></html>"""
        soup = BeautifulSoup(html, "lxml")
        events = extract_events_generic(soup, "https://example.com", "Src", "Venue", ["article"])
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["title"], "Spring Gala")


class TestSeedEvents(unittest.TestCase):
    def test_seed_has_events(self):
        events = get_seed_events()
        self.assertGreater(len(events), 10)

    def test_seed_fields(self):
        events = get_seed_events()
        for ev in events:
            self.assertIn("id", ev)
            self.assertIn("title", ev)
            self.assertIn("source", ev)
            self.assertIn("venue", ev)
            self.assertIn("date_start", ev)
            self.assertIn("categories", ev)
            self.assertTrue(len(ev["title"]) > 1)
            self.assertTrue(len(ev["id"]) == 12)

    def test_seed_no_duplicates(self):
        events = get_seed_events()
        ids = [e["id"] for e in events]
        self.assertEqual(len(ids), len(set(ids)), "Seed events have duplicate IDs")


if __name__ == "__main__":
    unittest.main()
