from flask import Blueprint, request, jsonify, session
from app.extensions import db
from app.models import (Hospital, BedInventory, LiveAlert, User,
                         BED_TYPES, BED_TYPE_LABELS, utcnow)
from app.utils.decorators import login_required, admin_required
from app.utils.geo import get_hospitals_within_radius, validate_coordinates, haversine_distance
from app.sockets import emit_new_alert, emit_alert_acknowledged, emit_bed_updated
import logging

api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


def success(data=None, **kwargs):
    return jsonify({'success': True, 'data': data, **kwargs})


def error(message, code=400):
    return jsonify({'success': False, 'error': message}), code


# ─── Hospitals ──────────────────────────────────────────────────────────────

@api_bp.route('/hospitals/nearby')
@login_required
def hospitals_nearby():
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    radius = float(request.args.get('radius', 10))
    bed_type_filter = request.args.get('bed_type', '')
    hospital_type_filter = request.args.get('hospital_type', 'all')
    available_only = request.args.get('available_only', 'true').lower() == 'true'

    if not lat or not lng:
        return error('lat and lng are required query parameters.', 400)
    if not validate_coordinates(lat, lng):
        return error('Invalid coordinates.', 400)
    radius = min(float(radius), 50)

    lat, lng = float(lat), float(lng)
    query = Hospital.query.filter_by(is_active=True)
    if hospital_type_filter != 'all':
        query = query.filter_by(hospital_type=hospital_type_filter)
    all_hospitals = query.all()

    nearby = get_hospitals_within_radius(all_hospitals, lat, lng, radius)

    results = []
    for hospital, dist in nearby:
        inventory = {b.bed_type: b.to_dict() for b in hospital.bed_inventory}

        if available_only and sum(b['available'] for b in inventory.values()) == 0:
            continue
        if bed_type_filter:
            types = [t.strip() for t in bed_type_filter.split(',') if t.strip()]
            has_type = any(inventory.get(t, {}).get('available', 0) > 0 for t in types)
            if not has_type:
                continue

        # Build ordered inventory for all 8 types
        ordered_inventory = []
        for bt in BED_TYPES:
            if bt in inventory:
                ordered_inventory.append(inventory[bt])
            else:
                ordered_inventory.append({
                    'bed_type': bt,
                    'bed_type_label': BED_TYPE_LABELS.get(bt, bt.title()),
                    'bed_type_icon': 'fa-bed',
                    'total_beds': 0,
                    'available_beds': 0,
                    'occupied_beds': 0,
                    'occupancy_pct': 0,
                    'last_updated': None,
                })

        results.append({
            'id': hospital.id,
            'name': hospital.name,
            'address': hospital.address,
            'city': hospital.city,
            'phone': hospital.phone,
            'latitude': hospital.latitude,
            'longitude': hospital.longitude,
            'hospital_type': hospital.hospital_type,
            'emergency_24h': hospital.emergency_24h,
            'ambulance': hospital.ambulance,
            'distance_km': round(dist, 1),
            'bed_inventory': ordered_inventory,
            'total_available': sum(b['available'] for b in inventory.values()),
            'total_beds': sum(b['total'] for b in inventory.values()),
        })

    return success({
        'count': len(results),
        'user_location': {'lat': lat, 'lng': lng},
        'radius_km': radius,
        'hospitals': results
    })


@api_bp.route('/hospitals/<int:hospital_id>')
@login_required
def hospital_detail(hospital_id):
    hospital = Hospital.query.get_or_404(hospital_id)
    data = hospital.to_dict()
    data['bed_inventory'] = [b.to_dict() for b in hospital.bed_inventory]
    return success(data)


# ─── Alerts ─────────────────────────────────────────────────────────────────

@api_bp.route('/alerts/create', methods=['POST'])
@login_required
def create_alert():
    if session.get('role') == 'hospital_admin':
        return error('Hospital staff cannot create patient alerts.', 403)

    data = request.get_json()
    if not data:
        return error('JSON body required.', 400)

    required = ['hospital_id', 'patient_name', 'bed_type_needed', 'contact_phone']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error(f'Missing required fields: {", ".join(missing)}', 400)

    hospital = Hospital.query.get(data['hospital_id'])
    if not hospital or not hospital.is_active:
        return error('Hospital not found.', 404)

    user_lat = data.get('user_lat')
    user_lng = data.get('user_lng')
    distance_km = None
    if user_lat and user_lng:
        try:
            distance_km = round(haversine_distance(
                float(user_lat), float(user_lng),
                hospital.latitude, hospital.longitude
            ), 1)
        except (TypeError, ValueError):
            pass

    alert = LiveAlert(
        hospital_id=hospital.id,
        user_id=session['user_id'],
        patient_name=data['patient_name'],
        patient_age=data.get('patient_age'),
        patient_gender=data.get('patient_gender'),
        bed_type_needed=data['bed_type_needed'],
        contact_phone=data['contact_phone'],
        notes=data.get('notes', ''),
        est_arrival_min=data.get('est_arrival_min'),
        user_lat=user_lat,
        user_lng=user_lng,
        distance_km=distance_km,
    )
    db.session.add(alert)
    db.session.commit()

    # Emit WebSocket event to hospital
    try:
        emit_new_alert(hospital.id, alert.to_dict())
    except Exception as e:
        logger.warning(f'WebSocket emit failed: {e}')

    return success({
        'booking_ref': alert.booking_ref,
        'hospital_name': hospital.name,
        'bed_type': data['bed_type_needed'],
        'status': 'pending',
        'distance_km': distance_km,
        'message': f'Alert sent to {hospital.name}. Reference: {alert.booking_ref}',
    })


@api_bp.route('/alerts/<int:alert_id>/cancel', methods=['POST'])
@login_required
def cancel_alert(alert_id):
    alert = LiveAlert.query.get_or_404(alert_id)
    if alert.user_id != session['user_id']:
        return error('Unauthorized.', 403)
    if alert.status != 'pending':
        return error(f'Cannot cancel alert with status: {alert.status}', 400)
    alert.status = 'cancelled'
    db.session.commit()
    return success({'booking_ref': alert.booking_ref, 'status': 'cancelled'})


@api_bp.route('/user/alerts')
@login_required
def user_alerts():
    alerts = LiveAlert.query.filter_by(user_id=session['user_id'])\
        .order_by(LiveAlert.created_at.desc()).all()
    return success({'alerts': [a.to_dict() for a in alerts]})


# ─── Admin APIs ──────────────────────────────────────────────────────────────

@api_bp.route('/admin/beds/update', methods=['PUT'])
@admin_required
def update_beds():
    data = request.get_json()
    hospital_id = session.get('hospital_id')

    if str(data.get('hospital_id')) != str(hospital_id):
        return error('Unauthorized.', 403)

    bed_type = data.get('bed_type')
    available = data.get('available_beds')
    total = data.get('total_beds')

    if bed_type not in BED_TYPES:
        return error(f'Invalid bed type: {bed_type}', 400)
    if available is None or total is None:
        return error('available_beds and total_beds are required.', 400)

    available, total = int(available), int(total)
    if available < 0 or total < 0:
        return error('Bed counts cannot be negative.', 400)
    if available > total:
        return error('Available beds cannot exceed total beds.', 400)

    bi = BedInventory.query.filter_by(hospital_id=hospital_id, bed_type=bed_type).first()
    if not bi:
        bi = BedInventory(hospital_id=hospital_id, bed_type=bed_type)
        db.session.add(bi)

    bi.available_beds = available
    bi.total_beds = total
    bi.last_updated = utcnow()
    bi.updated_by = session['user_id']
    db.session.commit()

    update_data = bi.to_dict()
    update_data['hospital_id'] = hospital_id
    try:
        emit_bed_updated(hospital_id, update_data)
    except Exception as e:
        logger.warning(f'WebSocket emit failed: {e}')

    return success(update_data)


@api_bp.route('/admin/alerts/<int:alert_id>/status', methods=['PUT'])
@admin_required
def update_alert_status(alert_id):
    alert = LiveAlert.query.get_or_404(alert_id)
    if alert.hospital_id != session.get('hospital_id'):
        return error('Unauthorized.', 403)

    data = request.get_json()
    new_status = data.get('status')
    allowed = ['acknowledged', 'admitted', 'cancelled']
    if new_status not in allowed:
        return error(f'Status must be one of: {", ".join(allowed)}', 400)

    alert.status = new_status
    if new_status == 'acknowledged':
        alert.acknowledged_at = utcnow()
        alert.acknowledged_by = session['user_id']

    db.session.commit()

    # Notify patient via WebSocket
    try:
        hospital = Hospital.query.get(alert.hospital_id)
        emit_alert_acknowledged(alert.user_id, {
            'booking_ref': alert.booking_ref,
            'status': new_status,
            'hospital_name': hospital.name if hospital else 'Hospital',
        })
    except Exception as e:
        logger.warning(f'WebSocket emit failed: {e}')

    return success(alert.to_dict())


@api_bp.route('/admin/alerts')
@admin_required
def admin_alerts():
    hospital_id = session.get('hospital_id')
    status = request.args.get('status', 'all')
    query = LiveAlert.query.filter_by(hospital_id=hospital_id)
    if status != 'all':
        query = query.filter_by(status=status)
    alerts = query.order_by(LiveAlert.created_at.desc()).all()
    return success({'alerts': [a.to_dict() for a in alerts]})
