"""
EMERGIX API Blueprint
All JSON endpoints. Session-auth (no CSRF needed - exempted in factory).
Hardened for concurrent load and concurrent bed bookings.
"""
from flask import Blueprint, request, jsonify, session
from sqlalchemy import select
from app.extensions import db
from app.models import (Hospital, BedInventory, LiveAlert, User,
                         BED_TYPES, BED_TYPE_LABELS, utcnow)
from app.utils.decorators import login_required, admin_required
from app.utils.geo import (get_hospitals_within_radius, validate_coordinates,
                            haversine_distance)
from app.sockets import emit_new_alert, emit_alert_acknowledged, emit_bed_updated
import logging

api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


# ── Response helpers ─────────────────────────────────────────────────────────

def ok(data=None, **kwargs):
    return jsonify({'success': True, 'data': data, **kwargs})

def err(message, code=400):
    return jsonify({'success': False, 'error': message}), code


# ── GET /api/hospitals/nearby ─────────────────────────────────────────────────

@api_bp.route('/hospitals/nearby')
@login_required
def hospitals_nearby():
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    if not lat or not lng:
        return err('lat and lng are required.', 400)
    if not validate_coordinates(lat, lng):
        return err('Invalid coordinates.', 400)

    lat, lng = float(lat), float(lng)
    radius = min(float(request.args.get('radius', 10)), 50)
    bed_type_filter  = request.args.get('bed_type', '')
    hosp_type_filter = request.args.get('hospital_type', 'all')
    available_only   = request.args.get('available_only', 'true').lower() == 'true'

    # ── Query hospitals ───────────────────────────────────────────────────────
    query = Hospital.query.filter_by(is_active=True)
    if hosp_type_filter != 'all':
        query = query.filter_by(hospital_type=hosp_type_filter)
    all_hospitals = query.all()

    nearby = get_hospitals_within_radius(all_hospitals, lat, lng, radius)

    # ── If none found in radius → find nearest served city ───────────────────
    if not nearby:
        nearest_city_info = _find_nearest_served_city(lat, lng, all_hospitals)
        return ok({
            'count': 0,
            'user_location': {'lat': lat, 'lng': lng},
            'radius_km': radius,
            'hospitals': [],
            'nearest_served': nearest_city_info,
        })

    # ── Build result list ─────────────────────────────────────────────────────
    results = []
    for hospital, dist in nearby:
        # Build inventory dict keyed by bed_type with correct field names
        raw_inv = {b.bed_type: {
            'bed_type':       b.bed_type,
            'bed_type_label': BED_TYPE_LABELS.get(b.bed_type, b.bed_type.title()),
            'bed_type_icon':  _bed_icon(b.bed_type),
            'total_beds':     b.total_beds,
            'available_beds': b.available_beds,           # ← FIXED (was 'available')
            'occupied_beds':  b.total_beds - b.available_beds,
            'occupancy_pct':  b.occupancy_pct(),
            'last_updated':   b.last_updated.isoformat() if b.last_updated else None,
        } for b in hospital.bed_inventory}

        total_avail = sum(v['available_beds'] for v in raw_inv.values())  # ← FIXED

        # Filter: available_only
        if available_only and total_avail == 0:
            continue

        # Filter: specific bed type requested
        if bed_type_filter:
            types = [t.strip() for t in bed_type_filter.split(',') if t.strip()]
            if not any(raw_inv.get(t, {}).get('available_beds', 0) > 0 for t in types):
                continue

        # Ordered inventory for all 8 types (fill gaps with zeros)
        ordered = []
        for bt in BED_TYPES:
            ordered.append(raw_inv.get(bt, {
                'bed_type': bt,
                'bed_type_label': BED_TYPE_LABELS.get(bt, bt.title()),
                'bed_type_icon':  _bed_icon(bt),
                'total_beds': 0, 'available_beds': 0,
                'occupied_beds': 0, 'occupancy_pct': 0, 'last_updated': None,
            }))

        results.append({
            'id':            hospital.id,
            'name':          hospital.name,
            'address':       hospital.address,
            'city':          hospital.city,
            'phone':         hospital.phone,
            'latitude':      hospital.latitude,
            'longitude':     hospital.longitude,
            'hospital_type': hospital.hospital_type,
            'emergency_24h': hospital.emergency_24h,
            'ambulance':     hospital.ambulance,
            'distance_km':   round(dist, 1),
            'bed_inventory': ordered,
            'total_available': total_avail,
            'total_beds':    sum(v['total_beds'] for v in raw_inv.values()),  # ← FIXED
        })

    return ok({
        'count':          len(results),
        'user_location':  {'lat': lat, 'lng': lng},
        'radius_km':      radius,
        'hospitals':      results,
        'nearest_served': None,
    })


def _find_nearest_served_city(user_lat, user_lng, all_hospitals):
    """Find the nearest city we cover when user is outside all radii."""
    if not all_hospitals:
        return None
    # Group hospitals by city, find closest city centroid
    city_hospitals = {}
    for h in all_hospitals:
        city_hospitals.setdefault(h.city, []).append(h)

    best = None
    best_dist = float('inf')
    for city, hospitals in city_hospitals.items():
        # City centroid = average of its hospitals' coordinates
        c_lat = sum(h.latitude for h in hospitals) / len(hospitals)
        c_lng = sum(h.longitude for h in hospitals) / len(hospitals)
        dist = haversine_distance(user_lat, user_lng, c_lat, c_lng)
        if dist < best_dist:
            best_dist = dist
            best = {
                'city':           city,
                'distance_km':    round(best_dist, 1),
                'hospital_count': len(hospitals),
                'lat':            round(c_lat, 4),
                'lng':            round(c_lng, 4),
            }
    return best


def _bed_icon(bed_type):
    return {
        'general': 'fa-bed', 'icu': 'fa-heart-pulse', 'oxygen': 'fa-lungs',
        'ventilator': 'fa-wind', 'opd': 'fa-stethoscope',
        'emergency': 'fa-truck-medical', 'pediatric': 'fa-child',
        'maternity': 'fa-baby',
    }.get(bed_type, 'fa-bed')


# ── GET /api/hospitals/<id> ───────────────────────────────────────────────────

@api_bp.route('/hospitals/<int:hospital_id>')
@login_required
def hospital_detail(hospital_id):
    hospital = Hospital.query.get_or_404(hospital_id)
    data = hospital.to_dict()
    data['bed_inventory'] = [b.to_dict() for b in hospital.bed_inventory]
    return ok(data)


# ── POST /api/alerts/create ───────────────────────────────────────────────────
# Hardened for concurrent submissions: uses DB-level row lock to atomically
# check + "soft-reserve" a bed slot before confirming the alert.

@api_bp.route('/alerts/create', methods=['POST'])
@login_required
def create_alert():
    if session.get('role') == 'hospital_admin':
        return err('Hospital staff cannot create patient alerts.', 403)

    data = request.get_json(silent=True)
    if not data:
        return err('JSON body required.', 400)

    required = ['hospital_id', 'patient_name', 'bed_type_needed', 'contact_phone']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return err(f'Missing: {", ".join(missing)}', 400)

    hospital = Hospital.query.get(data['hospital_id'])
    if not hospital or not hospital.is_active:
        return err('Hospital not found.', 404)

    bed_type = data['bed_type_needed']
    if bed_type not in BED_TYPES:
        return err(f'Invalid bed type: {bed_type}', 400)

    # ── Duplicate alert guard ─────────────────────────────────────────────────
    # Prevent the same user sending duplicate pending alerts to the same hospital
    # for the same bed type within 10 minutes.
    from datetime import timedelta
    cutoff = utcnow() - timedelta(minutes=10)
    duplicate = LiveAlert.query.filter_by(
        user_id=session['user_id'],
        hospital_id=hospital.id,
        bed_type_needed=bed_type,
        status='pending',
    ).filter(LiveAlert.created_at >= cutoff).first()
    if duplicate:
        return err(
            f'You already sent an alert to this hospital for a {bed_type.upper()} bed '
            f'(ref: {duplicate.booking_ref}). Please wait before sending another.',
            409
        )

    # ── Concurrency-safe bed availability check ───────────────────────────────
    # with_for_update() issues SELECT ... FOR UPDATE in PostgreSQL,
    # and an equivalent advisory lock in SQLite, preventing race conditions
    # where two patients simultaneously book the last available bed.
    bed_inv = (BedInventory.query
               .filter_by(hospital_id=hospital.id, bed_type=bed_type)
               .with_for_update()
               .first())

    if not bed_inv:
        return err(f'This hospital has no {bed_type.upper()} beds registered.', 404)

    if bed_inv.available_beds <= 0:
        return err(
            f'No {bed_type.upper()} beds available at {hospital.name} right now. '
            f'Please try a nearby hospital or choose a different bed type.',
            409
        )

    # ── Calculate distance ────────────────────────────────────────────────────
    user_lat = data.get('user_lat')
    user_lng = data.get('user_lng')
    distance_km = None
    if user_lat and user_lng:
        try:
            distance_km = round(
                haversine_distance(float(user_lat), float(user_lng),
                                   hospital.latitude, hospital.longitude), 1)
        except (TypeError, ValueError):
            pass

    # ── Create alert atomically ───────────────────────────────────────────────
    try:
        alert = LiveAlert(
            hospital_id=hospital.id,
            user_id=session['user_id'],
            patient_name=data['patient_name'],
            patient_age=data.get('patient_age'),
            patient_gender=data.get('patient_gender'),
            bed_type_needed=bed_type,
            contact_phone=data['contact_phone'],
            notes=data.get('notes', ''),
            est_arrival_min=data.get('est_arrival_min'),
            user_lat=user_lat,
            user_lng=user_lng,
            distance_km=distance_km,
        )
        db.session.add(alert)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Alert creation failed: {e}')
        return err('Could not save your alert. Please try again.', 500)

    # ── Emit WebSocket event ──────────────────────────────────────────────────
    try:
        emit_new_alert(hospital.id, alert.to_dict())
    except Exception as e:
        logger.warning(f'WebSocket emit failed (non-fatal): {e}')

    return ok({
        'booking_ref':   alert.booking_ref,
        'hospital_name': hospital.name,
        'bed_type':      bed_type,
        'status':        'pending',
        'distance_km':   distance_km,
        'message':       f'Alert sent to {hospital.name}. Reference: {alert.booking_ref}',
    })


# ── POST /api/alerts/<id>/cancel ──────────────────────────────────────────────

@api_bp.route('/alerts/<int:alert_id>/cancel', methods=['POST'])
@login_required
def cancel_alert(alert_id):
    alert = LiveAlert.query.get_or_404(alert_id)
    if alert.user_id != session['user_id']:
        return err('Unauthorized.', 403)
    if alert.status != 'pending':
        return err(f'Cannot cancel an alert with status: {alert.status}', 400)
    try:
        alert.status = 'cancelled'
        db.session.commit()
    except Exception:
        db.session.rollback()
        return err('Could not cancel the alert. Please try again.', 500)
    return ok({'booking_ref': alert.booking_ref, 'status': 'cancelled'})


# ── GET /api/user/alerts ──────────────────────────────────────────────────────

@api_bp.route('/user/alerts')
@login_required
def user_alerts():
    alerts = (LiveAlert.query
              .filter_by(user_id=session['user_id'])
              .order_by(LiveAlert.created_at.desc())
              .all())
    return ok({'alerts': [a.to_dict() for a in alerts]})


# ── PUT /api/admin/beds/update ────────────────────────────────────────────────
# Atomic bed count update with row-level locking.

@api_bp.route('/admin/beds/update', methods=['PUT'])
@admin_required
def update_beds():
    data = request.get_json(silent=True)
    if not data:
        return err('JSON body required.', 400)

    hospital_id = session.get('hospital_id')
    # Admin isolation: reject if they try to modify a different hospital
    if str(data.get('hospital_id')) != str(hospital_id):
        return err('Unauthorized: you may only update your own hospital.', 403)

    bed_type  = data.get('bed_type')
    available = data.get('available_beds')
    total     = data.get('total_beds')

    if bed_type not in BED_TYPES:
        return err(f'Invalid bed type: {bed_type}', 400)
    if available is None or total is None:
        return err('available_beds and total_beds are required.', 400)

    available, total = int(available), int(total)
    if available < 0 or total < 0:
        return err('Bed counts cannot be negative.', 400)
    if available > total:
        return err('Available beds cannot exceed total beds.', 400)

    # Row-level lock for this specific bed type
    bi = (BedInventory.query
          .filter_by(hospital_id=hospital_id, bed_type=bed_type)
          .with_for_update()
          .first())
    if not bi:
        bi = BedInventory(hospital_id=hospital_id, bed_type=bed_type)
        db.session.add(bi)

    bi.available_beds = available
    bi.total_beds     = total
    bi.last_updated   = utcnow()
    bi.updated_by     = session['user_id']

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Bed update failed: {e}')
        return err('Could not save bed count. Please retry.', 500)

    update_data = bi.to_dict()
    update_data['hospital_id'] = hospital_id
    try:
        emit_bed_updated(hospital_id, update_data)
    except Exception as e:
        logger.warning(f'WebSocket emit failed (non-fatal): {e}')

    return ok(update_data)


# ── PUT /api/admin/alerts/<id>/status ─────────────────────────────────────────

@api_bp.route('/admin/alerts/<int:alert_id>/status', methods=['PUT'])
@admin_required
def update_alert_status(alert_id):
    alert = LiveAlert.query.get_or_404(alert_id)
    if alert.hospital_id != session.get('hospital_id'):
        return err('Unauthorized.', 403)

    data = request.get_json(silent=True) or {}
    new_status = data.get('status')
    if new_status not in ('acknowledged', 'admitted', 'cancelled'):
        return err('Status must be: acknowledged, admitted, or cancelled.', 400)

    try:
        alert.status = new_status
        if new_status == 'acknowledged':
            alert.acknowledged_at = utcnow()
            alert.acknowledged_by = session['user_id']
        db.session.commit()
    except Exception:
        db.session.rollback()
        return err('Could not update status. Please retry.', 500)

    try:
        hospital = Hospital.query.get(alert.hospital_id)
        emit_alert_acknowledged(alert.user_id, {
            'booking_ref':   alert.booking_ref,
            'status':        new_status,
            'hospital_name': hospital.name if hospital else 'Hospital',
        })
    except Exception as e:
        logger.warning(f'WebSocket emit failed (non-fatal): {e}')

    return ok(alert.to_dict())


# ── GET /api/admin/alerts ─────────────────────────────────────────────────────

@api_bp.route('/admin/alerts')
@admin_required
def admin_alerts():
    hospital_id = session.get('hospital_id')
    status = request.args.get('status', 'all')
    query = LiveAlert.query.filter_by(hospital_id=hospital_id)
    if status != 'all':
        query = query.filter_by(status=status)
    alerts = query.order_by(LiveAlert.created_at.desc()).all()
    return ok({'alerts': [a.to_dict() for a in alerts]})
