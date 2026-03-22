/* ============================================================
   PhillyCulture — Main Application (v3 — 15 iterations)
   ============================================================ */

(function () {
  'use strict';

  // State
  let allEvents = [];
  let filteredEvents = [];
  let activeCategory = 'all';
  let activeTimeFilter = 'all';
  let searchQuery = '';
  let currentView = 'list';
  let sortBy = 'date';
  let calendarDate = new Date();
  let lastUpdated = '';
  let favorites = JSON.parse(localStorage.getItem('philly-culture-favorites') || '[]');
  let showFavoritesOnly = false;

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const listView = $('#listView');
  const calendarView = $('#calendarView');
  const eventsList = $('#eventsList');
  const emptyState = $('#emptyState');
  const searchInput = $('#searchInput');
  const categoryFilters = $('#categoryFilters');
  const viewToggle = $('#viewToggle');
  const refreshBtn = $('#refreshBtn');
  const eventModal = $('#eventModal');
  const modalClose = $('#modalClose');
  const eventCountEl = $('#eventCount');
  const lastUpdatedEl = $('#lastUpdated');
  const sourceCountEl = $('#sourceCount');

  const CAT_COLORS = {
    musical: '#ff6b9d', theater: '#ffa44f', dance: '#4fd1c5', ballet: '#f687b3',
    jazz: '#63b3ed', classical: '#d6a0ff', opera: '#fc8181', concert: '#68d391', performance: '#a0aec0'
  };

  // ---- Data loading ----
  async function loadEvents() {
    try {
      const resp = await fetch('data/events.json?' + Date.now());
      if (!resp.ok) throw new Error('Failed to load events');
      const data = await resp.json();
      allEvents = data.events || [];
      lastUpdated = data.last_updated || '';
      allEvents.sort((a, b) => (a.date_start || '').localeCompare(b.date_start || ''));
      applyFilters();
      updateStats(data);
      renderSpotlight();
      renderAnalytics();
    } catch (err) {
      console.error('Error loading events:', err);
      eventsList.innerHTML = '<div style="text-align:center;padding:3rem;color:var(--text-dim)"><p>Could not load events. Run the scraper first:</p><code style="display:block;margin-top:1rem;color:var(--accent)">python scraper/scrape_events.py</code></div>';
    }
  }

  function updateStats(data) {
    const count = filteredEvents.length;
    const total = allEvents.length;
    eventCountEl.textContent = count === total ? `${total} events` : `${count} of ${total} events`;
    if (lastUpdated) {
      const d = new Date(lastUpdated);
      lastUpdatedEl.textContent = `Updated ${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })}`;
    }
    const sources = data?.sources || [...new Set(allEvents.map(e => e.source))];
    sourceCountEl.textContent = `${sources.length} sources`;
    const fc = $('#footerSourceCount');
    if (fc) fc.textContent = sources.length;
  }

  // ---- Filtering ----
  function applyFilters() {
    const q = searchQuery.toLowerCase().trim();
    const today = new Date(); today.setHours(0,0,0,0);
    const todayStr = today.toISOString().slice(0, 10);
    const dow = today.getDay();
    const fri = new Date(today); fri.setDate(today.getDate() + (5 - dow + 7) % 7);
    const sun = new Date(fri); sun.setDate(fri.getDate() + 2);
    const friStr = fri.toISOString().slice(0, 10);
    const sunStr = sun.toISOString().slice(0, 10);
    const nxtSun = new Date(today); nxtSun.setDate(today.getDate() + (7 - dow));
    const nxtSunStr = nxtSun.toISOString().slice(0, 10);

    filteredEvents = allEvents.filter(ev => {
      if (activeCategory !== 'all' && (!ev.categories || !ev.categories.includes(activeCategory))) return false;
      if (activeTimeFilter === 'this-week') {
        const e = ev.date_end || ev.date_start || '', s = ev.date_start || '';
        if (!s || s > nxtSunStr || e < todayStr) return false;
      } else if (activeTimeFilter === 'this-weekend') {
        const e = ev.date_end || ev.date_start || '', s = ev.date_start || '';
        if (!s || s > sunStr || e < friStr) return false;
      } else if (activeTimeFilter === 'free') {
        if (!ev.price || ev.price.toLowerCase() !== 'free') return false;
      }
      if (showFavoritesOnly && !favorites.includes(ev.id)) return false;
      if (q) {
        const h = [ev.title, ev.venue, ev.source, ev.description, ev.date_display, ...(ev.categories || [])].filter(Boolean).join(' ').toLowerCase();
        if (!h.includes(q)) return false;
      }
      return true;
    });

    if (sortBy === 'name') filteredEvents.sort((a, b) => a.title.localeCompare(b.title));
    else if (sortBy === 'price-low') filteredEvents.sort((a, b) => extractMinPrice(a.price) - extractMinPrice(b.price));
    else if (sortBy === 'price-high') filteredEvents.sort((a, b) => extractMinPrice(b.price) - extractMinPrice(a.price));
    else filteredEvents.sort((a, b) => (a.date_start || '').localeCompare(b.date_start || ''));

    render();
    updateStats({ sources: [...new Set(allEvents.map(e => e.source))] });
  }

  function extractMinPrice(p) {
    if (!p) return 999;
    if (p.toLowerCase() === 'free') return 0;
    const m = p.match(/\$(\d+)/);
    return m ? parseInt(m[1]) : 999;
  }

  // ---- Rendering ----
  function render() {
    if (currentView === 'list') renderList();
    else renderCalendar();
    emptyState.classList.toggle('hidden', filteredEvents.length > 0);
    listView.classList.toggle('hidden', currentView !== 'list' || filteredEvents.length === 0);
    calendarView.classList.toggle('hidden', currentView !== 'calendar');
  }

  function renderList() {
    const groups = {};
    const today = new Date().toISOString().slice(0, 10);
    filteredEvents.forEach(ev => {
      const ds = ev.date_start || '';
      let gk;
      if (sortBy === 'name') gk = ev.title[0]?.toUpperCase() || '#';
      else if (ds) gk = new Date(ds + 'T00:00:00').toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
      else gk = 'Date TBD';
      if (!groups[gk]) groups[gk] = [];
      groups[gk].push(ev);
    });

    let html = '';
    for (const [g, evts] of Object.entries(groups)) {
      html += `<div class="date-group-header">${escHtml(g)}</div>`;
      evts.forEach(ev => { html += renderEventCard(ev, today); });
    }
    eventsList.innerHTML = html;

    eventsList.querySelectorAll('.event-card').forEach(card => {
      card.addEventListener('click', e => {
        if (e.target.closest('.fav-btn') || e.target.closest('.share-btn')) return;
        const ev = allEvents.find(x => x.id === card.dataset.id);
        if (ev) openModal(ev);
      });
    });
    eventsList.querySelectorAll('.fav-btn').forEach(btn => {
      btn.addEventListener('click', e => { e.stopPropagation(); toggleFavorite(btn.dataset.id); });
    });
    eventsList.querySelectorAll('.share-btn').forEach(btn => {
      btn.addEventListener('click', e => { e.stopPropagation(); shareEvent(allEvents.find(x => x.id === btn.dataset.id)); });
    });
  }

  function renderEventCard(ev, today) {
    const pc = ev.categories?.[0] || 'performance';
    const sd = ev.date_start ? new Date(ev.date_start + 'T00:00:00') : null;
    const ed = ev.date_end ? new Date(ev.date_end + 'T00:00:00') : null;
    const isFav = favorites.includes(ev.id);
    const hapNow = ev.date_start && ev.date_end && ev.date_start <= today && ev.date_end >= today;

    let mo = '', dy = '', rng = '';
    if (sd) {
      mo = sd.toLocaleDateString('en-US', { month: 'short' });
      dy = sd.getDate();
      if (ed && ev.date_start !== ev.date_end) rng = `– ${ed.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
    }

    const badges = (ev.categories || []).map(c => `<span class="badge badge-${c}">${c}</span>`).join('');

    return `
      <div class="event-card" data-id="${ev.id}" data-primary-cat="${pc}" tabindex="0" role="button" aria-label="${escHtml(ev.title)}">
        <div class="event-date-block">
          <div class="event-date-month">${mo}</div>
          <div class="event-date-day">${dy}</div>
          ${rng ? `<div class="event-date-range">${rng}</div>` : ''}
          ${hapNow ? '<div class="now-badge">NOW</div>' : ''}
        </div>
        <div class="event-info">
          <div class="event-title">${escHtml(ev.title)}</div>
          <div class="event-meta">
            <span class="event-meta-item"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>${escHtml(ev.venue || '')}</span>
            ${ev.time ? `<span class="event-meta-item"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>${escHtml(ev.time)}</span>` : ''}
          </div>
          <div class="event-badges">${badges}</div>
        </div>
        <div class="event-actions-block">
          <div class="card-action-row">
            <button class="fav-btn${isFav ? ' active' : ''}" data-id="${ev.id}" title="${isFav ? 'Unsave' : 'Save'}"><svg width="16" height="16" viewBox="0 0 24 24" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg></button>
            <button class="share-btn" data-id="${ev.id}" title="Share"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg></button>
          </div>
          ${ev.price ? `<div class="event-price${ev.price.toLowerCase() === 'free' ? ' free' : ''}">${escHtml(ev.price)}</div>` : ''}
          <div class="event-source">${escHtml(ev.source)}</div>
        </div>
      </div>`;
  }

  // ---- ITERATION 11: Spotlight — Tonight / Tomorrow ----
  function renderSpotlight() {
    const container = $('#spotlightSection');
    if (!container) return;
    const today = new Date(); today.setHours(0,0,0,0);
    const todayStr = today.toISOString().slice(0, 10);
    const tmrw = new Date(today); tmrw.setDate(tmrw.getDate() + 1);
    const tmrwStr = tmrw.toISOString().slice(0, 10);

    const tonightEvts = allEvents.filter(ev => ev.date_start && ev.date_start <= todayStr && (ev.date_end || ev.date_start) >= todayStr);
    const tmrwEvts = allEvents.filter(ev => ev.date_start && ev.date_start <= tmrwStr && (ev.date_end || ev.date_start) >= tmrwStr && !(ev.date_start <= todayStr && (ev.date_end || ev.date_start) >= todayStr));

    if (tonightEvts.length === 0 && tmrwEvts.length === 0) { container.classList.add('hidden'); return; }
    container.classList.remove('hidden');

    let html = '';
    if (tonightEvts.length > 0) {
      html += `<div class="spotlight-group"><h3 class="spotlight-label"><span class="spotlight-dot tonight"></span>Tonight</h3><div class="spotlight-cards">`;
      tonightEvts.slice(0, 4).forEach(ev => {
        const cat = ev.categories?.[0] || 'performance';
        html += `<div class="spotlight-card" data-id="${ev.id}" tabindex="0">
          <div class="spotlight-cat badge badge-${cat}">${cat}</div>
          <div class="spotlight-title">${escHtml(ev.title)}</div>
          <div class="spotlight-venue">${escHtml(ev.venue || '')}${ev.time ? ' · ' + escHtml(ev.time) : ''}</div>
          ${ev.price ? `<div class="spotlight-price">${escHtml(ev.price)}</div>` : ''}
        </div>`;
      });
      html += `</div></div>`;
    }
    if (tmrwEvts.length > 0) {
      html += `<div class="spotlight-group"><h3 class="spotlight-label"><span class="spotlight-dot tomorrow"></span>Tomorrow</h3><div class="spotlight-cards">`;
      tmrwEvts.slice(0, 4).forEach(ev => {
        const cat = ev.categories?.[0] || 'performance';
        html += `<div class="spotlight-card" data-id="${ev.id}" tabindex="0">
          <div class="spotlight-cat badge badge-${cat}">${cat}</div>
          <div class="spotlight-title">${escHtml(ev.title)}</div>
          <div class="spotlight-venue">${escHtml(ev.venue || '')}${ev.time ? ' · ' + escHtml(ev.time) : ''}</div>
          ${ev.price ? `<div class="spotlight-price">${escHtml(ev.price)}</div>` : ''}
        </div>`;
      });
      html += `</div></div>`;
    }
    container.innerHTML = html;
    container.querySelectorAll('.spotlight-card').forEach(card => {
      card.addEventListener('click', () => { const ev = allEvents.find(e => e.id === card.dataset.id); if (ev) openModal(ev); });
    });
  }

  // ---- ITERATION 12: Analytics Dashboard ----
  function renderAnalytics() {
    const container = $('#analyticsSection');
    if (!container) return;

    // Category donut
    const catCounts = {};
    allEvents.forEach(ev => { (ev.categories || ['performance']).forEach(c => { catCounts[c] = (catCounts[c] || 0) + 1; }); });
    const total = Object.values(catCounts).reduce((a, b) => a + b, 0) || 1;
    const sorted = Object.entries(catCounts).sort((a, b) => b[1] - a[1]);

    // SVG donut chart
    let donutSvg = '<svg viewBox="0 0 120 120" class="donut-chart">';
    let cumAngle = 0;
    sorted.forEach(([cat, count]) => {
      const pct = count / total;
      const angle = pct * 360;
      const startRad = (cumAngle - 90) * Math.PI / 180;
      const endRad = (cumAngle + angle - 90) * Math.PI / 180;
      const largeArc = angle > 180 ? 1 : 0;
      const r = 45, cx = 60, cy = 60;
      const x1 = cx + r * Math.cos(startRad), y1 = cy + r * Math.sin(startRad);
      const x2 = cx + r * Math.cos(endRad), y2 = cy + r * Math.sin(endRad);
      const color = CAT_COLORS[cat] || '#a0aec0';
      donutSvg += `<path d="M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${largeArc},1 ${x2},${y2} Z" fill="${color}" opacity="0.85"><title>${cat}: ${count}</title></path>`;
      cumAngle += angle;
    });
    donutSvg += `<circle cx="60" cy="60" r="28" fill="var(--bg-card)"/><text x="60" y="56" text-anchor="middle" fill="var(--text)" font-size="16" font-weight="700">${allEvents.length}</text><text x="60" y="70" text-anchor="middle" fill="var(--text-dim)" font-size="8">events</text></svg>`;

    const legend = sorted.map(([cat, count]) => {
      const color = CAT_COLORS[cat] || '#a0aec0';
      return `<div class="legend-item"><span class="legend-dot" style="background:${color}"></span><span class="legend-label">${cat}</span><span class="legend-count">${count}</span></div>`;
    }).join('');

    // Venue heatmap — top 8 venues by event count
    const venueCounts = {};
    allEvents.forEach(ev => { if (ev.venue) venueCounts[ev.venue] = (venueCounts[ev.venue] || 0) + 1; });
    const topVenues = Object.entries(venueCounts).sort((a, b) => b[1] - a[1]).slice(0, 8);
    const maxVenue = topVenues[0]?.[1] || 1;
    const venueHtml = topVenues.map(([v, c]) => {
      const pct = Math.round(c / maxVenue * 100);
      return `<div class="venue-bar-row"><span class="venue-bar-label">${escHtml(v)}</span><div class="venue-bar-track"><div class="venue-bar-fill" style="width:${pct}%"></div></div><span class="venue-bar-count">${c}</span></div>`;
    }).join('');

    container.innerHTML = `
      <div class="analytics-card">
        <h3 class="analytics-title">By Category</h3>
        <div class="donut-container">${donutSvg}<div class="legend">${legend}</div></div>
      </div>
      <div class="analytics-card">
        <h3 class="analytics-title">Top Venues</h3>
        <div class="venue-bars">${venueHtml}</div>
      </div>`;
  }

  // ---- Calendar ----
  function renderCalendar() {
    const year = calendarDate.getFullYear(), month = calendarDate.getMonth();
    $('#calendarTitle').textContent = calendarDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    const firstDay = new Date(year, month, 1).getDay();
    const dim = new Date(year, month + 1, 0).getDate();
    const todayStr = new Date().toISOString().slice(0, 10);

    const evMap = {};
    filteredEvents.forEach(ev => {
      if (!ev.date_start) return;
      const s = new Date(ev.date_start + 'T00:00:00'), e = ev.date_end ? new Date(ev.date_end + 'T00:00:00') : s;
      for (let d = new Date(s); d <= e; d.setDate(d.getDate() + 1)) {
        if (d.getFullYear() === year && d.getMonth() === month) {
          const dy = d.getDate();
          if (!evMap[dy]) evMap[dy] = [];
          if (!evMap[dy].find(x => x.id === ev.id)) evMap[dy].push(ev);
        }
      }
    });

    const c = $('#calendarDays');
    let h = '';
    for (let i = 0; i < firstDay; i++) h += '<div class="calendar-day empty"></div>';
    for (let day = 1; day <= dim; day++) {
      const ds = `${year}-${String(month+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
      const isT = ds === todayStr, de = evMap[day] || [], mx = 3;
      h += `<div class="calendar-day${isT?' today':''}${de.length?' has-events':''}"><div class="calendar-day-num">${day}</div>`;
      de.slice(0, mx).forEach(ev => { h += `<div class="calendar-event cat-${ev.categories?.[0]||'performance'}" data-id="${ev.id}" title="${escHtml(ev.title)}">${escHtml(ev.title)}</div>`; });
      if (de.length > mx) h += `<div class="calendar-more">+${de.length-mx} more</div>`;
      h += '</div>';
    }
    c.innerHTML = h;
    c.querySelectorAll('.calendar-event').forEach(el => {
      el.addEventListener('click', e => { e.stopPropagation(); const ev = allEvents.find(x => x.id === el.dataset.id); if (ev) openModal(ev); });
    });
  }

  // ---- Modal ----
  function openModal(ev) {
    const isFav = favorites.includes(ev.id);
    $('#modalTitle').textContent = ev.title;
    $('#modalDate').textContent = ev.date_display || 'Date TBD';
    $('#modalTime').textContent = ev.time || 'See website for times';
    $('#modalVenue').textContent = ev.venue || 'Venue TBD';
    $('#modalPrice').textContent = ev.price || 'See website for pricing';
    $('#modalDescription').textContent = ev.description || 'Visit the source website for more details.';
    $('#modalSource').textContent = ev.source;
    $('#modalSource').href = ev.source_url || '#';
    $('#modalTicketLink').href = ev.link || '#';
    $('#modalBadges').innerHTML = (ev.categories || []).map(c => `<span class="badge badge-${c}">${c}</span>`).join('');
    $('#modalPriceRow').style.display = ev.price ? 'flex' : 'none';

    // Map link
    const ml = $('#modalMapLink');
    if (ev.venue) { ml.href = `https://www.google.com/maps/search/${encodeURIComponent(ev.venue + ' Philadelphia PA')}`; ml.classList.remove('hidden'); }
    else ml.classList.add('hidden');

    // ICS
    $('#modalCalLink').onclick = () => downloadICS(ev);

    // ITERATION 11: Google Calendar
    const gcal = $('#modalGcalLink');
    if (gcal) {
      const s = (ev.date_start || '').replace(/-/g, ''), e = (ev.date_end || ev.date_start || '').replace(/-/g, '');
      gcal.href = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(ev.title)}&dates=${s}/${e}&location=${encodeURIComponent(ev.venue || '')}&details=${encodeURIComponent((ev.description || '') + '\n\nTickets: ' + (ev.link || ''))}`;
    }

    // ITERATION 14: Share
    const shareBtn = $('#modalShareBtn');
    if (shareBtn) shareBtn.onclick = () => shareEvent(ev);

    // Fav
    const mf = $('#modalFavBtn');
    mf.className = `btn btn-ghost${isFav ? ' fav-active' : ''}`;
    mf.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="${isFav?'currentColor':'none'}" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg><span>${isFav?'Saved':'Save'}</span>`;
    mf.onclick = () => { toggleFavorite(ev.id); openModal(ev); };

    eventModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() { eventModal.classList.add('hidden'); document.body.style.overflow = ''; }

  // ---- Favorites ----
  function toggleFavorite(id) {
    const i = favorites.indexOf(id);
    if (i >= 0) favorites.splice(i, 1); else favorites.push(id);
    localStorage.setItem('philly-culture-favorites', JSON.stringify(favorites));
    applyFilters();
  }

  // ---- ITERATION 14: Share ----
  function shareEvent(ev) {
    if (!ev) return;
    const text = `${ev.title} — ${ev.date_display || ''}\n${ev.venue || ''}\n${ev.price || ''}\n${ev.link || ''}`;
    if (navigator.share) {
      navigator.share({ title: ev.title, text: text, url: ev.link || window.location.href }).catch(() => {});
    } else {
      navigator.clipboard.writeText(text).then(() => {
        showToast('Copied to clipboard!');
      }).catch(() => {});
    }
  }

  function showToast(msg) {
    let t = $('#toast');
    if (!t) { t = document.createElement('div'); t.id = 'toast'; document.body.appendChild(t); }
    t.textContent = msg;
    t.className = 'toast show';
    setTimeout(() => { t.className = 'toast'; }, 2500);
  }

  // ---- ITERATION 13: Email Digest ----
  function generateEmailDigest() {
    const today = new Date(); today.setHours(0,0,0,0);
    const todayStr = today.toISOString().slice(0,10);
    const nextWeek = new Date(today); nextWeek.setDate(nextWeek.getDate() + 7);
    const nwStr = nextWeek.toISOString().slice(0,10);

    const upcoming = allEvents.filter(ev => {
      const s = ev.date_start || '', e = ev.date_end || s;
      return s && s <= nwStr && e >= todayStr;
    });

    let subject = `PhillyCulture: ${upcoming.length} events this week (${today.toLocaleDateString('en-US', {month:'short',day:'numeric'})})`;
    let body = 'PHILLY CULTURE — THIS WEEK\'S EVENTS\n' + '='.repeat(40) + '\n\n';

    const byCat = {};
    upcoming.forEach(ev => {
      const c = ev.categories?.[0] || 'performance';
      if (!byCat[c]) byCat[c] = [];
      byCat[c].push(ev);
    });

    for (const [cat, evts] of Object.entries(byCat)) {
      body += `\n${cat.toUpperCase()}\n${'-'.repeat(20)}\n`;
      evts.forEach(ev => {
        body += `\n* ${ev.title}\n  ${ev.date_display || ''} | ${ev.venue || ''}\n  ${ev.time ? 'Time: ' + ev.time + ' | ' : ''}${ev.price ? 'Price: ' + ev.price : ''}\n  ${ev.description ? ev.description.slice(0, 120) + '...' : ''}\n  Tickets: ${ev.link || 'See source'}\n`;
      });
    }
    body += '\n\n---\nGenerated by PhillyCulture | ' + window.location.href;

    window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  }

  // ---- ICS Download ----
  function downloadICS(ev) {
    const s = ev.date_start || '', e = ev.date_end || s;
    if (!s) return;
    const ics = ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//PhillyCulture//EN','BEGIN:VEVENT',
      `DTSTART;VALUE=DATE:${s.replace(/-/g,'')}`,`DTEND;VALUE=DATE:${e.replace(/-/g,'')}`,
      `SUMMARY:${ev.title}`,`LOCATION:${ev.venue||''}`,
      `DESCRIPTION:${(ev.description||'').replace(/\n/g,'\\n')}\\n\\nTickets: ${ev.link||''}`,
      `URL:${ev.link||''}`,'END:VEVENT','END:VCALENDAR'].join('\r\n');
    const b = new Blob([ics], {type:'text/calendar'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(b); a.download = `${ev.title.replace(/[^a-zA-Z0-9]/g,'_')}.ics`; a.click(); URL.revokeObjectURL(a.href);
  }

  // ---- Sources panel ----
  async function loadSources() {
    try {
      const r = await fetch('data/sources.json?' + Date.now());
      if (!r.ok) return;
      const d = await r.json();
      renderSources(d.sources || []);
    } catch(e) {}
  }

  function renderSources(sources) {
    const p = $('#sourcesPanel');
    if (!p) return;
    p.innerHTML = sources.map(s => `
      <a href="${escHtml(s.url)}" target="_blank" rel="noopener" class="source-card">
        <div class="source-name">${escHtml(s.name)}</div>
        <div class="source-covers">${escHtml(s.covers)}</div>
        <div class="source-venues">${(s.venues||[]).map(v=>escHtml(v)).join(' · ')}</div>
      </a>`).join('');
  }

  // ---- Event handlers ----
  categoryFilters.addEventListener('click', e => {
    const c = e.target.closest('.chip'); if (!c) return;
    categoryFilters.querySelectorAll('.chip').forEach(x => x.classList.remove('active'));
    c.classList.add('active'); activeCategory = c.dataset.category; applyFilters();
  });

  const timeFilters = $('#timeFilters');
  if (timeFilters) timeFilters.addEventListener('click', e => {
    const c = e.target.closest('.chip'); if (!c) return;
    timeFilters.querySelectorAll('.chip').forEach(x => x.classList.remove('active'));
    c.classList.add('active'); activeTimeFilter = c.dataset.time; applyFilters();
  });

  const sortSelect = $('#sortSelect');
  if (sortSelect) sortSelect.addEventListener('change', () => { sortBy = sortSelect.value; applyFilters(); });

  const favToggle = $('#favToggle');
  if (favToggle) favToggle.addEventListener('click', () => {
    showFavoritesOnly = !showFavoritesOnly; favToggle.classList.toggle('active', showFavoritesOnly); applyFilters();
  });

  // Email digest button
  const emailBtn = $('#emailDigestBtn');
  if (emailBtn) emailBtn.addEventListener('click', generateEmailDigest);

  // Sources panel
  const sourcesToggle = $('#sourcesToggle'), sourcesOverlay = $('#sourcesOverlay');
  if (sourcesToggle && sourcesOverlay) {
    sourcesToggle.addEventListener('click', () => { sourcesOverlay.classList.toggle('hidden'); document.body.style.overflow = sourcesOverlay.classList.contains('hidden') ? '' : 'hidden'; });
    sourcesOverlay.addEventListener('click', e => { if (e.target === sourcesOverlay) { sourcesOverlay.classList.add('hidden'); document.body.style.overflow = ''; } });
    const sc = $('#sourcesClose'); if (sc) sc.addEventListener('click', () => { sourcesOverlay.classList.add('hidden'); document.body.style.overflow = ''; });
  }

  // Analytics panel
  const analyticsToggle = $('#analyticsToggle'), analyticsOverlay = $('#analyticsOverlay');
  if (analyticsToggle && analyticsOverlay) {
    analyticsToggle.addEventListener('click', () => { analyticsOverlay.classList.toggle('hidden'); document.body.style.overflow = analyticsOverlay.classList.contains('hidden') ? '' : 'hidden'; renderAnalytics(); });
    analyticsOverlay.addEventListener('click', e => { if (e.target === analyticsOverlay) { analyticsOverlay.classList.add('hidden'); document.body.style.overflow = ''; } });
    const ac = $('#analyticsClose'); if (ac) ac.addEventListener('click', () => { analyticsOverlay.classList.add('hidden'); document.body.style.overflow = ''; });
  }

  searchInput.addEventListener('input', debounce(() => { searchQuery = searchInput.value; applyFilters(); }, 200));

  viewToggle.addEventListener('click', () => {
    currentView = currentView === 'list' ? 'calendar' : 'list';
    viewToggle.querySelector('.icon-calendar').classList.toggle('hidden', currentView === 'calendar');
    viewToggle.querySelector('.icon-list').classList.toggle('hidden', currentView === 'list');
    render();
  });

  refreshBtn.addEventListener('click', async () => {
    refreshBtn.classList.add('loading'); refreshBtn.disabled = true;
    await loadEvents();
    setTimeout(() => { refreshBtn.classList.remove('loading'); refreshBtn.disabled = false; }, 500);
  });

  modalClose.addEventListener('click', closeModal);
  eventModal.addEventListener('click', e => { if (e.target === eventModal) closeModal(); });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeModal();
      [sourcesOverlay, analyticsOverlay].forEach(o => { if (o && !o.classList.contains('hidden')) { o.classList.add('hidden'); document.body.style.overflow = ''; } });
    }
    if (e.key === 'Enter' && e.target.classList.contains('event-card')) {
      const ev = allEvents.find(x => x.id === e.target.dataset.id); if (ev) openModal(ev);
    }
  });

  $('#prevMonth').addEventListener('click', () => { calendarDate.setMonth(calendarDate.getMonth() - 1); renderCalendar(); });
  $('#nextMonth').addEventListener('click', () => { calendarDate.setMonth(calendarDate.getMonth() + 1); renderCalendar(); });

  function escHtml(s) { const el = document.createElement('span'); el.textContent = s || ''; return el.innerHTML; }
  function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

  // Init
  loadEvents();
  loadSources();
})();
