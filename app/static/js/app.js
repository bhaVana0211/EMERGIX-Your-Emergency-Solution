/* EMERGIX — app.js: geolocation, hospital discovery, filtering */
'use strict';

const EMERGIX = window.EMERGIX || {};
EMERGIX.userLat = null;
EMERGIX.userLng = null;
EMERGIX.hospitals = [];
EMERGIX.activeFilters = { bedTypes: [], hospitalType: 'all', availableOnly: true, radius: 10 };

/* ── Navbar hamburger ────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const hamburger = document.getElementById('hamburger');
  const navLinks  = document.getElementById('nav-links');
  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => navLinks.classList.toggle('open'));
  }

  // Flash message auto-dismiss
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => el.remove(), 5000);
    el.querySelector('.close-btn')?.addEventListener('click', () => el.remove());
  });
});

/* ── Geolocation + Hospital Discovery ───────────────────────────── */
function initDiscovery() {
  const loadingEl   = document.getElementById('loading-overlay');
  const locationBannerEl = document.getElementById('location-banner-text');
  const fallbackEl  = document.getElementById('location-fallback');
  const hospitalGridEl = document.getElementById('hospital-grid');

  showSkeletons(hospitalGridEl);

  if (!navigator.geolocation) {
    hideLoading(loadingEl);
    showFallback(fallbackEl, loadingEl);
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      EMERGIX.userLat = pos.coords.latitude;
      EMERGIX.userLng = pos.coords.longitude;
      hideLoading(loadingEl);
      reverseGeocode(EMERGIX.userLat, EMERGIX.userLng, locationBannerEl);
      fetchHospitals();
    },
    (_err) => {
      hideLoading(loadingEl);
      showFallback(fallbackEl, loadingEl);
    },
    { timeout: 10000, maximumAge: 60000 }
  );
}

function hideLoading(el) { if (el) el.style.display = 'none'; }

function showFallback(fallbackEl, loadingEl) {
  hideLoading(loadingEl);
  if (fallbackEl) fallbackEl.style.display = 'flex';
}

function reverseGeocode(lat, lng, bannerEl) {
  if (!bannerEl) return;
  fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
    .then(r => r.json())
    .then(data => {
      const area = data.address?.suburb || data.address?.town ||
                   data.address?.city || data.address?.state || 'your location';
      bannerEl.textContent = area + ', ' + (data.address?.city || data.address?.state || '');
    })
    .catch(() => { bannerEl.textContent = 'Your Location'; });
}

function fetchHospitals() {
  if (!EMERGIX.userLat || !EMERGIX.userLng) return;
  const { radius, hospitalType, availableOnly } = EMERGIX.activeFilters;
  const url = `/api/hospitals/nearby?lat=${EMERGIX.userLat}&lng=${EMERGIX.userLng}` +
              `&radius=${radius}&hospital_type=${hospitalType}` +
              `&available_only=${availableOnly}`;

  fetch(url)
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        EMERGIX.hospitals = data.data.hospitals;
        renderHospitals(EMERGIX.hospitals);
      } else {
        showGridError(document.getElementById('hospital-grid'), data.error);
      }
    })
    .catch(() => showGridError(document.getElementById('hospital-grid'), 'Network error. Please retry.'));
}

function renderHospitals(hospitals) {
  const grid = document.getElementById('hospital-grid');
  if (!grid) return;
  grid.innerHTML = '';

  const activeBedTypes = EMERGIX.activeFilters.bedTypes;
  const filtered = activeBedTypes.length
    ? hospitals.filter(h => activeBedTypes.some(t => (h.bed_inventory.find(b => b.bed_type === t)?.available_beds || 0) > 0))
    : hospitals;

  const resultCountEl = document.getElementById('result-count');
  if (resultCountEl) resultCountEl.textContent = `${filtered.length} hospital${filtered.length !== 1 ? 's' : ''} found`;

  if (!filtered.length) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <div class="empty-state-icon"><i class="fa-solid fa-hospital-slash"></i></div>
      <h3>No hospitals found nearby</h3>
      <p>Try increasing the search radius or adjusting your filters.</p>
      <button class="btn btn-outline" onclick="setRadius(25);fetchHospitals()">Expand to 25 km</button>
    </div>`;
    return;
  }

  filtered.forEach((h, i) => {
    const card = buildHospitalCard(h);
    card.style.animationDelay = `${i * 0.04}s`;
    card.classList.add('animate-fade');
    card.style.opacity = 0;
    grid.appendChild(card);
  });
}

function buildHospitalCard(h) {
  const div = document.createElement('div');
  div.className = 'hospital-card';
  div.dataset.hospitalId = h.id;

  const typeLabel  = { government: 'GOVT', private: 'PRIVATE', trust: 'TRUST' }[h.hospital_type] || h.hospital_type.toUpperCase();
  const typeBadge  = `badge-${h.hospital_type === 'government' ? 'govt' : h.hospital_type}`;

  const bedCells = h.bed_inventory.map(b => buildBedCell(b)).join('');
  const mapsUrl = buildMapsUrl(EMERGIX.userLat, EMERGIX.userLng, h.latitude, h.longitude);

  div.innerHTML = `
    <div class="hospital-card-header" onclick="goToDetail(${h.id})">
      <div class="hospital-card-meta">
        <span class="badge ${typeBadge}">${typeLabel}</span>
        ${h.emergency_24h ? '<span class="badge badge-24h"><i class="fa-solid fa-clock"></i> 24h ER</span>' : ''}
        ${h.ambulance ? '<span class="badge badge-24h"><i class="fa-solid fa-truck-medical"></i></span>' : ''}
      </div>
      <div class="hospital-card-name">${escHtml(h.name)}</div>
      <div class="hospital-card-address">
        <i class="fa-solid fa-location-dot" style="color:var(--teal);margin-top:2px;flex-shrink:0"></i>
        <span>${escHtml(h.address)}</span>
      </div>
      <div class="distance-chip" style="margin-bottom:0.5rem">
        <i class="fa-solid fa-route"></i> ${h.distance_km} km away
      </div>
    </div>
    <div class="bed-grid">${bedCells}</div>
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

function buildBedCell(b) {
  const avail   = b.available_beds;
  const total   = b.total_beds;
  const pct     = b.occupancy_pct;
  const isFull  = avail === 0;
  const isCrit  = !isFull && pct >= 80;
  const countClass = isFull ? 'full' : isCrit ? 'critical' : 'ok';
  const barClass   = isFull ? 'progress-critical' : isCrit ? 'progress-warning' : 'progress-ok';
  const display    = isFull ? '<span style="font-size:.7rem;color:var(--danger);font-weight:700">FULL</span>'
                   : `<span class="bed-cell-count ${countClass}">${avail}</span>`;

  return `<div class="bed-cell">
    <div class="bed-cell-icon"><i class="fa-solid ${b.bed_type_icon}"></i></div>
    <div class="bed-cell-label">${b.bed_type_label}</div>
    ${display}
    <div class="bed-cell-sub">of ${total}</div>
    <div class="bed-progress"><div class="bed-progress-bar ${barClass}" style="width:${pct}%"></div></div>
  </div>`;
}

function buildMapsUrl(lat1, lng1, lat2, lng2) {
  return `https://www.google.com/maps/dir/?api=1&origin=${lat1},${lng1}&destination=${lat2},${lng2}&travelmode=driving`;
}

function goToDetail(id) {
  const lat = EMERGIX.userLat || '';
  const lng = EMERGIX.userLng || '';
  window.location.href = `/hospitals/${id}?ulat=${lat}&ulng=${lng}`;
}

function showSkeletons(grid) {
  if (!grid) return;
  grid.innerHTML = Array(6).fill(0).map(() => `
    <div class="hospital-card" style="pointer-events:none">
      <div class="hospital-card-header">
        <div class="skeleton" style="height:22px;width:80px;margin-bottom:.5rem"></div>
        <div class="skeleton" style="height:26px;width:85%;margin-bottom:.4rem"></div>
        <div class="skeleton" style="height:16px;width:70%;margin-bottom:.4rem"></div>
        <div class="skeleton" style="height:18px;width:40%"></div>
      </div>
      <div class="bed-grid">
        ${Array(8).fill('<div class="bed-cell"><div class="skeleton" style="height:60px"></div></div>').join('')}
      </div>
      <div class="hospital-card-actions">
        <div class="skeleton" style="height:36px;flex:1;border-radius:8px"></div>
        <div class="skeleton" style="height:36px;flex:1;border-radius:8px"></div>
      </div>
    </div>`).join('');
}

function showGridError(grid, msg) {
  if (!grid) return;
  grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
    <div class="empty-state-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
    <h3>Could not load hospitals</h3><p>${escHtml(msg || 'Please try again.')}</p>
    <button class="btn btn-primary" onclick="fetchHospitals()">Retry</button>
  </div>`;
}

/* ── Fallback manual search ──────────────────────────────────────── */
function searchByCity(query) {
  if (!query.trim()) return;
  const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`;
  fetch(url)
    .then(r => r.json())
    .then(data => {
      if (data && data[0]) {
        EMERGIX.userLat = parseFloat(data[0].lat);
        EMERGIX.userLng = parseFloat(data[0].lon);
        document.getElementById('location-fallback').style.display = 'none';
        document.getElementById('location-banner-text').textContent = query;
        fetchHospitals();
      } else {
        alert('Location not found. Please try a different search.');
      }
    });
}

/* ── Filters ─────────────────────────────────────────────────────── */
function toggleBedTypeFilter(type, btn) {
  const idx = EMERGIX.activeFilters.bedTypes.indexOf(type);
  if (idx === -1) {
    EMERGIX.activeFilters.bedTypes.push(type);
    btn.classList.add('active');
  } else {
    EMERGIX.activeFilters.bedTypes.splice(idx, 1);
    btn.classList.remove('active');
  }
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

function setRadius(km) {
  EMERGIX.activeFilters.radius = km;
  document.querySelectorAll('.radius-btn').forEach(b => {
    b.classList.toggle('active', parseInt(b.dataset.radius) === km);
  });
  fetchHospitals();
}

/* ── Real-time bed updates ───────────────────────────────────────── */
function applyBedUpdate(data) {
  const hospital = EMERGIX.hospitals.find(h => h.id === data.hospital_id);
  if (!hospital) return;
  const bed = hospital.bed_inventory.find(b => b.bed_type === data.bed_type);
  if (bed) {
    bed.available_beds = data.available_beds;
    bed.total_beds = data.total_beds;
    bed.occupancy_pct = data.occupancy_pct;
  }
  // Update just that card's bed cell
  const card = document.querySelector(`.hospital-card[data-hospital-id="${data.hospital_id}"]`);
  if (card) {
    const cells = card.querySelectorAll('.bed-cell');
    const bedTypes = ['general','icu','oxygen','ventilator','opd','emergency','pediatric','maternity'];
    const idx = bedTypes.indexOf(data.bed_type);
    if (cells[idx]) {
      const isFull = data.available_beds === 0;
      const isCrit = !isFull && data.occupancy_pct >= 80;
      const countEl = cells[idx].querySelector('.bed-cell-count, span[style*="FULL"]');
      if (countEl) {
        countEl.className = 'bed-cell-count ' + (isFull ? 'full' : isCrit ? 'critical' : 'ok');
        countEl.textContent = isFull ? 'FULL' : data.available_beds;
      }
      const bar = cells[idx].querySelector('.bed-progress-bar');
      if (bar) {
        bar.style.width = data.occupancy_pct + '%';
        bar.className = 'bed-progress-bar ' + (isFull ? 'progress-critical' : isCrit ? 'progress-warning' : 'progress-ok');
      }
    }
  }
}

/* ── Utilities ───────────────────────────────────────────────────── */
function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

function showToast(title, msg, type = 'info') {
  const container = document.getElementById('toast-container') ||
    (() => { const c = document.createElement('div'); c.id = 'toast-container';
              c.className = 'toast-container'; document.body.appendChild(c); return c; })();
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.borderLeftColor = type === 'success' ? 'var(--success)' :
                                 type === 'danger'  ? 'var(--danger)'  : 'var(--teal)';
  toast.innerHTML = `<div class="toast-title">${escHtml(title)}</div><p>${escHtml(msg)}</p>`;
  container.prepend(toast);
  setTimeout(() => toast.remove(), 5000);
}
