#!/usr/bin/env python3
"""
Seed Events — verified Philadelphia performing arts events from public sources.

These are real, verified events from Visit Philadelphia, Ensemble Arts, and
other public listings. They serve as baseline data when the live scraper
cannot reach venue websites (e.g., due to bot blocking, network issues).

This file is updated periodically with current season data.
Last verified: 2026-03-23 via visitphilly.com, ensembleartsphilly.org, philaculture.org
"""

import hashlib
from datetime import datetime


def make_id(source, title, date_str=""):
    raw = f"{source}|{title}|{date_str}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def get_seed_events():
    """Return list of verified Philadelphia cultural events for the current season."""
    events = [
        # === CLASSICAL / ORCHESTRA ===
        {
            "title": "Mahler's Symphony No. 2",
            "date_start": "2026-03-06",
            "date_end": "2026-03-08",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["classical"],
            "description": "Yannick Nézet-Séguin conducts Mahler's monumental Symphony No. 2 'Resurrection' featuring vocalists Ying Fang and Joyce DiDonato.",
        },
        {
            "title": "Reena Esmail, Charles Ives & Wynton Marsalis",
            "date_start": "2026-03-13",
            "date_end": "2026-03-13",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["classical"],
            "description": "The Philadelphia Orchestra performs compositions by Reena Esmail, Charles Ives and Wynton Marsalis.",
        },
        {
            "title": "Brodsky Star Spotlight: Víkingur Ólafsson",
            "date_start": "2026-03-19",
            "date_end": "2026-03-19",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["classical"],
            "description": "Acclaimed Icelandic pianist Víkingur Ólafsson in the Brodsky Star Spotlight Series.",
        },
        {
            "title": "Marin Leads Rachmaninoff and Schumann",
            "date_start": "2026-03-20",
            "date_end": "2026-03-22",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["classical"],
            "description": "The Philadelphia Orchestra performs Rachmaninoff and Schumann under the baton of conductor Marin Alsop.",
        },
        {
            "title": "Distant Worlds: Music from Final Fantasy",
            "date_start": "2026-03-21",
            "date_end": "2026-03-21",
            "venue": "Academy of Music",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["classical", "concert"],
            "description": "The beloved music of Final Fantasy performed by a full symphony orchestra and chorus at the Academy of Music.",
        },
        {
            "title": "Sound All Around",
            "date_start": "2026-03-21",
            "date_end": "2026-03-23",
            "venue": "Kimmel Cultural Campus",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["classical", "performance"],
            "description": "Interactive musical experiences for all ages at the Kimmel Cultural Campus.",
        },

        # === JAZZ ===
        {
            "title": "Emmet Cohen: Miles and Coltrane at 100",
            "date_start": "2026-03-20",
            "date_end": "2026-03-20",
            "venue": "Perelman Theater, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["jazz"],
            "description": "Pianist Emmet Cohen celebrates the centennials of Miles Davis and John Coltrane in a special jazz concert.",
        },
        {
            "title": "Endea Owens & The Cookout",
            "date_start": "2026-03-28",
            "date_end": "2026-03-28",
            "venue": "Perelman Theater, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["jazz"],
            "description": "The Late Show's bassist Endea Owens brings her dynamic ensemble The Cookout to the Jazz Series.",
        },
        {
            "title": "Christian McBride & Edgar Meyer",
            "date_start": "2026-04-21",
            "date_end": "2026-04-21",
            "venue": "Perelman Theater, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["jazz"],
            "description": "Philly's own Christian McBride joined by fellow bassist Edgar Meyer in a special Jazz Series performance.",
        },
        {
            "title": "Pablo Batista: Latin Jazz Orchestra",
            "date_start": "2026-04-17",
            "date_end": "2026-04-17",
            "venue": "Esperanza Arts Center",
            "source": "Esperanza Arts Center",
            "source_url": "https://www.philaculture.org/events-calendar",
            "link": "https://www.philaculture.org/events-calendar",
            "price": None,
            "categories": ["jazz"],
            "description": "Grammy Award-winning percussionist Pablo Batista leads the Primera Primavera orchestra — 20 big band musicians performing legendary Latin jazz tunes.",
        },

        # === THEATER ===
        {
            "title": "Good Bones",
            "date_start": "2026-02-19",
            "date_end": "2026-03-22",
            "venue": "Arden Theatre",
            "source": "Arden Theatre",
            "source_url": "https://ardentheatre.org/productions/",
            "link": "https://ardentheatre.org/productions/",
            "price": "$37 – $70",
            "categories": ["theater"],
            "description": "Written by Pulitzer Prize-winning playwright James Ijames. A compelling new work at the Arden Theatre.",
        },
        {
            "title": "Romeo and Juliet",
            "date_start": "2026-03-12",
            "date_end": "2026-04-05",
            "venue": "Arden Theatre",
            "source": "Arden Theatre",
            "source_url": "https://ardentheatre.org/productions/",
            "link": "https://ardentheatre.org/productions/",
            "price": "$37 – $70",
            "categories": ["theater"],
            "description": "A bold reimagining of Shakespeare's star-crossed lovers at the Arden Theatre.",
        },
        {
            "title": "Sh!t-Faced Shakespeare",
            "date_start": "2026-03-20",
            "date_end": "2026-03-21",
            "venue": "Perelman Theater, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["theater"],
            "description": "The hilariously irreverent Shakespeare show where one cast member has had a few too many.",
        },
        {
            "title": "The Most Spectacularly Lamentable Trial of Miz Martha Washington",
            "date_start": "2026-03-18",
            "date_end": "2026-04-12",
            "venue": "The Wilma Theater",
            "source": "Theatre Philadelphia",
            "source_url": "https://theatrephiladelphia.org/whats-on-stage",
            "link": "https://theatrephiladelphia.org/whats-on-stage",
            "price": None,
            "categories": ["theater"],
            "description": "A bold new work at The Wilma Theater exploring history through a contemporary lens.",
        },

        # === BROADWAY / MUSICALS ===
        {
            "title": "TINA – The Tina Turner Musical",
            "date_start": "2026-03-10",
            "date_end": "2026-03-15",
            "venue": "Miller Theater",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["musical"],
            "description": "The electrifying biographical musical about the life and career of Tina Turner at the Miller Theater.",
        },
        {
            "title": "The Sound of Music",
            "date_start": "2026-03-31",
            "date_end": "2026-04-05",
            "venue": "Academy of Music",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["musical"],
            "description": "Rodgers and Hammerstein's beloved musical comes to the Academy of Music as part of the Broadway Series.",
        },

        # === BALLET / DANCE ===
        {
            "title": "The Merry Widow",
            "date_start": "2026-03-05",
            "date_end": "2026-03-15",
            "venue": "Academy of Music",
            "source": "Philadelphia Ballet",
            "source_url": "https://philadelphiaballet.org/performances/",
            "link": "https://philadelphiaballet.org/performances/",
            "price": None,
            "categories": ["ballet", "dance"],
            "description": "Philadelphia Ballet presents The Merry Widow, choreographed by Ronald Hynd. An unforgettable love story set in Belle Époque Paris.",
        },

        # === FAMILY ===
        {
            "title": "Peppa Pig: My First Concert",
            "date_start": "2026-04-04",
            "date_end": "2026-04-04",
            "venue": "Kimmel Cultural Campus",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["performance"],
            "description": "Part of Ensemble Arts' Family Discovery Series. Geared toward ages 18 months and up.",
        },
    ]

    # Add computed fields
    for ev in events:
        date_str = ev.get("date_start", "")
        ev["id"] = make_id(ev["source"], ev["title"], date_str)
        s, e = ev.get("date_start", ""), ev.get("date_end", "")
        if s and e and s != e:
            try:
                sd = datetime.strptime(s, "%Y-%m-%d")
                ed = datetime.strptime(e, "%Y-%m-%d")
                ev["date_display"] = f"{sd.strftime('%b %d')} – {ed.strftime('%b %d, %Y')}"
            except ValueError:
                ev["date_display"] = f"{s} – {e}"
        elif s:
            try:
                sd = datetime.strptime(s, "%Y-%m-%d")
                ev["date_display"] = sd.strftime("%b %d, %Y")
            except ValueError:
                ev["date_display"] = s
        else:
            ev["date_display"] = ""
        ev.setdefault("time", None)
        ev.setdefault("description", None)

    return events
