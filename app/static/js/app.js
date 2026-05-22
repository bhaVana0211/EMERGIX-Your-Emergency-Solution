/* ═══════════════════════════════════════════════════════════════
   EMERGIX — app.js
   Geolocation · Hospital discovery · Filters · Real-time updates
   ═══════════════════════════════════════════════════════════════ */
'use strict';

const EMERGIX = window.EMERGIX || {};
EMERGIX.userLat    = null;
EMERGIX.userLng    = null;
EMERGIX.hospitals  = [];
EMERGIX.activeFilters = {
  bedTypes: [], hospitalType: 'all', availableOnly: true, radius: 10
};

/* ── Navbar hamburger ────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const ham = document.getElementById('hamburger');
  const nav = document.getElementById('nav-links');
  if (ham && nav) ham.addEventListener('click', () => nav.classList.toggle('open'));

  // Flash messages auto-dismiss after 5s
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => el.style.opacity = '0', 4500);
    setTimeout(() => el.remove(), 5000);
    el.querySelector('.close-btn')?.addEventListener('click', () => el.remove());
  });
});

/* ══════════════════════════════════════════════════════════════
   GEOLOCATION + DISCOVERY
   ══════════════════════════════════════════════════════════════ */
function initDiscovery() {
  const loadingEl  = document.getElementById('loading-overlay');
  const bannerText = document.getElementById('location-banner-text');
  const fallbackEl = document.getElementById('location-fallback');
  const gridEl     = document.getElementById('hospital-grid');

  showSkeletons(gridEl);

  if (!navigator.geolocation) {
    hideEl(loadingEl);
    showFallback(fallbackEl);
    return;
  }

  navigator.geolocation.getCurrentPosition(
    pos => {
      EMERGIX.userLat = pos.coords.latitude;
      EMERGIX.userLng = pos.coords.longitude;
      hideEl(loadingEl);
      reverseGeocode(EMERGIX.userLat, EMERGIX.userLng, bannerText);
      fetchHospitals();
    },
    _err => {
      hideEl(loadingEl);
      showFallback(fallbackEl);
    },
    { timeout: 10000, maximumAge: 60000 }
  );
}

/* ── Reverse geocode for display label ───────────────────────── */
function reverseGeocode(lat, lng, el) {
  if (!el) return;
  fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`,
    { headers: { 'Accept-Language': 'en' } })
    .then(r => r.json())
    .then(d => {
      const area = d.address?.suburb || d.address?.neighbourhood ||
                   d.address?.town   || d.address?.city ||
                   d.address?.state  || 'Your Location';
      const city = d.address?.city || d.address?.state_district || '';
      el.textContent = city ? `${area}, ${city}` : area;
    })
    .catch(() => { el.textContent = 'Your Location'; });
}

/* ── Fetch hospitals from API ────────────────────────────────── */
let _fetchController = null;   // abort previous in-flight request on new search

function fetchHospitals() {
  if (!EMERGIX.userLat || !EMERGIX.userLng) return;

  // Abort any in-flight search
  if (_fetchController) _fetchController.abort();
  _fetchController = new AbortController();

  const { radius, hospitalType, availableOnly } = EMERGIX.activeFilters;
  const url =
    `/api/hospitals/nearby?lat=${EMERGIX.userLat}&lng=${EMERGIX.userLng}` +
    `&radius=${radius}&hospital_type=${hospitalType}` +
    `&available_only=${availableOnly}`;

  const gridEl = document.getElementById('hospital-grid');
  showSkeletons(gridEl);

  fetch(url, {
    signal: _fetchController.signal,
    credentials: 'same-origin',
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
    .then(r => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    })
    .then(data => {
      if (!data.success) throw new Error(data.error || 'Server error');
      EMERGIX.hospitals = data.data.hospitals;

      if (data.data.count === 0 && data.data.nearest_served) {
        showNearestCity(data.data.nearest_served, gridEl);
      } else {
        renderHospitals(EMERGIX.hospitals);
      }
    })
    .catch(e => {
      if (e.name === 'AbortError') return;   // intentionally cancelled
      console.error('Hospital fetch error:', e);
      showGridError(gridEl, e.message || 'Could not load hospitals. Please retry.');
    });
}

/* ── Render hospital cards ───────────────────────────────────── */
function renderHospitals(hospitals) {
  const grid = document.getElementById('hospital-grid');
  if (!grid) return;
  grid.innerHTML = '';

  const activeBedTypes = EMERGIX.activeFilters.bedTypes;
  const filtered = activeBedTypes.length
    ? hospitals.filter(h =>
        activeBedTypes.some(t => {
          const b = h.bed_inventory.find(b => b.bed_type === t);
          return b && b.available_beds > 0;
        })
      )
    : hospitals;

  const countEl = document.getElementById('result-count');
  if (countEl) countEl.textContent =
    `${filtered.length} hospital${filtered.length !== 1 ? 's' : ''} found`;

  if (!filtered.length) {
    grid.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1">
        <div class="empty-state-icon"><i class="fa-solid fa-hospital-slash"></i></div>
        <h3>No matching hospitals</h3>
        <p>Try removing bed-type filters or increasing the search radius.</p>
        <button class="btn btn-outline" onclick="clearFilters()">Clear Filters</button>
      </div>`;
    return;
  }

  filtered.forEach((h, i) => {
    const card = buildHospitalCard(h);
    card.style.animationDelay = `${i * 0.04}s`;
    card.style.opacity = '0';
    card.classList.add('animate-fade');
    grid.appendChild(card);
  });
}

/* ── "We don't serve your city" panel ───────────────────────── */
function showNearestCity(nearest, gridEl) {
  const countEl = document.getElementById('result-count');
  if (countEl) countEl.textContent = '0 hospitals found';

  gridEl.innerHTML = `
    <div style="grid-column:1/-1">
      <div class="glass" style="padding:2.5rem;text-align:center;max-width:580px;margin:0 auto;">
        <div style="font-size:3rem;margin-bottom:1rem">📍</div>
        <h3 style="font-family:var(--font-display);color:var(--teal-dark);margin-bottom:.6rem">
          EMERGIX doesn't cover your area yet
        </h3>
        <p style="color:var(--slate);margin-bottom:1.5rem;line-height:1.7">
          We couldn't find any hospitals within
          <strong>${EMERGIX.activeFilters.radius} km</strong> of your location.
          The nearest city we serve is
          <strong style="color:var(--teal-dark)">${escHtml(nearest.city)}</strong>
          — just <strong>${nearest.distance_km} km away</strong>
          with <strong>${nearest.hospital_count}</strong> hospitals tracked.
        </p>
        <div style="display:flex;flex-wrap:wrap;gap:.75rem;justify-content:center;">
          <button class="btn btn-primary" onclick="searchInCity(${nearest.lat},${nearest.lng},'${escHtml(nearest.city)}')">
            <i class="fa-solid fa-magnifying-glass-location"></i>
            Search in ${escHtml(nearest.city)}
          </button>
          <button class="btn btn-outline" onclick="setRadius(25);fetchHospitals()">
            <i class="fa-solid fa-expand"></i> Expand radius to 25 km
          </button>
        </div>
        <p style="font-size:.78rem;color:var(--slate-light);margin-top:1.25rem">
          <i class="fa-solid fa-circle-info"></i>
          We are rapidly onboarding hospitals across India.
          In an emergency, please also call <strong>112</strong> (National Emergency).
        </p>
      </div>
    </div>`;
}

/* ── Search in a specific city (nearest served) ──────────────── */
function searchInCity(lat, lng, cityName) {
  EMERGIX.userLat = lat;
  EMERGIX.userLng = lng;
  const bannerEl = document.getElementById('location-banner-text');
  if (bannerEl) bannerEl.textContent = cityName;
  fetchHospitals();
}

/* ── Build a single hospital card ───────────────────────────── */
function buildHospitalCard(h) {
  const div = document.createElement('div');
  div.className = 'hospital-card';
  div.dataset.hospitalId = h.id;

  const typeLabels = { government: 'GOVT', private: 'PRIVATE', trust: 'TRUST' };
  const typeBadge  = `badge-${h.hospital_type === 'government' ? 'govt' : h.hospital_type}`;
  const mapsUrl    = buildMapsUrl(EMERGIX.userLat, EMERGIX.userLng, h.latitude, h.longitude);

  div.innerHTML = `
    <div class="hospital-card-header" onclick="goToDetail(${h.id})">
      <div class="hospital-card-meta">
        <span class="badge ${typeBadge}">${typeLabels[h.hospital_type] || h.hospital_type.toUpperCase()}</span>
        ${h.emergency_24h ? '<span class="badge badge-24h"><i class="fa-solid fa-clock"></i> 24h ER</span>' : ''}
        ${h.ambulance     ? '<span class="badge badge-24h"><i class="fa-solid fa-truck-medical"></i></span>' : ''}
      </div>
      <div class="hospital-card-name">${escHtml(h.name)}</div>
      <div class="hospital-card-address">
        <i class="fa-solid fa-location-dot" style="color:var(--teal);margin-top:2px;flex-shrink:0"></i>
        <span>${escHtml(h.address)}</span>
      </div>
      <div class="distance-chip" style="margin-bottom:.5rem">
        <i class="fa-solid fa-route"></i> ${h.distance_km} km away
      </div>
    </div>
    <div class="bed-grid">${h.bed_inventory.map(buildBedCell).join('')}</div>
    <div class="hospital-card-actions">
      <a class="btn btn-ghost btn-sm" href="${mapsUrl}" target="_blank" rel="noopener"
         onclick="event.stopPropagation()">
        <i class="fa-solid fa-map-location-dot"></i> Navigate
      </a>
      <button class="btn btn-primary btn-sm"
              onclick="event.stopPropagation();openAlertModal(${h.id},'${escHtml(h.name)}',${h.latitude},${h.longitude})">
        <i class="fa-solid fa-bell"></i> Alert Hospital
      </button>
    </div>`;
  return div;
}

/* ── Build a bed cell inside a card ──────────────────────────── */
function buildBedCell(b) {
  const avail    = b.available_beds;
  const total    = b.total_beds;
  const pct      = b.occupancy_pct;
  const isFull   = avail === 0;
  const isCrit   = !isFull && pct >= 80;
  const cls      = isFull ? 'full' : isCrit ? 'critical' : 'ok';
  const barCls   = isFull ? 'progress-critical' : isCrit ? 'progress-warning' : 'progress-ok';
  const display  = isFull
    ? `<span style="font-size:.68rem;color:var(--danger);font-weight:700;line-height:1">FULL</span>`
    : `<span class="bed-cell-count ${cls}">${avail}</span>`;

  return `<div class="bed-cell">
    <div class="bed-cell-icon"><i class="fa-solid ${b.bed_type_icon}"></i></div>
    <div class="bed-cell-label">${b.bed_type_label}</div>
    ${display}
    <div class="bed-cell-sub">of ${total}</div>
    <div class="bed-progress">
      <div class="bed-progress-bar ${barCls}" style="width:${pct}%"></div>
    </div>
  </div>`;
}

/* ── Google Maps URL ─────────────────────────────────────────── */
function buildMapsUrl(lat1, lng1, lat2, lng2) {
  return `https://www.google.com/maps/dir/?api=1` +
         `&origin=${lat1},${lng1}&destination=${lat2},${lng2}&travelmode=driving`;
}

/* ── Navigate to hospital detail ────────────────────────────── */
function goToDetail(id) {
  const lat = EMERGIX.userLat || '';
  const lng = EMERGIX.userLng || '';
  window.location.href = `/hospitals/${id}?ulat=${lat}&ulng=${lng}`;
}

/* ── Fallback manual location search ────────────────────────── */
function showFallback(el) {
  if (el) el.style.display = 'flex';
}

function searchByCity(query) {
  if (!query?.trim()) return;
  const btn = document.getElementById('manual-search-btn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>'; }

  fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`,
    { headers: { 'Accept-Language': 'en' } })
    .then(r => r.json())
    .then(d => {
      if (d && d[0]) {
        EMERGIX.userLat = parseFloat(d[0].lat);
        EMERGIX.userLng = parseFloat(d[0].lon);
        document.getElementById('location-fallback').style.display = 'none';
        const bannerEl = document.getElementById('location-banner-text');
        if (bannerEl) bannerEl.textContent = query;
        fetchHospitals();
      } else {
        showToast('Location not found', 'Try a different area name.', 'warning');
      }
    })
    .catch(() => showToast('Error', 'Could not search for that location.', 'danger'))
    .finally(() => {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-search"></i> Go'; }
    });
}

/* ══════════════════════════════════════════════════════════════
   FILTERS
   ══════════════════════════════════════════════════════════════ */
function toggleBedTypeFilter(type, btn) {
  const idx = EMERGIX.activeFilters.bedTypes.indexOf(type);
  if (idx === -1) { EMERGIX.activeFilters.bedTypes.push(type); btn.classList.add('active'); }
  else            { EMERGIX.activeFilters.bedTypes.splice(idx, 1); btn.classList.remove('active'); }
  renderHospitals(EMERGIX.hospitals);
}

function setHospitalType(type, btn) {
  EMERGIX.activeFilters.hospitalType = type;
  document.querySelectorAll('.type-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  fetchHospitals();
}

function setAvailableOnly(checked) {
  EMERGIX.activeFilters.availableOnly = checked;
  fetchHospitals();
}

function setRadius(km, btn) {
  EMERGIX.activeFilters.radius = km;
  document.querySelectorAll('.radius-btn').forEach(b =>
    b.classList.toggle('active', parseInt(b.dataset.radius) === km));
  if (btn) btn.classList.add('active');
  fetchHospitals();
}

function clearFilters() {
  EMERGIX.activeFilters.bedTypes = [];
  EMERGIX.activeFilters.hospitalType = 'all';
  document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  document.querySelector('.type-filter-btn[data-type="all"]')?.classList.add('active');
  document.querySelector('.radius-btn[data-radius="10"]')?.classList.add('active');
  EMERGIX.activeFilters.radius = 10;
  renderHospitals(EMERGIX.hospitals);
}

/* ══════════════════════════════════════════════════════════════
   REAL-TIME BED UPDATES (WebSocket)
   ══════════════════════════════════════════════════════════════ */
function applyBedUpdate(data) {
  // Update in-memory store
  const hospital = EMERGIX.hospitals.find(h => h.id === data.hospital_id);
  if (hospital) {
    const bed = hospital.bed_inventory.find(b => b.bed_type === data.bed_type);
    if (bed) {
      bed.available_beds  = data.available_beds;
      bed.total_beds      = data.total_beds;
      bed.occupancy_pct   = data.occupancy_pct;
    }
    hospital.total_available = hospital.bed_inventory.reduce(
      (s, b) => s + b.available_beds, 0);
  }

  // Update DOM if the card is visible
  const card = document.querySelector(
    `.hospital-card[data-hospital-id="${data.hospital_id}"]`);
  if (!card) return;

  const bedTypes = ['general','icu','oxygen','ventilator','opd','emergency','pediatric','maternity'];
  const idx = bedTypes.indexOf(data.bed_type);
  const cells = card.querySelectorAll('.bed-cell');
  if (!cells[idx]) return;

  const cell = cells[idx];
  const isFull = data.available_beds === 0;
  const isCrit = !isFull && data.occupancy_pct >= 80;
  const cls    = isFull ? 'full' : isCrit ? 'critical' : 'ok';

  // Animate the number change
  const countEl = cell.querySelector('.bed-cell-count, span[style*="FULL"]');
  if (countEl) {
    countEl.className = `bed-cell-count ${cls}`;
    countEl.style.transform = 'scale(1.3)';
    countEl.textContent = isFull ? 'FULL' : data.available_beds;
    setTimeout(() => { countEl.style.transform = 'scale(1)'; }, 300);
  }
  const bar = cell.querySelector('.bed-progress-bar');
  if (bar) {
    bar.style.width = data.occupancy_pct + '%';
    bar.className = 'bed-progress-bar ' +
      (isFull ? 'progress-critical' : isCrit ? 'progress-warning' : 'progress-ok');
  }
}

/* ══════════════════════════════════════════════════════════════
   LOADING STATES
   ══════════════════════════════════════════════════════════════ */
function showSkeletons(grid) {
  if (!grid) return;
  grid.innerHTML = Array(6).fill(0).map(() => `
    <div class="hospital-card" style="pointer-events:none">
      <div class="hospital-card-header">
        <div class="skeleton" style="height:20px;width:80px;margin-bottom:.6rem;border-radius:99px"></div>
        <div class="skeleton" style="height:26px;width:85%;margin-bottom:.4rem"></div>
        <div class="skeleton" style="height:15px;width:70%;margin-bottom:.4rem"></div>
        <div class="skeleton" style="height:20px;width:38%;border-radius:99px"></div>
      </div>
      <div class="bed-grid">
        ${Array(8).fill('<div class="bed-cell"><div class="skeleton" style="height:72px;border-radius:8px"></div></div>').join('')}
      </div>
      <div class="hospital-card-actions">
        <div class="skeleton" style="height:38px;flex:1;border-radius:8px"></div>
        <div class="skeleton" style="height:38px;flex:1;border-radius:8px"></div>
      </div>
    </div>`).join('');
}

function showGridError(grid, msg) {
  if (!grid) return;
  grid.innerHTML = `
    <div class="empty-state" style="grid-column:1/-1">
      <div class="empty-state-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
      <h3>Could not load hospitals</h3>
      <p>${escHtml(msg || 'An error occurred. Please try again.')}</p>
      <button class="btn btn-primary" onclick="fetchHospitals()">
        <i class="fa-solid fa-rotate-right"></i> Retry
      </button>
    </div>`;
}

function hideEl(el) { if (el) el.style.display = 'none'; }

/* ══════════════════════════════════════════════════════════════
   UTILITIES
   ══════════════════════════════════════════════════════════════ */
function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

function showToast(title, msg, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.borderLeftColor =
    type === 'success' ? 'var(--success)' :
    type === 'danger'  ? 'var(--danger)'  :
    type === 'warning' ? 'var(--warning)' : 'var(--teal)';
  toast.innerHTML = `<div class="toast-title">${escHtml(title)}</div><p>${escHtml(msg)}</p>`;
  container.prepend(toast);
  setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 400); }, 5000);
}
