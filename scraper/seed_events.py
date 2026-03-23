#!/usr/bin/env python3
"""
Seed Events — verified Philadelphia performing arts events from public sources.

These are real, verified events from Visit Philadelphia, Ensemble Arts Philly,
Theatre Philadelphia, Penn Live Arts, Opera Philadelphia, and other public listings.
They serve as baseline data when the live scraper cannot reach venue websites.

Last verified: 2026-03-23 via visitphilly.com, ensembleartsphilly.org,
theatrephiladelphia.org, pennlivearts.org, operaphila.org, walnutstreettheatre.org,
philadelphiaballet.org, balletx.org
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
