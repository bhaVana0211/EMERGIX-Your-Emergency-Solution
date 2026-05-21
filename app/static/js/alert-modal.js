/* EMERGIX — alert-modal.js: Pre-arrival booking modal */
'use strict';

let _modalHospitalId = null;

function openAlertModal(hospitalId, hospitalName, lat, lng) {
  _modalHospitalId = hospitalId;
  const overlay = document.getElementById('alert-modal-overlay');
  if (!overlay) return;
  document.getElementById('modal-hospital-name').textContent = hospitalName;

  // Pre-fill fields if user data is available
  const pre = window.EMERGIX_USER || {};
  const nameField = document.getElementById('alert-patient-name');
  const phoneField = document.getElementById('alert-contact-phone');
  if (nameField && pre.full_name) nameField.value = pre.full_name;
  if (phoneField && pre.phone) phoneField.value = pre.phone;

  // Reset form
  document.getElementById('alert-form')?.reset();
  if (nameField && pre.full_name) nameField.value = pre.full_name;
  if (phoneField && pre.phone) phoneField.value = pre.phone;

  hideElement('booking-confirm-section');
  showElement('alert-form-section');
  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeAlertModal() {
  const overlay = document.getElementById('alert-modal-overlay');
  if (overlay) overlay.classList.remove('open');
  document.body.style.overflow = '';
  _modalHospitalId = null;
}

// Close on overlay click
document.addEventListener('DOMContentLoaded', () => {
  const overlay = document.getElementById('alert-modal-overlay');
  if (overlay) {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeAlertModal();
    });
  }

  // Form submission
  const form = document.getElementById('alert-form');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      await submitAlert();
    });
  }
});

async function submitAlert() {
  const submitBtn = document.getElementById('alert-submit-btn');
  if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending…'; }

  const payload = {
    hospital_id: _modalHospitalId,
    patient_name: document.getElementById('alert-patient-name')?.value?.trim(),
    patient_age:  parseInt(document.getElementById('alert-patient-age')?.value) || null,
    patient_gender: document.querySelector('input[name="patient_gender"]:checked')?.value,
    bed_type_needed: document.getElementById('alert-bed-type')?.value,
    contact_phone: document.getElementById('alert-contact-phone')?.value?.trim(),
    notes: document.getElementById('alert-notes')?.value?.trim(),
    est_arrival_min: parseInt(document.getElementById('alert-arrival')?.value) || null,
    user_lat: EMERGIX.userLat,
    user_lng: EMERGIX.userLng,
  };

  if (!payload.patient_name || !payload.contact_phone || !payload.bed_type_needed) {
    showFormError('Please fill in all required fields.');
    if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = '<i class="fa-solid fa-bell"></i> Send Alert'; }
    return;
  }

  try {
    const res = await fetch('/api/alerts/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (data.success) {
      showBookingConfirm(data.data);
    } else {
      showFormError(data.error || 'Something went wrong. Please try again.');
    }
  } catch (err) {
    showFormError('Network error. Please check your connection and retry.');
  } finally {
    if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = '<i class="fa-solid fa-bell"></i> Send Alert'; }
  }
}

function showBookingConfirm(data) {
  hideElement('alert-form-section');
  showElement('booking-confirm-section');
  document.getElementById('booking-ref-display').textContent = data.booking_ref;
  document.getElementById('booking-hospital-display').textContent = data.hospital_name || '';
}

function copyBookingRef() {
  const ref = document.getElementById('booking-ref-display')?.textContent;
  if (!ref) return;
  navigator.clipboard.writeText(ref).then(() => {
    const btn = document.getElementById('copy-ref-btn');
    if (btn) { btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!'; setTimeout(() => { btn.innerHTML = '<i class="fa-solid fa-copy"></i> Copy'; }, 2000); }
  });
}

function showFormError(msg) {
  const el = document.getElementById('alert-form-error');
  if (el) { el.textContent = msg; el.style.display = 'block'; setTimeout(() => { el.style.display = 'none'; }, 5000); }
}

function showElement(id) { const el = document.getElementById(id); if (el) el.style.display = 'block'; }
function hideElement(id) { const el = document.getElementById(id); if (el) el.style.display = 'none'; }
