/* ============================================================
   PhillyCulture — Main Application (v2 — 10 iterations)
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
  let sortBy = 'date'; // 'date', 'price-low', 'price-high', 'name'
  let calendarDate = new Date();
  let lastUpdated = '';
  let favorites = JSON.parse(localStorage.getItem('philly-culture-favorites') || '[]');
  let showFavoritesOnly = false;

  // DOM refs
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
    } catch (err) {
      console.error('Error loading events:', err);
      eventsList.innerHTML = `
        <div style="text-align:center;padding:3rem;color:var(--text-dim)">
          <p>Could not load events. Run the scraper first:</p>
          <code style="display:block;margin-top:1rem;color:var(--accent)">python scraper/scrape_events.py</code>
        </div>`;
    }
  }

  function updateStats(data) {
    const count = filteredEvents.length;
    const total = allEvents.length;
    eventCountEl.textContent = count === total
      ? `${total} events`
      : `${count} of ${total} events`;

    if (lastUpdated) {
      const d = new Date(lastUpdated);
      lastUpdatedEl.textContent = `Updated ${d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })}`;
    }
    const sources = data?.sources || [...new Set(allEvents.map(e => e.source))];
    sourceCountEl.textContent = `${sources.length} sources`;
    const footerCount = $('#footerSourceCount');
    if (footerCount) footerCount.textContent = sources.length;
  }

  // ---- Filtering ----
  function applyFilters() {
    const q = searchQuery.toLowerCase().trim();
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayStr = today.toISOString().slice(0, 10);

    // Compute weekend range
    const dayOfWeek = today.getDay();
    const friday = new Date(today);
    friday.setDate(today.getDate() + (5 - dayOfWeek + 7) % 7);
    const sunday = new Date(friday);
    sunday.setDate(friday.getDate() + 2);
    const fridayStr = friday.toISOString().slice(0, 10);
    const sundayStr = sunday.toISOString().slice(0, 10);

    // This week range (today through next Sunday)
    const nextSunday = new Date(today);
    nextSunday.setDate(today.getDate() + (7 - dayOfWeek));
    const nextSundayStr = nextSunday.toISOString().slice(0, 10);

    filteredEvents = allEvents.filter(ev => {
      // Category
      if (activeCategory !== 'all') {
        if (!ev.categories || !ev.categories.includes(activeCategory)) return false;
      }
      // Time filter
      if (activeTimeFilter === 'this-week') {
        const end = ev.date_end || ev.date_start || '';
        const start = ev.date_start || '';
        if (!start || start > nextSundayStr || end < todayStr) return false;
      } else if (activeTimeFilter === 'this-weekend') {
        const end = ev.date_end || ev.date_start || '';
        const start = ev.date_start || '';
        if (!start || start > sundayStr || end < fridayStr) return false;
      } else if (activeTimeFilter === 'free') {
        if (!ev.price || ev.price.toLowerCase() !== 'free') return false;
      }
      // Favorites
      if (showFavoritesOnly) {
        if (!favorites.includes(ev.id)) return false;
      }
      // Search
      if (q) {
        const haystack = [ev.title, ev.venue, ev.source, ev.description, ev.date_display, ...(ev.categories || [])]
          .filter(Boolean).join(' ').toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });

    // Sort
    if (sortBy === 'name') {
      filteredEvents.sort((a, b) => a.title.localeCompare(b.title));
    } else if (sortBy === 'price-low') {
      filteredEvents.sort((a, b) => extractMinPrice(a.price) - extractMinPrice(b.price));
    } else if (sortBy === 'price-high') {
      filteredEvents.sort((a, b) => extractMinPrice(b.price) - extractMinPrice(a.price));
    } else {
      filteredEvents.sort((a, b) => (a.date_start || '').localeCompare(b.date_start || ''));
    }

    render();
    updateStats({ sources: [...new Set(allEvents.map(e => e.source))] });
  }

  function extractMinPrice(priceStr) {
    if (!priceStr) return 999;
    if (priceStr.toLowerCase() === 'free') return 0;
    const m = priceStr.match(/\$(\d+)/);
    return m ? parseInt(m[1]) : 999;
  }

  // ---- Rendering ----
  function render() {
    if (currentView === 'list') {
      renderList();
    } else {
      renderCalendar();
    }
    emptyState.classList.toggle('hidden', filteredEvents.length > 0);
    listView.classList.toggle('hidden', currentView !== 'list' || filteredEvents.length === 0);
    calendarView.classList.toggle('hidden', currentView !== 'calendar');
  }

  function renderList() {
    const groups = {};
    const today = new Date().toISOString().slice(0, 10);

    filteredEvents.forEach(ev => {
      const dateStr = ev.date_start || '';
      let groupKey;
      if (sortBy === 'name') {
        groupKey = ev.title[0]?.toUpperCase() || '#';
      } else if (dateStr) {
        const d = new Date(dateStr + 'T00:00:00');
        groupKey = d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
      } else {
        groupKey = 'Date TBD';
      }
      if (!groups[groupKey]) groups[groupKey] = [];
      groups[groupKey].push(ev);
    });

    let html = '';
    for (const [group, events] of Object.entries(groups)) {
      html += `<div class="date-group-header">${escHtml(group)}</div>`;
      events.forEach(ev => { html += renderEventCard(ev, today); });
    }
    eventsList.innerHTML = html;

    eventsList.querySelectorAll('.event-card').forEach(card => {
      card.addEventListener('click', (e) => {
        if (e.target.closest('.fav-btn')) return;
        const ev = allEvents.find(e => e.id === card.dataset.id);
        if (ev) openModal(ev);
      });
    });

    // Favorite button handlers
    eventsList.querySelectorAll('.fav-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleFavorite(btn.dataset.id);
      });
    });
  }

  function renderEventCard(ev, today) {
    const primaryCat = ev.categories?.[0] || 'performance';
    const startDate = ev.date_start ? new Date(ev.date_start + 'T00:00:00') : null;
    const endDate = ev.date_end ? new Date(ev.date_end + 'T00:00:00') : null;
    const isFav = favorites.includes(ev.id);

    // "Happening now" indicator
    let happeningNow = false;
    if (ev.date_start && ev.date_end) {
      happeningNow = ev.date_start <= today && ev.date_end >= today;
    }

    let monthStr = '', dayStr = '', rangeStr = '';
    if (startDate) {
      monthStr = startDate.toLocaleDateString('en-US', { month: 'short' });
      dayStr = startDate.getDate();
      if (endDate && ev.date_start !== ev.date_end) {
        rangeStr = `– ${endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`;
      }
    }

    const priceClass = ev.price === 'Free' ? 'free' : '';
    const badges = (ev.categories || []).map(c =>
      `<span class="badge badge-${c}">${c}</span>`
    ).join('');

    return `
      <div class="event-card" data-id="${ev.id}" data-primary-cat="${primaryCat}" tabindex="0" role="button" aria-label="View details for ${escHtml(ev.title)}">
        <div class="event-date-block">
          <div class="event-date-month">${monthStr}</div>
          <div class="event-date-day">${dayStr}</div>
          ${rangeStr ? `<div class="event-date-range">${rangeStr}</div>` : ''}
          ${happeningNow ? '<div class="now-badge">NOW</div>' : ''}
        </div>
        <div class="event-info">
          <div class="event-title">${escHtml(ev.title)}</div>
          <div class="event-meta">
            <span class="event-meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
              ${escHtml(ev.venue || '')}
            </span>
            ${ev.time ? `
            <span class="event-meta-item">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              ${escHtml(ev.time)}
            </span>` : ''}
          </div>
          <div class="event-badges">${badges}</div>
        </div>
        <div class="event-actions-block">
          <button class="fav-btn${isFav ? ' active' : ''}" data-id="${ev.id}" title="${isFav ? 'Remove from saved' : 'Save event'}" aria-label="${isFav ? 'Remove from saved' : 'Save event'}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
          </button>
          ${ev.price ? `<div class="event-price ${priceClass}">${escHtml(ev.price)}</div>` : ''}
          <div class="event-source">${escHtml(ev.source)}</div>
        </div>
      </div>`;
  }

  // ---- Calendar ----
  function renderCalendar() {
    const year = calendarDate.getFullYear();
    const month = calendarDate.getMonth();
    $('#calendarTitle').textContent = calendarDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const todayStr = new Date().toISOString().slice(0, 10);

    const eventMap = {};
    filteredEvents.forEach(ev => {
      if (!ev.date_start) return;
      const start = new Date(ev.date_start + 'T00:00:00');
      const end = ev.date_end ? new Date(ev.date_end + 'T00:00:00') : start;
      for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
        if (d.getFullYear() === year && d.getMonth() === month) {
          const day = d.getDate();
          if (!eventMap[day]) eventMap[day] = [];
          if (!eventMap[day].find(e => e.id === ev.id)) eventMap[day].push(ev);
        }
      }
    });

    const container = $('#calendarDays');
    let html = '';
    for (let i = 0; i < firstDay; i++) html += '<div class="calendar-day empty"></div>';

    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      const isToday = dateStr === todayStr;
      const dayEvents = eventMap[day] || [];
      const maxShow = 3;

      html += `<div class="calendar-day${isToday ? ' today' : ''}${dayEvents.length ? ' has-events' : ''}">`;
      html += `<div class="calendar-day-num">${day}</div>`;
      dayEvents.slice(0, maxShow).forEach(ev => {
        const cat = ev.categories?.[0] || 'performance';
        html += `<div class="calendar-event cat-${cat}" data-id="${ev.id}" title="${escHtml(ev.title)}">${escHtml(ev.title)}</div>`;
      });
      if (dayEvents.length > maxShow) {
        html += `<div class="calendar-more">+${dayEvents.length - maxShow} more</div>`;
      }
      html += '</div>';
    }
    container.innerHTML = html;

    container.querySelectorAll('.calendar-event').forEach(el => {
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        const ev = allEvents.find(e => e.id === el.dataset.id);
        if (ev) openModal(ev);
      });
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

    $('#modalBadges').innerHTML = (ev.categories || []).map(c =>
      `<span class="badge badge-${c}">${c}</span>`
    ).join('');

    $('#modalPriceRow').style.display = ev.price ? 'flex' : 'none';

    // Venue map link
    const mapLink = $('#modalMapLink');
    if (ev.venue) {
      mapLink.href = `https://www.google.com/maps/search/${encodeURIComponent(ev.venue + ' Philadelphia PA')}`;
      mapLink.classList.remove('hidden');
    } else {
      mapLink.classList.add('hidden');
    }

    // Save to calendar link
    const calLink = $('#modalCalLink');
    calLink.onclick = () => downloadICS(ev);

    // Favorite button in modal
    const modalFav = $('#modalFavBtn');
    modalFav.className = `btn btn-ghost${isFav ? ' fav-active' : ''}`;
    modalFav.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
      <span>${isFav ? 'Saved' : 'Save'}</span>`;
    modalFav.onclick = () => {
      toggleFavorite(ev.id);
      openModal(ev); // Re-render modal
    };

    eventModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    eventModal.classList.add('hidden');
    document.body.style.overflow = '';
  }

  // ---- Favorites ----
  function toggleFavorite(id) {
    const idx = favorites.indexOf(id);
    if (idx >= 0) {
      favorites.splice(idx, 1);
    } else {
      favorites.push(id);
    }
    localStorage.setItem('philly-culture-favorites', JSON.stringify(favorites));
    applyFilters();
  }

  // ---- ICS Download ----
  function downloadICS(ev) {
    const start = ev.date_start || '';
    const end = ev.date_end || start;
    if (!start) return;

    const dtStart = start.replace(/-/g, '');
    const dtEnd = end.replace(/-/g, '');

    const ics = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//PhillyCulture//EN',
      'BEGIN:VEVENT',
      `DTSTART;VALUE=DATE:${dtStart}`,
      `DTEND;VALUE=DATE:${dtEnd}`,
      `SUMMARY:${ev.title}`,
      `LOCATION:${ev.venue || ''}`,
      `DESCRIPTION:${(ev.description || '').replace(/\n/g, '\\n')}\\n\\nTickets: ${ev.link || ''}`,
      `URL:${ev.link || ''}`,
      'END:VEVENT',
      'END:VCALENDAR'
    ].join('\r\n');

    const blob = new Blob([ics], { type: 'text/calendar' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${ev.title.replace(/[^a-zA-Z0-9]/g, '_')}.ics`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  // ---- Sources panel ----
  async function loadSources() {
    try {
      const resp = await fetch('data/sources.json?' + Date.now());
      if (!resp.ok) return;
      const data = await resp.json();
      renderSources(data.sources || []);
    } catch (e) { /* ignore */ }
  }

  function renderSources(sources) {
    const panel = $('#sourcesPanel');
    if (!panel) return;
    panel.innerHTML = sources.map(s => `
      <a href="${escHtml(s.url)}" target="_blank" rel="noopener" class="source-card">
        <div class="source-name">${escHtml(s.name)}</div>
        <div class="source-covers">${escHtml(s.covers)}</div>
        <div class="source-venues">${(s.venues || []).map(v => escHtml(v)).join(' · ')}</div>
      </a>
    `).join('');
  }

  // ---- Event handlers ----
  categoryFilters.addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    categoryFilters.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    activeCategory = chip.dataset.category;
    applyFilters();
  });

  // Time filter chips
  const timeFilters = $('#timeFilters');
  if (timeFilters) {
    timeFilters.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (!chip) return;
      timeFilters.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      activeTimeFilter = chip.dataset.time;
      applyFilters();
    });
  }

  // Sort control
  const sortSelect = $('#sortSelect');
  if (sortSelect) {
    sortSelect.addEventListener('change', () => {
      sortBy = sortSelect.value;
      applyFilters();
    });
  }

  // Favorites toggle
  const favToggle = $('#favToggle');
  if (favToggle) {
    favToggle.addEventListener('click', () => {
      showFavoritesOnly = !showFavoritesOnly;
      favToggle.classList.toggle('active', showFavoritesOnly);
      applyFilters();
    });
  }

  // Sources panel toggle
  const sourcesToggle = $('#sourcesToggle');
  const sourcesOverlay = $('#sourcesOverlay');
  if (sourcesToggle && sourcesOverlay) {
    sourcesToggle.addEventListener('click', () => {
      sourcesOverlay.classList.toggle('hidden');
      document.body.style.overflow = sourcesOverlay.classList.contains('hidden') ? '' : 'hidden';
    });
    sourcesOverlay.addEventListener('click', (e) => {
      if (e.target === sourcesOverlay) {
        sourcesOverlay.classList.add('hidden');
        document.body.style.overflow = '';
      }
    });
    const sourcesClose = $('#sourcesClose');
    if (sourcesClose) sourcesClose.addEventListener('click', () => {
      sourcesOverlay.classList.add('hidden');
      document.body.style.overflow = '';
    });
  }

  searchInput.addEventListener('input', debounce(() => {
    searchQuery = searchInput.value;
    applyFilters();
  }, 200));

  viewToggle.addEventListener('click', () => {
    currentView = currentView === 'list' ? 'calendar' : 'list';
    viewToggle.querySelector('.icon-calendar').classList.toggle('hidden', currentView === 'calendar');
    viewToggle.querySelector('.icon-list').classList.toggle('hidden', currentView === 'list');
    render();
  });

  refreshBtn.addEventListener('click', async () => {
    refreshBtn.classList.add('loading');
    refreshBtn.disabled = true;
    await loadEvents();
    setTimeout(() => {
      refreshBtn.classList.remove('loading');
      refreshBtn.disabled = false;
    }, 500);
  });

  modalClose.addEventListener('click', closeModal);
  eventModal.addEventListener('click', (e) => {
    if (e.target === eventModal) closeModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeModal();
      if (sourcesOverlay && !sourcesOverlay.classList.contains('hidden')) {
        sourcesOverlay.classList.add('hidden');
        document.body.style.overflow = '';
      }
    }
  });

  // Keyboard navigation for event cards
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.target.classList.contains('event-card')) {
      const ev = allEvents.find(x => x.id === e.target.dataset.id);
      if (ev) openModal(ev);
    }
  });

  $('#prevMonth').addEventListener('click', () => {
    calendarDate.setMonth(calendarDate.getMonth() - 1);
    renderCalendar();
  });
  $('#nextMonth').addEventListener('click', () => {
    calendarDate.setMonth(calendarDate.getMonth() + 1);
    renderCalendar();
  });

  // ---- Utilities ----
  function escHtml(str) {
    const el = document.createElement('span');
    el.textContent = str || '';
    return el.innerHTML;
  }

  function debounce(fn, ms) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), ms);
    };
  }

  // ---- Init ----
  loadEvents();
  loadSources();
})();
