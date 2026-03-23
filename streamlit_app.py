import streamlit as st
import json
from datetime import datetime, timedelta
from pathlib import Path
import urllib.parse
from collections import Counter

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PhillyCulture — Philadelphia Performing Arts",
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
    "performance": "#a0aec0",
}

CAT_ICONS = {
    "musical": "🎵", "theater": "🎭", "dance": "💃", "ballet": "🩰",
    "jazz": "🎷", "classical": "🎻", "opera": "🎤", "concert": "🎶",
    "performance": "🎪",
}

CATEGORIES = ["all", "musical", "theater", "dance", "ballet", "jazz", "classical", "opera"]


# ── Load seed events as fallback ─────────────────────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).parent / "scraper"))
try:
    from seed_events import get_seed_events
    FALLBACK_EVENTS = get_seed_events()
except Exception:
    FALLBACK_EVENTS = []


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
        return data
    except Exception:
        return {
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "sources": sorted({e["source"] for e in FALLBACK_EVENTS}),
            "events": FALLBACK_EVENTS,
            "scrape_report": {"successes": ["Using seed data"], "failures": [], "warnings": []},
        }


# ── Helpers ──────────────────────────────────────────────────────────────────
def get_month_key(iso_str):
    try:
        return datetime.strptime(iso_str, "%Y-%m-%d").strftime("%B %Y")
    except Exception:
        return "Unknown"


def is_this_week(event):
    today = datetime.now().date()
    end_of_week = today + timedelta(days=(6 - today.weekday()))
    try:
        start = datetime.strptime(event["date_start"], "%Y-%m-%d").date()
        end = datetime.strptime(event.get("date_end") or event["date_start"], "%Y-%m-%d").date()
    except Exception:
        return False
    return start <= end_of_week and end >= today


def is_this_weekend(event):
    today = datetime.now().date()
    days_to_fri = (4 - today.weekday()) % 7
    friday = today + timedelta(days=days_to_fri)
    sunday = friday + timedelta(days=2)
    try:
        start = datetime.strptime(event["date_start"], "%Y-%m-%d").date()
        end = datetime.strptime(event.get("date_end") or event["date_start"], "%Y-%m-%d").date()
    except Exception:
        return False
    return start <= sunday and end >= friday


def is_happening_now(event):
    today_str = datetime.now().strftime("%Y-%m-%d")
    return (event.get("date_start", "") <= today_str
            and (event.get("date_end") or event.get("date_start", "")) >= today_str)


def is_free(event):
    price = (event.get("price") or "").lower().strip()
    return price in ("free", "$0", "0")


def days_until(event):
    try:
        start = datetime.strptime(event["date_start"], "%Y-%m-%d").date()
        delta = (start - datetime.now().date()).days
        if delta < 0:
            return "Now"
        elif delta == 0:
            return "Today"
        elif delta == 1:
            return "Tomorrow"
        elif delta < 7:
            return f"In {delta} days"
        else:
            return f"In {delta // 7}w"
    except Exception:
        return ""


def gcal_url(event):
    start = event.get("date_start", "").replace("-", "")
    end_raw = event.get("date_end") or event.get("date_start", "")
    try:
        end_dt = datetime.strptime(end_raw, "%Y-%m-%d") + timedelta(days=1)
        end = end_dt.strftime("%Y%m%d")
    except Exception:
        end = start
    params = urllib.parse.urlencode({
        "action": "TEMPLATE",
        "text": event.get("title", ""),
        "dates": f"{start}/{end}",
        "details": event.get("description", ""),
        "location": event.get("venue", ""),
    })
    return f"https://calendar.google.com/calendar/render?{params}"


def maps_url(event):
    venue = event.get("venue", "")
    return f"https://www.google.com/maps/search/{urllib.parse.quote(venue + ' Philadelphia PA')}"


def category_badge_html(cat):
    color = CAT_COLORS.get(cat, "#a0aec0")
    icon = CAT_ICONS.get(cat, "")
    return f'<span style="background:{color}22;color:{color};padding:3px 12px;border-radius:12px;font-size:0.78rem;font-weight:600;margin-right:4px;text-transform:capitalize;">{icon} {cat}</span>'


def urgency_badge(event):
    label = days_until(event)
    if not label:
        return ""
    if label in ("Today", "Now"):
        return f'<span style="background:#ff6b9d22;color:#ff6b9d;padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:700;margin-left:8px">🔴 {label}</span>'
    elif label == "Tomorrow":
        return f'<span style="background:#ffa44f22;color:#ffa44f;padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:700;margin-left:8px">🟠 {label}</span>'
    else:
        return f'<span style="background:#4fd1c522;color:#4fd1c5;padding:3px 10px;border-radius:12px;font-size:0.75rem;font-weight:600;margin-left:8px">{label}</span>'


# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@300;400;500;600;700&display=swap');

.stApp { font-family: 'Inter', sans-serif; }

/* Hide default Streamlit elements for cleaner look */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
div[data-testid="stDecoration"] {display: none;}

.main-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.4rem;
    margin-bottom: -0.3rem;
    line-height: 1.2;
}
.main-title .highlight { color: #7c6aff; }
.subtitle {
    color: #8888a0;
    font-size: 0.82rem;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    margin-bottom: 1rem;
}

/* Stats */
.stat-box {
    background: #16161f;
    border: 1px solid #23233080;
    border-radius: 12px;
    padding: 0.8rem 1rem;
    text-align: center;
}
.stat-value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #7c6aff;
    line-height: 1.2;
}
.stat-label {
    font-size: 0.72rem;
    color: #8888a0;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Event cards */
.event-card {
    background: #16161f;
    border: 1px solid #23233080;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 0.4rem;
    transition: all 0.2s ease;
}
.event-card:hover {
    border-color: #7c6aff55;
    box-shadow: 0 4px 20px rgba(124, 106, 255, 0.08);
}
.event-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: #e8e8f0;
    margin-bottom: 0.25rem;
}
.event-meta {
    color: #8888a0;
    font-size: 0.86rem;
    margin-bottom: 0.3rem;
}
.event-venue { color: #7c6aff; font-weight: 500; }
.event-desc {
    color: #aaaabc;
    font-size: 0.88rem;
    line-height: 1.5;
    margin-top: 0.4rem;
}
.price-tag {
    background: #68d39122;
    color: #68d391;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.78rem;
    font-weight: 600;
}
.month-header {
    font-family: 'Playfair Display', serif;
    font-size: 1.35rem;
    color: #e8e8f0;
    margin-top: 1.5rem;
    margin-bottom: 0.6rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #23233080;
}

/* Spotlight */
.spotlight-card {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border: 1px solid #7c6aff44;
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    height: 100%;
}
.spotlight-label {
    color: #7c6aff;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 0.4rem;
}

/* Coming up next */
.coming-up {
    background: #12121a;
    border: 1px solid #23233080;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin-bottom: 0.3rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* Analytics bar */
.analytics-bar {
    background: #16161f;
    border: 1px solid #23233080;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    margin-bottom: 0.8rem;
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

div[data-testid="stHorizontalBlock"] > div { padding: 0 0.3rem; }

/* Make link buttons smaller */
.stLinkButton > a {
    font-size: 0.82rem !important;
    padding: 0.3rem 0.6rem !important;
}
</style>
""", unsafe_allow_html=True)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    data = load_events()
    all_events = data.get("events", [])
    sources = data.get("sources", [])
    last_updated = data.get("last_updated", "")

    # ── Header ───────────────────────────────────────────────────────────────
    col_title, col_spacer, col_s1, col_s2, col_s3, col_refresh = st.columns([4, 0.5, 1, 1, 1, 1])
    with col_title:
        st.markdown('<div class="main-title">Philly<span class="highlight">Culture</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle">Your guide to Philadelphia\'s performing arts</div>', unsafe_allow_html=True)
    with col_s1:
        st.markdown(f'<div class="stat-box"><div class="stat-value">{len(all_events)}</div><div class="stat-label">Events</div></div>', unsafe_allow_html=True)
    with col_s2:
        now_playing = sum(1 for e in all_events if is_happening_now(e))
        st.markdown(f'<div class="stat-box"><div class="stat-value">{now_playing}</div><div class="stat-label">Now Playing</div></div>', unsafe_allow_html=True)
    with col_s3:
        st.markdown(f'<div class="stat-box"><div class="stat-value">{len(sources)}</div><div class="stat-label">Sources</div></div>', unsafe_allow_html=True)
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ── Last updated line ────────────────────────────────────────────────────
    try:
        dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        updated_str = dt.strftime("%b %d, %Y at %I:%M %p")
    except Exception:
        updated_str = "—"
    st.caption(f"Data updated: {updated_str}")

    st.divider()

    # ── Filters ──────────────────────────────────────────────────────────────
    # Iteration 2: Better filter UX with pills-style category selection
    col_cat, col_time, col_search, col_sort = st.columns([3, 2, 2, 1])

    with col_cat:
        category = st.selectbox(
            "Category",
            CATEGORIES,
            format_func=lambda x: (CAT_ICONS.get(x, "🎯") + " " + x.capitalize()) if x != "all" else "🎯 All Categories",
            label_visibility="collapsed",
        )

    with col_time:
        time_filter = st.selectbox(
            "Time",
            ["all", "this_week", "this_weekend", "free"],
            format_func=lambda x: {
                "all": "📅 All Dates",
                "this_week": "📅 This Week",
                "this_weekend": "🎉 This Weekend",
                "free": "🆓 Free Events",
            }.get(x, x),
            label_visibility="collapsed",
        )

    with col_search:
        search = st.text_input("Search", placeholder="Search events, venues...", label_visibility="collapsed")

    with col_sort:
        sort_by = st.selectbox(
            "Sort",
            ["date", "name", "venue"],
            format_func=lambda x: {"date": "By Date", "name": "By Name", "venue": "By Venue"}.get(x, x),
            label_visibility="collapsed",
        )

    # ── Apply filters ────────────────────────────────────────────────────────
    filtered = list(all_events)

    if category != "all":
        filtered = [e for e in filtered if category in e.get("categories", [])]

    if time_filter == "this_week":
        filtered = [e for e in filtered if is_this_week(e)]
    elif time_filter == "this_weekend":
        filtered = [e for e in filtered if is_this_weekend(e)]
    elif time_filter == "free":
        filtered = [e for e in filtered if is_free(e)]

    if search:
        q = search.lower()
        filtered = [
            e for e in filtered
            if q in e.get("title", "").lower()
            or q in e.get("venue", "").lower()
            or q in e.get("description", "").lower()
            or q in e.get("source", "").lower()
        ]

    if sort_by == "name":
        filtered.sort(key=lambda e: e.get("title", "").lower())
    elif sort_by == "venue":
        filtered.sort(key=lambda e: e.get("venue", "").lower())
    else:
        filtered.sort(key=lambda e: e.get("date_start", "9999"))

    # ── Iteration 3: Category overview bar ───────────────────────────────────
    all_cats = []
    for e in all_events:
        all_cats.extend(e.get("categories", []))
    cat_counts = Counter(all_cats)
    if cat_counts:
        chips_html = ""
        for cat in ["theater", "musical", "jazz", "classical", "ballet", "dance", "opera", "concert", "performance"]:
            count = cat_counts.get(cat, 0)
            if count > 0:
                color = CAT_COLORS.get(cat, "#a0aec0")
                icon = CAT_ICONS.get(cat, "")
                chips_html += f'<span class="cat-chip" style="background:{color}18;color:{color};border:1px solid {color}44">{icon} {cat.capitalize()} <strong>{count}</strong></span>'
        if chips_html:
            st.markdown(f'<div style="margin-bottom:1rem">{chips_html}</div>', unsafe_allow_html=True)

    # ── Spotlight: What's Happening Now ───────────────────────────────────────
    tonight = [e for e in all_events if is_happening_now(e)]
    if tonight:
        st.markdown("#### 🔴 Happening Now")
        cols = st.columns(min(len(tonight), 4))
        for i, event in enumerate(tonight[:4]):
            with cols[i]:
                badges = "".join(category_badge_html(c) for c in event.get("categories", []))
                price_html = f' <span class="price-tag">{event["price"]}</span>' if event.get("price") else ""
                st.markdown(f"""
                <div class="spotlight-card">
                    <div class="spotlight-label">Now Playing</div>
                    <div class="event-title">{event['title']}</div>
                    <div class="event-meta"><span class="event-venue">{event['venue']}</span></div>
                    <div class="event-meta">{event.get('date_display', '')}{price_html}</div>
                    <div style="margin-top:0.5rem">{badges}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("")

    # ── Iteration 4: Coming Up Next section ──────────────────────────────────
    upcoming = [e for e in all_events if not is_happening_now(e)]
    upcoming.sort(key=lambda e: e.get("date_start", "9999"))
    next_up = upcoming[:3]
    if next_up:
        st.markdown("#### Coming Up Next")
        for event in next_up:
            badge = urgency_badge(event)
            cats = "".join(category_badge_html(c) for c in event.get("categories", []))
            st.markdown(f"""
            <div class="coming-up">
                <div>
                    <span style="color:#e8e8f0;font-weight:600">{event['title']}</span>
                    <span style="color:#8888a0;font-size:0.85rem"> at <span class="event-venue">{event['venue']}</span></span>
                    {badge}
                </div>
                <div style="color:#8888a0;font-size:0.85rem;white-space:nowrap">{event.get('date_display','')}</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("")

    st.divider()

    # ── Results count ────────────────────────────────────────────────────────
    st.caption(f"Showing {len(filtered)} of {len(all_events)} events")

    # ── Event listing grouped by month ───────────────────────────────────────
    if not filtered:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#8888a0">
            <div style="font-size:3rem;margin-bottom:1rem">🔍</div>
            <h3 style="color:#e8e8f0;margin-bottom:0.5rem">No events match your filters</h3>
            <p>Try adjusting your category, date range, or search query.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    current_month = None
    for event in filtered:
        month = get_month_key(event.get("date_start", ""))
        if month != current_month:
            current_month = month
            st.markdown(f'<div class="month-header">{month}</div>', unsafe_allow_html=True)

        badges = "".join(category_badge_html(c) for c in event.get("categories", []))
        price_html = f'<span class="price-tag">{event["price"]}</span>' if event.get("price") else ""
        time_html = f' · {event["time"]}' if event.get("time") else ""
        urg = urgency_badge(event)

        st.markdown(f"""
        <div class="event-card">
            <div class="event-title">{event['title']}{urg}</div>
            <div class="event-meta">
                <span class="event-venue">{event['venue']}</span>{time_html}
            </div>
            <div class="event-meta">
                {event.get('date_display', '')}{' · ' if event.get('price') else ''}{price_html}
            </div>
            <div class="event-desc">{event.get('description', '')}</div>
            <div style="margin-top:0.6rem">{badges}</div>
        </div>
        """, unsafe_allow_html=True)

        # Iteration 1: Cleaner action buttons with better layout
        btn_cols = st.columns([1, 1, 1, 5])
        with btn_cols[0]:
            if event.get("link"):
                st.link_button("🎟 Tickets", event["link"], use_container_width=True)
        with btn_cols[1]:
            st.link_button("📅 Add to Cal", gcal_url(event), use_container_width=True)
        with btn_cols[2]:
            st.link_button("📍 Map", maps_url(event), use_container_width=True)

    # ── Iteration 5: Analytics section in sidebar ────────────────────────────
    with st.sidebar:
        st.markdown("### 📊 Analytics")
        st.markdown(f"**{len(all_events)}** events across **{len(sources)}** sources")
        st.markdown("")

        # Category breakdown
        st.markdown("**By Category**")
        for cat in sorted(cat_counts.keys(), key=lambda c: -cat_counts[c]):
            color = CAT_COLORS.get(cat, "#a0aec0")
            icon = CAT_ICONS.get(cat, "")
            pct = cat_counts[cat] / len(all_events) * 100 if all_events else 0
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
        venue_counts = Counter(e.get("venue", "Unknown") for e in all_events)
        for venue, count in venue_counts.most_common(5):
            st.markdown(f'<div style="color:#e8e8f0;font-size:0.9rem">{venue} <span style="color:#7c6aff;font-weight:600">({count})</span></div>', unsafe_allow_html=True)

        st.markdown("")
        st.markdown("**Data Sources**")
        for source in sorted(sources):
            st.markdown(f'<div style="color:#8888a0;font-size:0.85rem">• {source}</div>', unsafe_allow_html=True)

    # ── Footer ───────────────────────────────────────────────────────────────
    st.divider()
    st.markdown(f"""
    <div style="text-align:center;color:#55556a;padding:1rem;font-size:0.85rem">
        <strong>PhillyCulture</strong> — Aggregating {len(sources)} Philadelphia performing arts sources<br>
        Data from verified public event listings. Not affiliated with any venue.
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
