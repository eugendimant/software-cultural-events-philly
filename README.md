# PhillyCulture

Philadelphia Cultural Events Tracker — aggregating performing arts from 14 local venues.

## Features (15 iterations)

- **Event aggregation** from 14 Philadelphia performing arts venues
- **Category filtering** — musicals, theater, dance, ballet, jazz, classical, opera
- **Time filters** — this week, this weekend, free events
- **Calendar view** with monthly navigation
- **Search** across titles, venues, descriptions
- **Sorting** by date, name, price
- **Favorites** — save events locally with heart button
- **Tonight/Tomorrow Spotlight** — hero section for imminent events
- **Analytics Dashboard** — category donut chart + top venues bar chart
- **Email Weekly Digest** — mailto: with formatted upcoming events
- **Share Events** — Web Share API (mobile) or clipboard (desktop)
- **Google Calendar** — one-click "Add to GCal" from event modal
- **ICS Download** — download .ics calendar files
- **Map links** — Google Maps integration for venues
- **Sources panel** — view all 14 data sources

## Tech Stack

- Pure vanilla JS — no frameworks, no build step
- Python scraper with BeautifulSoup for event data
- GitHub Actions for automated scraping
- GitHub Pages for hosting

## Run Locally

```bash
# Scrape events
pip install -r scraper/requirements.txt
python scraper/scrape_events.py

# Serve
python -m http.server 8000
```
