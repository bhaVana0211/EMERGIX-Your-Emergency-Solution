/* EMERGIX — admin-realtime.js: Socket.IO + bed management */
'use strict';

let socket;
let reconnectAttempts = 0;
const MAX_RECONNECT = 6;

function initAdminSocket() {
  if (typeof io === 'undefined') return;
  socket = io({ transports: ['websocket', 'polling'], reconnection: false });

  socket.on('connect', () => {
    reconnectAttempts = 0;
    hideBanner();
    socket.emit('join_hospital', {});
  });

  socket.on('disconnect', () => {
    showBanner('Connection lost. Reconnecting…');
    scheduleReconnect();
  });

  socket.on('connect_error', () => {
    scheduleReconnect();
  });

  socket.on('new_alert', (alertData) => {
    handleNewAlert(alertData);
  });
}

function scheduleReconnect() {
  if (reconnectAttempts >= MAX_RECONNECT) {
    showBanner('Connection lost. Please refresh the page.', true);
    return;
  }
  const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
  reconnectAttempts++;
  showBanner(`Reconnecting in ${Math.round(delay/1000)}s…`);
  setTimeout(() => { if (socket) socket.connect(); }, delay);
}

function showBanner(msg, isError = false) {
  const banner = document.getElementById('connection-banner');
  if (!banner) return;
  banner.classList.add('show');
  banner.innerHTML = `<i class="fa-solid fa-${isError ? 'triangle-exclamation' : 'circle-notch fa-spin'}"></i> ${msg}`;
  if (isError) banner.style.background = '#FEE2E2';
}

function hideBanner() {
  const banner = document.getElementById('connection-banner');
  if (banner) banner.classList.remove('show');
}

function handleNewAlert(alertData) {
  // Update pending count badge
  const badge = document.getElementById('sidebar-alert-badge');
  if (badge) {
    const current = parseInt(badge.textContent || '0');
    badge.textContent = current + 1;
    badge.style.display = 'inline';
  }

  // Update dashboard pending count
  const pendingEl = document.getElementById('stat-pending');
  if (pendingEl) pendingEl.textContent = parseInt(pendingEl.textContent || '0') + 1;

  // Browser notification
  if (Notification.permission === 'granted') {
    new Notification('New Patient Alert — EMERGIX', {
      body: `${alertData.patient_name} needs a ${alertData.bed_type_label} bed.`,
      icon: '/static/images/logo.png',
    });
  }

  // If on alerts page, inject the card
  const alertsContainer = document.getElementById('alerts-container');
  if (alertsContainer) {
    const card = buildAlertCard(alertData);
    card.classList.add('new-alert');
    alertsContainer.prepend(card);
    const emptyState = document.getElementById('empty-alerts');
    if (emptyState) emptyState.remove();
  }

  showToast('🔔 New Alert', `${alertData.patient_name} en route — needs ${alertData.bed_type_label} bed.`, 'warning');
}

function buildAlertCard(a) {
  const div = document.createElement('div');
  div.className = 'alert-card';
  div.id = `alert-card-${a.id}`;
  const arrivalText = a.est_arrival_min ? `~${a.est_arrival_min} min` : 'Unknown';
  div.innerHTML = `
    <div class="alert-header">
      <div>
        <div class="alert-patient-name">${escHtml(a.patient_name)}</div>
        <div class="alert-meta">
          <span class="badge badge-pending"><span class="status-dot pending"></span> Pending</span>
          <span class="alert-ref">${escHtml(a.booking_ref)}</span>
        </div>
      </div>
      <div>
        <span class="badge badge-private" style="font-size:.8rem">
          <i class="fa-solid fa-bed"></i> ${escHtml(a.bed_type_label || a.bed_type_needed)}
        </span>
      </div>
    </div>
    <div class="alert-detail-row">
      ${a.patient_age ? `<div class="alert-detail"><i class="fa-solid fa-user"></i> Age ${a.patient_age}${a.patient_gender ? ', ' + a.patient_gender : ''}</div>` : ''}
      <div class="alert-detail"><i class="fa-solid fa-phone"></i> <a href="tel:${escHtml(a.contact_phone)}">${escHtml(a.contact_phone)}</a></div>
      <div class="alert-detail"><i class="fa-solid fa-clock"></i> Arrival: ${arrivalText}</div>
      ${a.distance_km ? `<div class="alert-detail"><i class="fa-solid fa-route"></i> ${a.distance_km} km away</div>` : ''}
    </div>
    ${a.notes ? `<div class="alert-notes"><i class="fa-solid fa-note-sticky"></i> ${escHtml(a.notes)}</div>` : ''}
    <div class="alert-actions">
      <button class="btn btn-primary btn-sm" onclick="updateAlertStatus(${a.id},'acknowledged',this)">
        <i class="fa-solid fa-check"></i> Acknowledge
      </button>
      <button class="btn btn-ghost btn-sm" onclick="updateAlertStatus(${a.id},'admitted',this)">
        <i class="fa-solid fa-bed-pulse"></i> Mark Admitted
      </button>
      <button class="btn btn-sm" style="background:rgba(100,116,139,0.1);color:var(--slate)"
              onclick="updateAlertStatus(${a.id},'cancelled',this)">
        <i class="fa-solid fa-xmark"></i> Cancel
      </button>
    </div>`;
  return div;
}

/* ── Alert status update ─────────────────────────────────────────── */
async function updateAlertStatus(alertId, status, btn) {
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>'; }
  try {
    const res = await fetch(`/api/admin/alerts/${alertId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    const data = await res.json();
    if (data.success) {
      const card = document.getElementById(`alert-card-${alertId}`);
      if (card) {
        const badgeEl = card.querySelector('.badge-pending, .badge-acknowledged, .badge-admitted, .badge-cancelled');
        if (badgeEl) {
          const labels = { acknowledged: 'Acknowledged', admitted: 'Admitted', cancelled: 'Cancelled' };
          badgeEl.className = `badge badge-${status}`;
          badgeEl.innerHTML = `<span class="status-dot ${status}"></span> ${labels[status]}`;
        }
        card.querySelectorAll('.alert-actions .btn').forEach(b => b.remove());
        if (status === 'acknowledged') {
          const actDiv = card.querySelector('.alert-actions');
          if (actDiv) actDiv.innerHTML = `<button class="btn btn-ghost btn-sm" onclick="updateAlertStatus(${alertId},'admitted',this)"><i class="fa-solid fa-bed-pulse"></i> Mark Admitted</button>`;
        }
      }
      // Update badges
      if (status !== 'pending') {
        const badge = document.getElementById('sidebar-alert-badge');
        if (badge) {
          const val = Math.max(0, parseInt(badge.textContent || '0') - 1);
          badge.textContent = val;
          if (val === 0) badge.style.display = 'none';
        }
        const pendingEl = document.getElementById('stat-pending');
        if (pendingEl) pendingEl.textContent = Math.max(0, parseInt(pendingEl.textContent || '0') - 1);
      }
      showToast('Updated', `Alert marked as ${status}.`, 'success');
    } else {
      showToast('Error', data.error || 'Could not update status.', 'danger');
    }
  } catch (err) {
    showToast('Error', 'Network error. Please retry.', 'danger');
  } finally {
    if (btn) { btn.disabled = false; }
  }
}

/* ── Bed management ──────────────────────────────────────────────── */
const pendingUpdates = {};
const debounceTimers = {};

function changeBed(hospitalId, bedType, direction) {
  const valueEl = document.getElementById(`avail-${bedType}`);
  const totalEl = document.getElementById(`total-${bedType}`);
  if (!valueEl || !totalEl) return;

  let current = parseInt(valueEl.textContent) || 0;
  const total  = parseInt(totalEl.textContent) || 0;
  current = Math.max(0, Math.min(total, current + direction));
  valueEl.textContent = current;
  valueEl.classList.add('flash-update');
  setTimeout(() => valueEl.classList.remove('flash-update'), 500);

  // Update progress bar
  const bar = document.getElementById(`bar-${bedType}`);
  if (bar && total > 0) {
    const pct = Math.round(((total - current) / total) * 100);
    bar.style.width = pct + '%';
    bar.className = 'occ-bar-fill ' + (pct >= 90 ? 'progress-critical' : pct >= 70 ? 'progress-warning' : 'progress-ok');
    const pctEl = document.getElementById(`pct-${bedType}`);
    if (pctEl) pctEl.textContent = pct + '% occupied';
  }

  if (!pendingUpdates[bedType]) pendingUpdates[bedType] = {};
  pendingUpdates[bedType] = { available_beds: current, total_beds: total };

  clearTimeout(debounceTimers[bedType]);
  debounceTimers[bedType] = setTimeout(() => saveBed(hospitalId, bedType), 1200);
}

async function saveBed(hospitalId, bedType) {
  const update = pendingUpdates[bedType];
  if (!update) return;

  try {
    const res = await fetch('/api/admin/beds/update', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hospital_id: hospitalId, bed_type: bedType, ...update }),
    });
    const data = await res.json();
    if (data.success) {
      delete pendingUpdates[bedType];
      showSaveIndicator(bedType, true);
    } else {
      showSaveIndicator(bedType, false, data.error);
    }
  } catch (err) {
    showSaveIndicator(bedType, false, 'Network error');
  }
}

async function saveAllBeds(hospitalId) {
  const types = ['general','icu','oxygen','ventilator','opd','emergency','pediatric','maternity'];
  for (const bedType of types) {
    const valueEl = document.getElementById(`avail-${bedType}`);
    const totalEl = document.getElementById(`total-${bedType}`);
    if (!valueEl || !totalEl) continue;
    const available = parseInt(valueEl.textContent) || 0;
    const total = parseInt(totalEl.textContent) || 0;
    await saveBed(hospitalId, bedType);
    // Collect new totals
    pendingUpdates[bedType] = { available_beds: available, total_beds: total };
    await saveBed(hospitalId, bedType);
  }
  showToast('Saved', 'All bed counts updated successfully.', 'success');
}

function showSaveIndicator(bedType, ok, errMsg) {
  const el = document.getElementById(`save-${bedType}`);
  if (!el) return;
  el.style.display = 'inline';
  el.textContent = ok ? '✓ Saved' : `⚠ ${errMsg || 'Error'}`;
  el.style.color = ok ? 'var(--success)' : 'var(--danger)';
  setTimeout(() => { el.style.display = 'none'; }, 3000);
}

/* ── Notification permission ──────────────────────────────────────── */
if (Notification.permission === 'default') {
  Notification.requestPermission();
}

/* ── Utilities ───────────────────────────────────────────────────── */
function escHtml(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

function showToast(title, msg, type) {
  const container = document.getElementById('toast-container') ||
    (() => { const c = document.createElement('div'); c.id = 'toast-container';
             c.className = 'toast-container'; document.body.appendChild(c); return c; })();
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.borderLeftColor = type === 'success' ? 'var(--success)'
                               : type === 'danger'  ? 'var(--danger)'
                               : type === 'warning' ? 'var(--warning)'
                               : 'var(--teal)';
  toast.innerHTML = `<div class="toast-title">${title}</div><p>${msg}</p>`;
  container.prepend(toast);
  setTimeout(() => toast.remove(), 5000);
}

/* ── Sidebar mobile toggle ───────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const mobileBtn = document.getElementById('mobile-menu-btn');
  const sidebar   = document.getElementById('sidebar');
  const overlay   = document.getElementById('sidebar-overlay');

  function openSidebar() {
    sidebar?.classList.add('open');
    overlay?.classList.add('show');
  }
  function closeSidebar() {
    sidebar?.classList.remove('open');
    overlay?.classList.remove('show');
  }

  mobileBtn?.addEventListener('click', openSidebar);
  overlay?.addEventListener('click', closeSidebar);

  initAdminSocket();
});
