#!/usr/bin/env python3
"""
Seed Events — verified Philadelphia arts & culture events from public sources.

These are real, verified events from Visit Philadelphia, Ensemble Arts Philly,
Theatre Philadelphia, Penn Live Arts, Opera Philadelphia, Philadelphia Museum of Art,
Barnes Foundation, Franklin Institute, Penn Museum, Academy of Natural Sciences,
Mütter Museum, Science on Tap, Profs and Pints, and other public listings.
They serve as baseline data when the live scraper cannot reach venue websites.

Last verified: 2026-03-24 via visitphilly.com, ensembleartsphilly.org,
theatrephiladelphia.org, pennlivearts.org, operaphila.org, walnutstreettheatre.org,
philadelphiaballet.org, balletx.org, philamuseum.org, barnesfoundation.org,
fi.edu, penn.museum, ansp.org, muttermuseum.org, scienceontapphilly.com
"""

import hashlib
import re
from datetime import datetime


def make_id(source, title, date_str=""):
    raw = f"{source}|{title}|{date_str}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _slugify(text):
    """Convert text to URL slug: 'Lang Lang and Yannick' -> 'lang-lang-and-yannick'."""
    text = (text or "").lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text


def _auto_link(ev):
    """Generate a direct event page link based on source and title.
    Falls back to the source_url if no pattern matches.
    """
    source = ev.get("source", "")
    title = ev.get("title", "")
    slug = _slugify(title)
    if not slug:
        return ev.get("source_url", "")

    venue = (ev.get("venue") or "").lower()
    cats = ev.get("categories", [])

    if source in ("Ensemble Arts Philly", "Philadelphia Orchestra"):
        # Ensemble Arts URLs: /tickets-and-events/<org>/<season>/<slug>
        if "orchestra" in source.lower() or "orchestra" in venue:
            return f"https://www.ensembleartsphilly.org/tickets-and-events/philadelphia-orchestra/2025-26-season/{slug}"
        if "musical" in cats and ("academy" in venue or "forrest" in venue):
            return f"https://www.ensembleartsphilly.org/tickets-and-events/broadway/2025-26-season/{slug}"
        if "jazz" in cats:
            return f"https://www.ensembleartsphilly.org/tickets-and-events/jazz/2025-26-season/{slug}"
        # General Ensemble Arts events
        return f"https://www.ensembleartsphilly.org/tickets-and-events/events/{slug}"

    if source == "Penn Live Arts":
        return f"https://pennlivearts.org/event/{slug}"

    if source == "Arden Theatre":
        return f"https://ardentheatre.org/productions/{slug}/"

    if source == "The Wilma Theater":
        return f"https://www.wilmatheater.org/whats-on/{slug}/"

    if source == "Opera Philadelphia":
        return f"https://www.operaphila.org/whats-on/events/{slug}/"

    if source == "FringeArts":
        return f"https://fringearts.com/event/{slug}/"

    if source == "Walnut Street Theatre":
        return f"https://www.walnutstreettheatre.org/season/{slug}"

    if source == "Philadelphia Theatre Company":
        return f"https://www.philatheatreco.org/{slug}"

    if source == "Philadelphia Ballet":
        return f"https://philadelphiaballet.org/performances/{slug}/"

    if source == "BalletX":
        return f"https://www.balletx.org/seasons/{slug}/"

    if source == "Philadelphia Museum of Art":
        return f"https://philamuseum.org/exhibitions/{slug}"

    if source == "Barnes Foundation":
        return f"https://www.barnesfoundation.org/whats-on/{slug}"

    if source == "The Franklin Institute":
        return f"https://fi.edu/en/exhibits-and-experiences/{slug}"

    if source == "Penn Museum":
        return f"https://www.penn.museum/on-view/{slug}"

    if source == "Academy of Natural Sciences":
        return f"https://ansp.org/exhibits/{slug}/"

    if source == "Mütter Museum":
        return f"https://muttermuseum.org/events/{slug}/"

    if source == "Science on Tap":
        return "https://www.scienceontapphilly.com/events"

    if source == "Profs and Pints":
        return "https://www.profsandpints.com/philadelphia"

    if source == "Science History Institute":
        return f"https://www.sciencehistory.org/visit/events/{slug}"

    if source == "Sofar Sounds Philadelphia":
        return "https://www.sofarsounds.com/cities/philadelphia"

    # Fallback to source URL
    return ev.get("source_url", "")


def get_seed_events():
    """Return list of verified Philadelphia cultural events for the current season."""
    events = [
        # ═══════════════════════════════════════════════════════════════════
        # CLASSICAL / ORCHESTRA
        # ═══════════════════════════════════════════════════════════════════
        {
            "title": "Mahler's Symphony No. 2",
            "date_start": "2026-03-06",
            "date_end": "2026-03-08",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "link": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "price": None,
            "categories": ["classical"],
            "description": "Yannick Nézet-Séguin conducts Mahler's monumental Symphony No. 2 'Resurrection' featuring vocalists Ying Fang and Joyce DiDonato.",
            "time": "8:00 PM",
        },
        {
            "title": "Yo-Yo Ma and Interlochen Center for the Arts",
            "date_start": "2026-03-13",
            "date_end": "2026-03-13",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["classical"],
            "description": "Legendary cellist Yo-Yo Ma performs with the Interlochen Center for the Arts to Celebrate America at 250.",
            "time": "8:00 PM",
        },
        {
            "title": "The Young Person's Guide to the Orchestra",
            "date_start": "2026-03-14",
            "date_end": "2026-03-14",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["classical", "performance"],
            "description": "Part of the Family Discovery Series — a magical introduction to the orchestra designed for young audiences. Explore Britten's beloved guide to every instrument family, from the delicate flute to the thundering timpani. Ideal for ages 3–10.",
            "time": "11:30 AM",
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
            "description": "Acclaimed Icelandic pianist Víkingur Ólafsson takes the stage in the Brodsky Star Spotlight Series. Known for his revelatory Bach and Debussy recordings, Ólafsson brings his signature intensity and clarity to a solo recital.",
            "time": "7:30 PM",
        },
        {
            "title": "Marin Leads Rachmaninoff and Schumann",
            "date_start": "2026-03-20",
            "date_end": "2026-03-22",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "link": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "price": None,
            "categories": ["classical"],
            "description": "Conductor Marin Alsop leads the Philadelphia Orchestra in Rachmaninoff's lush Symphonic Dances and Schumann's deeply romantic Second Symphony. A program that showcases the Orchestra's legendary warmth and power.",
            "time": "8:00 PM",
        },
        {
            "title": "Distant Worlds: Music from Final Fantasy",
            "date_start": "2026-03-21",
            "date_end": "2026-03-21",
            "venue": "Academy of Music",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "time": "8:00 PM",
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
            "description": "A free weekend of interactive musical experiences for all ages at the Kimmel Cultural Campus. Explore instruments, meet musicians, enjoy mini-performances, and discover the world of orchestral music up close.",
        },
        {
            "title": "ECCO with Anthony McGill & Tai Murray",
            "date_start": "2026-03-31",
            "date_end": "2026-03-31",
            "venue": "Perelman Theater, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "time": "7:30 PM",
            "price": None,
            "categories": ["classical"],
            "description": "The East Coast Chamber Orchestra (ECCO) performs a conductor-less program featuring clarinetist Anthony McGill (NY Philharmonic principal) and violinist Tai Murray. An intimate evening of chamber music at the Perelman.",
        },
        {
            "title": "Lang Lang and Yannick",
            "date_start": "2026-04-07",
            "date_end": "2026-04-07",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events/philadelphia-orchestra/2025-26-season/lang-lang-and-yannick",
            "time": "7:30 PM",
            "price": None,
            "categories": ["classical"],
            "description": "A Benefit Concert for the Musicians' Retirement Fund. The celebrated pianist Lang Lang joins Yannick Nézet-Séguin and the Orchestra in Beethoven's lyrical Piano Concerto No. 4. A one-night-only engagement.",
        },
        {
            "title": "Mozart's Requiem",
            "date_start": "2026-04-09",
            "date_end": "2026-04-12",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "link": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "price": None,
            "categories": ["classical"],
            "description": "Yannick Nézet-Séguin conducts Mozart's final masterwork — the hauntingly beautiful Requiem in D minor, K. 626. Featuring world-class soloists and the Philadelphia Symphonic Choir in a performance that explores the boundary between life and eternity.",
            "time": "8:00 PM",
        },
        {
            "title": "Bolero and Don Juan",
            "date_start": "2026-04-23",
            "date_end": "2026-04-25",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "link": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "price": None,
            "categories": ["classical"],
            "description": "Two orchestral showstoppers in one program — Ravel's hypnotic, ever-building Bolero and Strauss's virtuosic tone poem Don Juan. A thrilling display of orchestral color, power, and the Philadelphia Orchestra's legendary sound.",
            "time": "8:00 PM",
        },
        {
            "title": "Copland's American Inspiration",
            "date_start": "2026-04-30",
            "date_end": "2026-05-02",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "link": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "price": None,
            "categories": ["classical"],
            "description": "Matthias Pintscher leads the Philadelphia Orchestra through Copland's most iconic American works — from the wide-open optimism of Appalachian Spring to the rhythmic energy of Rodeo. A celebration of the American musical spirit.",
            "time": "8:00 PM",
        },
        {
            "title": "Family Concert: Hip-Hop Orchestra",
            "date_start": "2026-05-02",
            "date_end": "2026-05-02",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "link": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "time": "11:30 AM",
            "price": None,
            "categories": ["classical", "performance"],
            "description": "A high-energy family concert where hip-hop meets the symphony. MC and beatboxer performers join the Philadelphia Orchestra in an explosive fusion of classical instruments and urban beats. Ages 5 and up.",
        },
        {
            "title": "Orchestra After 5: Postcards from Spain",
            "date_start": "2026-05-14",
            "date_end": "2026-05-14",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "link": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "time": "6:30 PM",
            "price": None,
            "categories": ["classical"],
            "description": "Unwind after work with the Philadelphia Orchestra's casual concert series. This edition transports you to Spain with Bizet's fiery Carmen Suite No. 1 and de Falla's colorful The Three-Cornered Hat. Cash bar and socializing included.",
        },
        {
            "title": "Yannick Nézet-Séguin: Mahler & Sorey",
            "date_start": "2026-05-15",
            "date_end": "2026-05-16",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "link": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "price": None,
            "categories": ["classical"],
            "description": "Music Director Yannick Nézet-Séguin pairs Mahler's deeply emotional symphonic world with a new work by MacArthur Fellow Tyshawn Sorey — one of the most visionary composers working today. A program that bridges centuries of musical ambition.",
            "time": "8:00 PM",
        },
        {
            "title": "Beethoven & Marsalis",
            "date_start": "2026-05-28",
            "date_end": "2026-05-30",
            "venue": "Marian Anderson Hall, Kimmel Center",
            "source": "Philadelphia Orchestra",
            "source_url": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "link": "https://philorch.ensembleartsphilly.org/tickets-and-events/2025-26-season",
            "price": None,
            "categories": ["classical", "jazz"],
            "description": "The Philadelphia Orchestra teams up with Jazz at Lincoln Center Orchestra to honor Beethoven and Wynton Marsalis.",
            "time": "8:00 PM",
        },

        # ═══════════════════════════════════════════════════════════════════
        # JAZZ
        # ═══════════════════════════════════════════════════════════════════
        {
            "title": "Emmet Cohen: Miles and Coltrane at 100",
            "date_start": "2026-03-20",
            "date_end": "2026-03-20",
            "venue": "Perelman Theater, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "time": "7:30 PM",
            "price": None,
            "categories": ["jazz"],
            "description": "Rising star pianist Emmet Cohen pays tribute to two giants who transformed American music — Miles Davis and John Coltrane, both born in 1926. Expect reimagined classics from Kind of Blue, A Love Supreme, and beyond.",
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
            "description": "You've seen her holding down the bass on The Late Show with Stephen Colbert — now Endea Owens brings her powerhouse ensemble The Cookout to Philadelphia. A joyful, genre-bending night of jazz, R&B, gospel, and funk.",
            "time": "7:30 PM",
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
            "description": "Grammy Award-winning percussionist Pablo Batista leads 20 big band musicians performing legendary Latin jazz.",
            "time": "7:00 PM",
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
            "description": "Philadelphia's own Christian McBride — eight-time Grammy winner and jazz legend — teams up with the genre-defying bassist Edgar Meyer for an extraordinary double-bass summit. Two virtuosos, one unforgettable night of improvisation.",
            "time": "7:30 PM",
        },
        {
            "title": "Delbert Anderson Quartet: Beyond Belief",
            "date_start": "2026-04-26",
            "date_end": "2026-04-26",
            "venue": "Annenberg Center, Penn Live Arts",
            "source": "Penn Live Arts",
            "source_url": "https://pennlivearts.org/events/",
            "link": "https://pennlivearts.org/events/",
            "price": None,
            "categories": ["jazz"],
            "description": "A world premiere — Navajo trumpeter Delbert Anderson's three-part reflection on the relationship between the Navajo Nation and America.",
            "time": "8:00 PM",
        },

        # ═══════════════════════════════════════════════════════════════════
        # THEATER
        # ═══════════════════════════════════════════════════════════════════
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
            "description": "A bold, contemporary reimagining of Shakespeare's most famous love story. The Arden Theatre strips the tragedy down to its raw emotional core — passion, family loyalty, and the devastating cost of hatred. Intimate staging in Old City.",
            "time": "7:00 PM",
        },
        {
            "title": "The Most Spectacularly Lamentable Trial of Miz Martha Washington",
            "date_start": "2026-03-17",
            "date_end": "2026-04-05",
            "venue": "The Wilma Theater",
            "source": "The Wilma Theater",
            "source_url": "https://www.wilmatheater.org/whats-on/",
            "link": "https://www.wilmatheater.org/whats-on/",
            "price": None,
            "categories": ["theater"],
            "description": "From Pulitzer Prize winner James Ijames — First Lady Martha Washington faces the enslaved people who will be freed upon her death. HotHouse Acting Company.",
            "time": "7:30 PM",
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
            "description": "The international smash hit where a full cast performs Shakespeare — except one actor is genuinely intoxicated. Hilarious, unpredictable, and surprisingly theatrical. Not your English teacher's Shakespeare. Ages 18+.",
            "time": "7:30 PM",
        },
        {
            "title": "A Delicate Balance",
            "date_start": "2026-03-04",
            "date_end": "2026-03-29",
            "venue": "Walnut Street Theatre",
            "source": "Walnut Street Theatre",
            "source_url": "https://www.walnutstreettheatre.org/",
            "link": None,
            "price": "$33 – $247",
            "categories": ["theater"],
            "description": "Edward Albee's Pulitzer Prize-winning play — an absorbing look at the everyday hopes, fears, and secrets we all delicately balance. America's oldest theater.",
            "time": "8:00 PM",
        },
        {
            "title": "The Stinky Cheese Man and Other Fairly Stupid Tales",
            "date_start": "2026-04-08",
            "date_end": "2026-05-31",
            "venue": "Arden Theatre",
            "source": "Arden Theatre",
            "source_url": "https://ardentheatre.org/productions/",
            "link": "https://ardentheatre.org/productions/",
            "price": None,
            "categories": ["theater", "performance"],
            "description": "Arden Children's Theatre presents the beloved tales in a zany, irreverent show for the whole family.",
        },
        {
            "title": "Wilderness Generation",
            "date_start": "2026-04-10",
            "date_end": "2026-05-03",
            "venue": "Suzanne Roberts Theatre",
            "source": "Philadelphia Theatre Company",
            "source_url": "https://www.philatheatreco.org/",
            "link": "https://www.philatheatreco.org/",
            "price": None,
            "categories": ["theater"],
            "description": "World premiere by James Ijames at Philadelphia Theatre Company. A compelling new work exploring identity and belonging.",
            "time": "7:00 PM",
        },
        {
            "title": "Shucked",
            "date_start": "2026-04-21",
            "date_end": "2026-05-03",
            "venue": "Forrest Theatre",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["musical"],
            "description": "The hilarious Tony-nominated Broadway musical. A small-town comedy with heart, corn, and unforgettable laughs.",
            "time": "7:30 PM",
        },
        {
            "title": "1776 The Musical",
            "date_start": "2026-05-05",
            "date_end": "2026-06-07",
            "venue": "Walnut Street Theatre",
            "source": "Walnut Street Theatre",
            "source_url": "https://www.walnutstreettheatre.org/",
            "link": None,
            "price": None,
            "categories": ["musical"],
            "description": "The Tony Award-winning musical about the signing of the Declaration of Independence — in the city where it happened.",
        },

        # ═══════════════════════════════════════════════════════════════════
        # BROADWAY / MUSICALS
        # ═══════════════════════════════════════════════════════════════════
        {
            "title": "TINA – The Tina Turner Musical",
            "date_start": "2026-03-10",
            "date_end": "2026-03-15",
            "venue": "Miller Theater, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": "From $87",
            "categories": ["musical"],
            "description": "From humble beginnings in Nutbush, Tennessee to becoming the Queen of Rock 'n' Roll — TINA chronicles Tina Turner's extraordinary journey of resilience, reinvention, and raw talent. Featuring iconic hits including 'Proud Mary' and 'What's Love Got to Do with It.'",
            "time": "7:30 PM",
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
            "description": "Rodgers & Hammerstein's beloved classic at the Academy of Music. Directed by three-time Tony winner Jack O'Brien. Broadway Series.",
            "time": "7:30 PM",
        },
        {
            "title": "The Outsiders",
            "date_start": "2026-05-26",
            "date_end": "2026-06-07",
            "venue": "Academy of Music",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["musical"],
            "description": "The Tony Award-winning Broadway adaptation of S.E. Hinton's classic novel about rival gangs, brotherhood, and staying gold. Features a stunning original score and the raw emotional intensity that made the story an American classic.",
            "time": "7:30 PM",
        },

        # ═══════════════════════════════════════════════════════════════════
        # BALLET / DANCE
        # ═══════════════════════════════════════════════════════════════════
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
            "description": "Philadelphia Ballet presents Ronald Hynd's celebrated choreography set to Franz Lehár's gorgeous music. A Parisian love story.",
            "time": "7:30 PM",
        },
        {
            "title": "Rennie Harris Puremovement: Losing My Religion",
            "date_start": "2026-03-20",
            "date_end": "2026-03-21",
            "venue": "Annenberg Center, Penn Live Arts",
            "source": "Penn Live Arts",
            "source_url": "https://pennlivearts.org/events/",
            "link": "https://pennlivearts.org/events/",
            "price": None,
            "categories": ["dance"],
            "description": "World premiere fusing street dance and visual art. Rennie Harris abstractly examines our nation's cycle of injustice.",
            "time": "8:00 PM",
        },
        {
            "title": "Explosive: Bold New Works on the Rise",
            "date_start": "2026-04-17",
            "date_end": "2026-04-19",
            "venue": "Perelman Theater, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["dance", "ballet"],
            "description": "Philadelphia Ballet's Spring Residency showcases bold new choreography from emerging and established creators. An intimate showcase at the Perelman Theater where you'll see tomorrow's masterworks taking shape today.",
            "time": "7:30 PM",
        },
        {
            "title": "Paul Taylor Dance Company",
            "date_start": "2026-04-17",
            "date_end": "2026-04-18",
            "venue": "Annenberg Center, Penn Live Arts",
            "source": "Penn Live Arts",
            "source_url": "https://pennlivearts.org/event/PTDC2026",
            "link": "https://pennlivearts.org/event/PTDC2026",
            "price": None,
            "categories": ["dance"],
            "description": "Founded by the legendary Paul Taylor, this company continues to define modern American dance. Expect athletic, emotionally charged choreography that ranges from exuberant to deeply contemplative. A cornerstone of Penn Live Arts' dance season.",
            "time": "8:00 PM",
        },
        {
            "title": "BalletX Spring Series 2026",
            "date_start": "2026-03-27",
            "date_end": "2026-03-29",
            "venue": "Wilma Theater",
            "source": "BalletX",
            "source_url": "https://www.balletx.org/season-and-tickets/",
            "link": "https://www.balletx.org/seasons/spring-series-2026/",
            "price": None,
            "categories": ["ballet", "dance"],
            "description": "BalletX celebrates its 20th anniversary with three works by Matthew Neenan — Show Me, Broke Apart, and more.",
        },
        {
            "title": "Martha Graham Dance Company",
            "date_start": "2026-05-29",
            "date_end": "2026-05-30",
            "venue": "Annenberg Center, Penn Live Arts",
            "source": "Penn Live Arts",
            "source_url": "https://pennlivearts.org/event/MGDC2026",
            "link": "https://pennlivearts.org/event/MGDC2026",
            "price": None,
            "categories": ["dance"],
            "description": "The legendary Martha Graham Dance Company. Includes Tommie-Waheed Evans' 'in case of fire, speak' — co-commissioned with ArtPhilly.",
            "time": "8:00 PM",
        },
        {
            "title": "Dance Theatre of Harlem",
            "date_start": "2026-04-03",
            "date_end": "2026-04-04",
            "venue": "Annenberg Center, Penn Live Arts",
            "source": "Penn Live Arts",
            "source_url": "https://pennlivearts.org/event/DTH2026",
            "link": "https://pennlivearts.org/event/DTH2026",
            "price": None,
            "categories": ["ballet", "dance"],
            "description": "Dance Theatre of Harlem brings its celebrated repertoire blending classical and contemporary ballet.",
            "time": "8:00 PM",
        },

        # ═══════════════════════════════════════════════════════════════════
        # OPERA
        # ═══════════════════════════════════════════════════════════════════
        {
            "title": "Sleepers Awake (World Premiere)",
            "date_start": "2026-04-22",
            "date_end": "2026-04-26",
            "venue": "Academy of Music",
            "source": "Opera Philadelphia",
            "source_url": "https://www.operaphila.org/whats-on/events/",
            "link": "https://www.operaphila.org/whats-on/events/",
            "price": None,
            "categories": ["opera"],
            "description": "World premiere by composer Gregory Spears — inspired by the absurdist retelling of Sleeping Beauty by Robert Walser. Directed by Jenny Koons.",
            "time": "8:00 PM",
        },
        {
            "title": "The Black Clown (Philadelphia Premiere)",
            "date_start": "2026-05-14",
            "date_end": "2026-05-17",
            "venue": "Miller Theater, Kimmel Center",
            "source": "Opera Philadelphia",
            "source_url": "https://www.operaphila.org/whats-on/events/",
            "link": "https://www.operaphila.org/whats-on/events/",
            "price": None,
            "categories": ["opera", "musical"],
            "description": "Philadelphia premiere — a genre-shattering work based on Langston Hughes' searing 1931 poem. Fuses vaudeville, gospel, opera, jazz, and spirituals to tell the story of Black joy and perseverance against impossible odds. A visceral theatrical experience.",
            "time": "8:00 PM",
        },

        # ═══════════════════════════════════════════════════════════════════
        # PENN LIVE ARTS
        # ═══════════════════════════════════════════════════════════════════
        {
            "title": "Alarm Will Sound: American Stories",
            "date_start": "2026-03-13",
            "date_end": "2026-03-13",
            "venue": "Annenberg Center, Penn Live Arts",
            "source": "Penn Live Arts",
            "source_url": "https://pennlivearts.org/events/",
            "link": "https://pennlivearts.org/events/",
            "price": None,
            "categories": ["classical"],
            "description": "Contemporary ensemble Alarm Will Sound with Bora Yoon — diverse works exploring shifting perspectives and identities.",
            "time": "8:00 PM",
        },
        {
            "title": "Ukulele Orchestra of Great Britain",
            "date_start": "2026-04-11",
            "date_end": "2026-04-11",
            "venue": "Annenberg Center, Penn Live Arts",
            "source": "Penn Live Arts",
            "source_url": "https://pennlivearts.org/events/",
            "link": "https://pennlivearts.org/events/",
            "price": None,
            "categories": ["concert"],
            "description": "'The best musical entertainment in the country' — from ABBA to Tchaikovsky, Nirvana to Broadway, all on ukuleles.",
            "time": "8:00 PM",
        },
        {
            "title": "Tiburtina Ensemble: Celestial Harmony",
            "date_start": "2026-04-23",
            "date_end": "2026-04-23",
            "venue": "Annenberg Center, Penn Live Arts",
            "source": "Penn Live Arts",
            "source_url": "https://pennlivearts.org/events/",
            "link": "https://pennlivearts.org/events/",
            "price": None,
            "categories": ["classical"],
            "description": "Prague's Tiburtina Ensemble performs sacred works by Hildegard of Bingen — the 12th-century mystic, composer, and polymath. Ethereal, otherworldly vocal music that has mesmerized audiences for nearly a millennium. A rare and luminous evening.",
            "time": "7:30 PM",
        },

        # ═══════════════════════════════════════════════════════════════════
        # FAMILY / OTHER
        # ═══════════════════════════════════════════════════════════════════
        {
            "title": "Peppa Pig: My First Concert",
            "date_start": "2026-04-04",
            "date_end": "2026-04-04",
            "venue": "Miller Theater, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": "From $63",
            "categories": ["performance"],
            "description": "Peppa Pig comes to life in this interactive concert designed for the youngest music lovers. Sing along, dance, and explore instruments with Peppa and friends. Shows at 1:00 PM and 4:00 PM. Ages 18 months and up.",
        },
        {
            "title": "Shen Yun",
            "date_start": "2026-04-15",
            "date_end": "2026-04-15",
            "venue": "Miller Theater, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "time": "7:30 PM",
            "price": "From $132",
            "categories": ["dance", "performance"],
            "description": "5,000 years of Chinese civilization brought to life through classical Chinese dance and a live orchestra.",
        },
        {
            "title": "Dog Man: The Musical",
            "date_start": "2026-04-25",
            "date_end": "2026-04-26",
            "venue": "Miller Theater, Kimmel Center",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events",
            "price": None,
            "categories": ["musical", "performance"],
            "description": "The hero who is part dog, part police officer leaps off the page and onto the stage in this action-packed musical based on Dav Pilkey's mega-bestselling series. Fun for the whole family. Sensory Friendly Performance available on Sunday, April 26.",
        },
        {
            "title": "Philadelphia Children's Festival",
            "date_start": "2026-05-03",
            "date_end": "2026-05-05",
            "venue": "Annenberg Center, Penn Live Arts",
            "source": "Penn Live Arts",
            "source_url": "https://pennlivearts.org/events/",
            "link": "https://pennlivearts.org/events/",
            "price": None,
            "categories": ["performance"],
            "description": "Family-friendly performances, hands-on activities, and outdoor PLAYground. Includes The Magic School Bus, Bill Blagg Magic, and more.",
        },
        {
            "title": "Girl Dolls: The American Musical",
            "date_start": "2026-05-09",
            "date_end": "2026-05-17",
            "venue": "FringeArts",
            "source": "FringeArts",
            "source_url": "https://fringearts.com/programs/",
            "link": "https://fringearts.com/programs/",
            "price": None,
            "categories": ["theater", "musical"],
            "description": "BYO your favorite doll — The Bearded Ladies Cabaret explores America's obsession with dolls, childhood, and identity.",
        },
        # ═══════════════════════════════════════════════════════════════════
        # CHRIS' JAZZ CAFE — verified events with direct links
        # Source: chrisjazzcafe.com (Squarespace, uses numeric IDs in URLs)
        # ═══════════════════════════════════════════════════════════════════
        {
            "title": "Saxophonists Victor North and Aidan McKeon Sextet featuring Special Guest Trombonist Conrad Herwig",
            "date_start": "2026-04-10",
            "date_end": "2026-04-10",
            "venue": "Chris' Jazz Cafe",
            "source": "Chris' Jazz Cafe",
            "source_url": "https://www.chrisjazzcafe.com/events",
            "link": "https://www.chrisjazzcafe.com/shows/355335",
            "time": "7:30 PM",
            "price": "$25",
            "categories": ["jazz"],
            "description": "A powerful sextet led by saxophonists Victor North and Aidan McKeon with special guest Conrad Herwig — a 4-time Grammy-nominated New York jazz trombonist who has recorded 26 albums as a leader. Two shows at 7:30 and 9:30.",
        },
        {
            "title": "James Santangelo's Late Night Jam",
            "date_start": "2026-04-11",
            "date_end": "2026-04-11",
            "venue": "Chris' Jazz Cafe",
            "source": "Chris' Jazz Cafe",
            "source_url": "https://www.chrisjazzcafe.com/events",
            "link": "https://www.chrisjazzcafe.com/shows/363351",
            "time": "11:00 PM",
            "price": "$15",
            "categories": ["jazz"],
            "description": "James Santangelo 'is a force to be reckoned with on piano' and is a committed musician on the Philadelphia jazz scene. A late-night jam session open to all.",
        },
        {
            "title": "Duane Eubanks Celebrates Lee Morgan",
            "date_start": "2026-04-22",
            "date_end": "2026-04-22",
            "venue": "Chris' Jazz Cafe",
            "source": "Chris' Jazz Cafe",
            "source_url": "https://www.chrisjazzcafe.com/events",
            "link": "https://www.chrisjazzcafe.com/events/131523",
            "time": "7:30 PM",
            "price": "$35",
            "categories": ["jazz"],
            "description": "The Philadelphia Jazz Archive presents a special fundraiser concert headlined by acclaimed trumpeter Duane Eubanks and his band, performing an electrifying tribute to Lee Morgan. All proceeds support the preservation of Philadelphia's rich jazz legacy.",
        },
        {
            "title": "Oliver Mayman + Jam Session",
            "date_start": "2026-04-24",
            "date_end": "2026-04-24",
            "venue": "Chris' Jazz Cafe",
            "source": "Chris' Jazz Cafe",
            "source_url": "https://www.chrisjazzcafe.com/events",
            "link": "https://www.chrisjazzcafe.com/shows/363349",
            "time": "11:00 PM",
            "price": "$15",
            "categories": ["jazz"],
            "description": "Philadelphia-based vibraphonist, composer, and educator Oliver Mayman — originally from Ann Arbor, MI — has become a distinguished voice on the instrument. Late-night jam session follows.",
        },
        {
            "title": "Trumpeter James McGovern and His Quintet",
            "date_start": "2026-04-30",
            "date_end": "2026-04-30",
            "venue": "Chris' Jazz Cafe",
            "source": "Chris' Jazz Cafe",
            "source_url": "https://www.chrisjazzcafe.com/events",
            "link": "https://www.chrisjazzcafe.com/shows/363632",
            "time": "10:30 PM",
            "price": "$15",
            "categories": ["jazz"],
            "description": "Trumpeter James McGovern leads his quintet at Chris' Jazz Cafe. McGovern is a rising talent from Temple University's jazz program, bringing fresh energy to the Philadelphia jazz scene.",
        },
        {
            "title": "Saxophonist Christian Ertl and His Quartet",
            "date_start": "2026-04-17",
            "date_end": "2026-04-17",
            "venue": "Chris' Jazz Cafe",
            "source": "Chris' Jazz Cafe",
            "source_url": "https://www.chrisjazzcafe.com/events",
            "link": "https://www.chrisjazzcafe.com/events/132133",
            "time": "7:30 PM",
            "price": "$15",
            "categories": ["jazz"],
            "description": "Christian Ertl is an alto saxophonist, bandleader, composer, and arranger originally from Waukee, Iowa, now living and performing in Philadelphia. Dinner & Show available at $70; VIP at $90.",
        },
        {
            "title": "Drummer Willie Jones III and His Quartet",
            "date_start": "2026-04-03",
            "date_end": "2026-04-03",
            "venue": "Chris' Jazz Cafe",
            "source": "Chris' Jazz Cafe",
            "source_url": "https://www.chrisjazzcafe.com/events",
            "link": "https://www.chrisjazzcafe.com/events/126357",
            "time": "7:30 PM",
            "price": "$30",
            "categories": ["jazz"],
            "description": "Willie Jones III is 'one of the world's leading jazz drummers,' honoring influences like Philly Joe Jones, Art Blakey, and Billy Higgins. With Justin Robinson (alto sax), Danton Boller (bass), and Tyler Bullock (piano). Two shows at 7:30 and 9:30.",
        },
        {
            "title": "Vocalist Jackie Johnson and Her Band",
            "date_start": "2026-04-05",
            "date_end": "2026-04-05",
            "venue": "Chris' Jazz Cafe",
            "source": "Chris' Jazz Cafe",
            "source_url": "https://www.chrisjazzcafe.com/events",
            "link": "https://www.chrisjazzcafe.com/events/128944",
            "time": "7:30 PM",
            "price": "$15",
            "categories": ["jazz"],
            "description": "Jazz vocalist Jackie Johnson brings her band to Chris' Jazz Cafe for an evening of standards and original compositions. Two sets at 7:30 and 9:00 PM.",
        },
        {
            "title": "Joe Block and His Trio with Special Guest Georgia Heers",
            "date_start": "2026-04-12",
            "date_end": "2026-04-12",
            "venue": "Chris' Jazz Cafe",
            "source": "Chris' Jazz Cafe",
            "source_url": "https://www.chrisjazzcafe.com/events",
            "link": "https://www.chrisjazzcafe.com/shows/342181",
            "time": "7:30 PM",
            "price": "$15",
            "categories": ["jazz"],
            "description": "Pianist Joe Block leads his trio with a special guest appearance by vocalist Georgia Heers. An intimate evening of jazz at Philadelphia's premier jazz club.",
        },
        {
            "title": "The Oscar Beesley Quartet",
            "date_start": "2026-04-09",
            "date_end": "2026-04-09",
            "venue": "Chris' Jazz Cafe",
            "source": "Chris' Jazz Cafe",
            "source_url": "https://www.chrisjazzcafe.com/events",
            "link": "https://www.chrisjazzcafe.com/shows/360150",
            "time": "7:30 PM",
            "price": "$15",
            "categories": ["jazz"],
            "description": "The Oscar Beesley Quartet performs an evening of original compositions and jazz standards at Chris' Jazz Cafe.",
        },
        {
            "title": "Jonathan Daddis and His Band",
            "date_start": "2026-04-16",
            "date_end": "2026-04-16",
            "venue": "Chris' Jazz Cafe",
            "source": "Chris' Jazz Cafe",
            "source_url": "https://www.chrisjazzcafe.com/events",
            "link": "https://www.chrisjazzcafe.com/shows/346275",
            "time": "7:30 PM",
            "price": "$15",
            "categories": ["jazz"],
            "description": "Saxophonist Jonathan Daddis leads his band in an evening of hard bop and modern jazz at Philadelphia's beloved Chris' Jazz Cafe.",
        },
        {
            "title": "Vocalist Martina Barta and the Philly All-Star Quartet",
            "date_start": "2026-04-19",
            "date_end": "2026-04-19",
            "venue": "Chris' Jazz Cafe",
            "source": "Chris' Jazz Cafe",
            "source_url": "https://www.chrisjazzcafe.com/events",
            "link": "https://www.chrisjazzcafe.com/shows/340902",
            "time": "7:30 PM",
            "price": "$25",
            "categories": ["jazz"],
            "description": "Czech-born jazz vocalist Martina Barta teams up with the Philly All-Star Quartet for an intimate evening of jazz vocal artistry at Chris' Jazz Cafe.",
        },
        # ═══════════════════════════════════════════════════════════════════
        # ADDITIONAL ENSEMBLE ARTS / PHILA ORCHESTRA EVENTS
        # ═══════════════════════════════════════════════════════════════════
        {
            "title": "Between the Notes: Sleepers Awake Virtual Lecture",
            "date_start": "2026-04-07",
            "date_end": "2026-04-07",
            "venue": "Zoom",
            "source": "Ensemble Arts Philly",
            "source_url": "https://www.ensembleartsphilly.org/tickets-and-events",
            "link": "https://www.ensembleartsphilly.org/tickets-and-events/events/between-the-notes-sleepers-awake",
            "time": "12:00 PM",
            "price": "Free",
            "categories": ["classical", "performance"],
            "description": "A free virtual lecture exploring the themes and music behind Opera Philadelphia's world premiere Sleepers Awake. Join the conversation with the creative team as they discuss the making of this groundbreaking new work by Gregory Spears.",
        },
        # ═══════════════════════════════════════════════════════════════════
        # EXHIBITIONS — ART
        # ═══════════════════════════════════════════════════════════════════
        {
            "title": "Noah Davis",
            "date_start": "2026-01-24",
            "date_end": "2026-04-26",
            "venue": "Philadelphia Museum of Art",
            "source": "Philadelphia Museum of Art",
            "source_url": "https://philamuseum.org/exhibitions",
            "price": None,
            "categories": ["exhibition"],
            "description": "A landmark survey bringing together over 60 works charting Noah Davis's (1983-2015) practice. Davis's luminous paintings blend figuration and abstraction, drawing on art history and personal memory.",
            "time": None,
        },
        {
            "title": "A Nation of Artists",
            "date_start": "2026-04-12",
            "date_end": "2027-07-05",
            "venue": "Philadelphia Museum of Art",
            "source": "Philadelphia Museum of Art",
            "source_url": "https://philamuseum.org/exhibitions",
            "price": None,
            "categories": ["exhibition"],
            "description": "The most expansive presentation of American art ever mounted in Philadelphia. Featuring more than 1,000 works across PMA and PAFA, celebrating the museum's 150th anniversary and the nation's 250th.",
            "time": None,
        },
        {
            "title": "Rising Up: Rocky and the Making of Monuments",
            "date_start": "2026-04-25",
            "date_end": "2026-08-02",
            "venue": "Philadelphia Museum of Art",
            "source": "Philadelphia Museum of Art",
            "source_url": "https://philamuseum.org/exhibitions",
            "price": None,
            "categories": ["exhibition"],
            "description": "Timed to the 50th anniversary of the Rocky franchise, this major exhibition explores the creation, context, and significance of monuments through the lens of Philadelphia's most iconic statue.",
            "time": None,
        },
        {
            "title": "Workshop of the World: Arts and Crafts in Philadelphia",
            "date_start": "2026-07-05",
            "date_end": "2026-10-18",
            "venue": "Philadelphia Museum of Art",
            "source": "Philadelphia Museum of Art",
            "source_url": "https://philamuseum.org/exhibitions",
            "price": None,
            "categories": ["exhibition"],
            "description": "An exploration of Philadelphia's rich tradition in the arts and crafts movement, showcasing decorative arts, furniture, textiles, and metalwork from the city's workshops.",
            "time": None,
        },
        {
            "title": "Marcel Duchamp",
            "date_start": "2026-10-10",
            "date_end": "2027-01-31",
            "venue": "Philadelphia Museum of Art",
            "source": "Philadelphia Museum of Art",
            "source_url": "https://philamuseum.org/exhibitions",
            "price": None,
            "categories": ["exhibition"],
            "description": "The first North American retrospective of Marcel Duchamp's work in over 50 years. Spanning painting, sculpture, film, photography, drawings, and printed matter across six decades of the artist's multifaceted career.",
            "time": None,
        },
        {
            "title": "Henri Matisse at the Barnes",
            "date_start": "2026-04-12",
            "date_end": "2026-08-09",
            "venue": "Barnes Foundation",
            "source": "Barnes Foundation",
            "source_url": "https://www.barnesfoundation.org/whats-on/exhibitions",
            "price": None,
            "categories": ["exhibition"],
            "description": "A tour of the Barnes's renowned collection of paintings by Henri Matisse, exploring how a visit to the Barnes collection was a pivotal moment in the artist's career and transformed his approach to color and form.",
            "time": None,
        },
        {
            "title": "PECO Free First Sunday: April",
            "date_start": "2026-04-05",
            "date_end": "2026-04-05",
            "venue": "Barnes Foundation",
            "source": "Barnes Foundation",
            "source_url": "https://www.barnesfoundation.org/whats-on",
            "price": "Free",
            "categories": ["exhibition"],
            "description": "Free admission on the first Sunday with family art activities, performances by Equinox from the Philadelphia High School for Creative and Performing Arts, storytime, and free gallery access. April is Philly Jazz Month.",
            "time": "10:00 AM",
        },
        {
            "title": "PECO Free First Sunday: May",
            "date_start": "2026-05-03",
            "date_end": "2026-05-03",
            "venue": "Barnes Foundation",
            "source": "Barnes Foundation",
            "source_url": "https://www.barnesfoundation.org/whats-on",
            "price": "Free",
            "categories": ["exhibition"],
            "description": "Free admission and family-friendly activities celebrating the 10th annual Art of Math challenge, where students design and build 3D scale models of paintings from the collection as a STEAM-based challenge.",
            "time": "10:00 AM",
        },
        # ═══════════════════════════════════════════════════════════════════
        # EXHIBITIONS & EVENTS — SCIENCE
        # ═══════════════════════════════════════════════════════════════════
        {
            "title": "Universal Theme Parks: The Exhibition",
            "date_start": "2026-02-14",
            "date_end": "2026-09-07",
            "venue": "The Franklin Institute",
            "source": "The Franklin Institute",
            "source_url": "https://fi.edu/en/exhibits-experiences",
            "price": "$47",
            "categories": ["exhibition", "science"],
            "description": "World premiere spanning 18,000 square feet with eight themed galleries, 25 interactive experiences, and over 100 original artifacts from Universal's iconic theme parks. Extended evening hours Thu-Sat.",
            "time": None,
        },
        {
            "title": "Science After Hours: Rhythm & Booms",
            "date_start": "2026-04-10",
            "date_end": "2026-04-10",
            "venue": "The Franklin Institute",
            "source": "The Franklin Institute",
            "source_url": "https://fi.edu/en/events-calendar",
            "price": None,
            "categories": ["science"],
            "description": "Dance your way through exhibits, sip drinks, and dive into activities inspired by music and sound, then experience explosive live science demonstrations. Ages 21+ only.",
            "time": "7:30 PM",
        },
        {
            "title": "Astronomy Day 2026",
            "date_start": "2026-04-25",
            "date_end": "2026-04-25",
            "venue": "The Franklin Institute",
            "source": "The Franklin Institute",
            "source_url": "https://fi.edu/en/events-calendar",
            "price": None,
            "categories": ["science"],
            "description": "Celebrate International Astronomy Day across four floors including the Wondrous Space exhibit, Fels Planetarium, and the Holt & Miller Observatory. Special activities and expert talks throughout the day.",
            "time": "11:00 AM",
        },
        {
            "title": "Ancient Egypt in Watercolors: Paintings and Artifacts from Dra Abu el-Naga",
            "date_start": "2026-02-28",
            "date_end": "2026-11-30",
            "venue": "Penn Museum",
            "source": "Penn Museum",
            "source_url": "https://www.penn.museum/on-view/galleries-exhibitions",
            "price": None,
            "categories": ["exhibition"],
            "description": "Century-old watercolors by Egyptian artist Ahmed Yousef capturing New Kingdom tomb chapels from Dra Abu el-Naga, Thebes. First rotation through June; second rotation from July through November ahead of the Egypt Galleries grand reopening.",
            "time": None,
        },
        {
            "title": "Botany of Nations",
            "date_start": "2026-03-28",
            "date_end": "2026-09-13",
            "venue": "Academy of Natural Sciences",
            "source": "Academy of Natural Sciences",
            "source_url": "https://ansp.org/exhibits/exhibits/",
            "price": None,
            "categories": ["exhibition", "science"],
            "description": "The Lewis and Clark expedition retold through an Indigenous lens. Plants act as portals to under-shared stories, cultures, and sciences of the Indigenous peoples encountered on the journey. Created in collaboration with Indigenous-led nonprofit Local Contexts.",
            "time": None,
        },
        {
            "title": "Revolutionary Botany",
            "date_start": "2026-01-01",
            "date_end": "2026-12-31",
            "venue": "Mütter Museum",
            "source": "Mütter Museum",
            "source_url": "https://muttermuseum.org/events/",
            "price": None,
            "categories": ["exhibition", "science"],
            "description": "Tracing the evolution of medicine in America from medicinal plants to the modern pharmacy. Part of the Mütter Museum's 2026 programming celebrating medical milestones throughout the past 250 years.",
            "time": None,
        },
        {
            "title": "Legionnaires' Disease: The Philadelphia Outbreak",
            "date_start": "2026-05-01",
            "date_end": "2026-12-31",
            "venue": "Mütter Museum",
            "source": "Mütter Museum",
            "source_url": "https://muttermuseum.org/events/",
            "price": None,
            "categories": ["exhibition", "science"],
            "description": "Examining Philadelphia's headline-grabbing 1976 outbreak of Legionnaires' Disease during the Bicentennial — the mysterious illness that baffled scientists and changed public health forever.",
            "time": None,
        },
        {
            "title": "Creating a City of Medicine",
            "date_start": "2026-06-01",
            "date_end": "2026-12-31",
            "venue": "Mütter Museum",
            "source": "Mütter Museum",
            "source_url": "https://muttermuseum.org/events/",
            "price": None,
            "categories": ["exhibition", "science"],
            "description": "Philadelphia's role in the evolution of American medicine and medical schooling, from the nation's first hospital and medical school to groundbreaking surgical innovations.",
            "time": None,
        },
        # ═══════════════════════════════════════════════════════════════════
        # LECTURES & TALKS
        # ═══════════════════════════════════════════════════════════════════
        {
            "title": "Science on Tap: Monthly Talk",
            "date_start": "2026-04-13",
            "date_end": "2026-04-13",
            "venue": "National Mechanics",
            "source": "Science on Tap",
            "source_url": "https://www.scienceontapphilly.com/events",
            "price": "Free",
            "categories": ["lecture", "science"],
            "description": "Monthly science talk at National Mechanics bar. Organized by a consortium of six Philadelphia science museums including the Academy of Natural Sciences, Penn Museum, Mütter Museum, and Science History Institute. Second Monday of every month since 2009.",
            "time": "6:00 PM",
        },
        {
            "title": "Science on Tap: May",
            "date_start": "2026-05-11",
            "date_end": "2026-05-11",
            "venue": "National Mechanics",
            "source": "Science on Tap",
            "source_url": "https://www.scienceontapphilly.com/events",
            "price": "Free",
            "categories": ["lecture", "science"],
            "description": "Monthly science talk at National Mechanics bar, presented by a consortium of six Philadelphia science museums. Free and open to the public.",
            "time": "6:00 PM",
        },
        {
            "title": "Past, Peril, and Preservation in Syria",
            "date_start": "2026-04-09",
            "date_end": "2026-04-30",
            "venue": "Penn Museum",
            "source": "Penn Museum",
            "source_url": "https://www.penn.museum/",
            "price": None,
            "categories": ["lecture"],
            "description": "A 4-Thursday online series with Dr. Michael Danti exploring the intersection of cultural heritage, conflict, and preservation efforts in Syria. Join virtually for in-depth discussion of archaeological sites under threat.",
            "time": "6:00 PM",
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

        # Auto-generate direct event page links (replaces generic listing page URLs)
        current_link = ev.get("link") or ""
        source_url = ev.get("source_url", "")
        # If link is missing, None, or same as source_url (generic listing page), generate a better one
        if not current_link or current_link == source_url:
            ev["link"] = _auto_link(ev)

    return events
