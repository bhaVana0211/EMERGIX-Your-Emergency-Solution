"""
EMERGIX — API Blueprint
All JSON API endpoints for hospitals, alerts, and admin operations.
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime, timezone
from Emergix.models import db, Hospital, BedInventory, LiveAlert, User
from Emergix.utils.decorators import login_required, login_required_admin
from Emergix.utils.geo import haversine_distance, validate_coordinates, find_nearby_hospitals
from Emergix.utils.alerts import generate_booking_ref, BED_TYPES

api_bp = Blueprint('api', __name__)


@api_bp.route('/hospitals/nearby')
@login_required
def hospitals_nearby():
    """GET — Find hospitals near user's location."""
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    radius = request.args.get('radius', 10, type=int)
    bed_type = request.args.get('bed_type', '')
    hospital_type = request.args.get('hospital_type', 'all')
    available_only = request.args.get('available_only', 'true').lower() == 'true'

    if lat is None or lng is None:
        return jsonify({'success': False, 'error': 'lat and lng are required', 'code': 400}), 400

    valid, lat, lng = validate_coordinates(lat, lng)
    if not valid:
        return jsonify({'success': False, 'error': 'Invalid coordinates', 'code': 400}), 400

    radius = min(max(radius, 1), 50)

    # Query all active hospitals
    query = Hospital.query.filter_by(is_active=True)
    if hospital_type and hospital_type != 'all':
        query = query.filter_by(hospital_type=hospital_type)
    
    # Bounding Box Filter for Scalability (Pre-filter before Haversine)
    import math
    lat_deg_dist = radius / 111.0
    lng_deg_dist = radius / (111.0 * math.cos(math.radians(lat)))
    
    query = query.filter(
        Hospital.latitude.between(lat - lat_deg_dist, lat + lat_deg_dist),
        Hospital.longitude.between(lng - lng_deg_dist, lng + lng_deg_dist)
    )

    hospitals = query.all()

    # Filter by distance using Haversine (SQLite fallback)
    nearby = find_nearby_hospitals(hospitals, lat, lng, radius)

    # Build response
    results = []
    bed_type_filters = [bt.strip() for bt in bed_type.split(',') if bt.strip()] if bed_type else []

    for hospital, distance in nearby:
        inventory = BedInventory.query.filter_by(hospital_id=hospital.id).all()
        
        bed_data = []
        total_available = 0
        total_beds_count = 0
        has_matching_beds = False

        for bi in inventory:
            inv = bi.to_dict()
            bed_data.append(inv)
            total_available += bi.available_beds
            total_beds_count += bi.total_beds
            if bed_type_filters and bi.bed_type in bed_type_filters and bi.available_beds > 0:
                has_matching_beds = True

        # If bed_type filter is set and no matching beds, skip
        if bed_type_filters and not has_matching_beds:
            continue

        # If available_only and no beds available, skip
        if available_only and total_available == 0:
            continue

        last_updated = None
        for bi in inventory:
            if bi.last_updated and (last_updated is None or bi.last_updated > last_updated):
                last_updated = bi.last_updated

        results.append({
            'id': hospital.id,
            'name': hospital.name,
            'address': hospital.address or '',
            'city': hospital.city,
            'distance_km': distance,
            'hospital_type': hospital.hospital_type,
            'phone': hospital.phone,
            'latitude': hospital.latitude,
            'longitude': hospital.longitude,
            'emergency_24h': hospital.emergency_24h,
            'ambulance': hospital.ambulance,
            'bed_inventory': bed_data,
            'last_updated': last_updated.isoformat() if last_updated else None,
            'total_available': total_available,
            'total_beds': total_beds_count
        })

    return jsonify({
        'success': True,
        'data': {
            'count': len(results),
            'user_location': {'lat': lat, 'lng': lng},
            'hospitals': results
        }
    })


@api_bp.route('/hospitals/<int:hospital_id>')
@login_required
def hospital_detail(hospital_id):
    """GET — Full hospital detail with bed inventory."""
    hospital = Hospital.query.get(hospital_id)
    if not hospital:
        return jsonify({'success': False, 'error': 'Hospital not found', 'code': 404}), 404

    data = hospital.to_dict(include_beds=True)
    return jsonify({'success': True, 'data': data})


@api_bp.route('/alerts/create', methods=['POST'])
@login_required
def create_alert():
    """POST — Create a new pre-arrival alert."""
    if session.get('role') == 'hospital_admin':
        return jsonify({'success': False, 'error': 'Only patients can create alerts', 'code': 403}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request body required', 'code': 400}), 400

    # Validate required fields
    required = ['hospital_id', 'patient_name', 'contact_phone']
    for field in required:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'{field} is required', 'code': 400}), 400

    hospital = Hospital.query.get(data['hospital_id'])
    if not hospital:
        return jsonify({'success': False, 'error': 'Hospital not found', 'code': 404}), 404

    # Calculate distance
    distance_km = None
    user_lat = data.get('user_lat')
    user_lng = data.get('user_lng')
    if user_lat and user_lng and hospital.latitude and hospital.longitude:
        distance_km = haversine_distance(user_lat, user_lng, hospital.latitude, hospital.longitude)

    # Generate booking reference
    booking_ref = generate_booking_ref()

    try:
        alert = LiveAlert(
            hospital_id=data['hospital_id'],
            user_id=session['user_id'],
            patient_name=data['patient_name'],
            patient_age=data.get('patient_age'),
            patient_gender=data.get('patient_gender'),
            bed_type_needed=data.get('bed_type_needed'),
            contact_phone=data['contact_phone'],
            notes=data.get('notes', '')[:200],
            user_lat=user_lat,
            user_lng=user_lng,
            distance_km=distance_km,
            est_arrival_min=data.get('est_arrival_min'),
            booking_ref=booking_ref
        )
        db.session.add(alert)
        db.session.commit()

        # Emit WebSocket event to hospital admin
        from Emergix import socketio
        socketio.emit('new_alert', alert.to_dict(), room=f'hospital_{data["hospital_id"]}')

        return jsonify({
            'success': True,
            'data': {
                'booking_ref': booking_ref,
                'hospital_name': hospital.name,
                'bed_type': data.get('bed_type_needed', 'general').upper(),
                'status': 'pending',
                'message': f'Your alert has been sent to {hospital.name}. Keep this reference: {booking_ref}'
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to create alert. Please try again.', 'code': 500}), 500


@api_bp.route('/alerts/<int:alert_id>/cancel', methods=['POST'])
@login_required
def cancel_alert(alert_id):
    """POST — Cancel own alert (patient only)."""
    alert = LiveAlert.query.get(alert_id)
    if not alert:
        return jsonify({'success': False, 'error': 'Alert not found', 'code': 404}), 404

    if alert.user_id != session.get('user_id'):
        return jsonify({'success': False, 'error': 'Unauthorized', 'code': 403}), 403

    if alert.status != 'pending':
        return jsonify({'success': False, 'error': 'Only pending alerts can be cancelled', 'code': 400}), 400

    try:
        alert.status = 'cancelled'
        db.session.commit()
        return jsonify({'success': True, 'data': {'status': 'cancelled', 'booking_ref': alert.booking_ref}})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to cancel alert', 'code': 500}), 500


@api_bp.route('/admin/beds/update', methods=['PUT'])
@login_required_admin
def update_beds():
    """PUT — Update bed counts (admin only). Enforces hospital isolation."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request body required', 'code': 400}), 400

    hospital_id = session.get('hospital_id')
    bed_type = data.get('bed_type')
    available_beds = data.get('available_beds')
    total_beds = data.get('total_beds')

    if bed_type not in BED_TYPES:
        return jsonify({'success': False, 'error': 'Invalid bed type', 'code': 400}), 400

    # Admin isolation: only update own hospital
    inventory = BedInventory.query.filter_by(
        hospital_id=hospital_id,
        bed_type=bed_type
    ).with_for_update().first()

    if not inventory:
        return jsonify({'success': False, 'error': 'Bed inventory not found', 'code': 404}), 404

    # Validation
    if total_beds is not None:
        total_beds = int(total_beds)
        if total_beds < 0:
            return jsonify({'success': False, 'error': 'Total beds cannot be negative', 'code': 400}), 400
        inventory.total_beds = total_beds

    if available_beds is not None:
        available_beds = int(available_beds)
        if available_beds < 0:
            return jsonify({'success': False, 'error': 'Available beds cannot be negative', 'code': 400}), 400
        if available_beds > inventory.total_beds:
            return jsonify({'success': False, 'error': 'Available beds cannot exceed total beds', 'code': 400}), 400
        inventory.available_beds = available_beds

    try:
        inventory.last_updated = datetime.now(timezone.utc)
        inventory.updated_by = session.get('user_id')
        db.session.commit()

        # Emit WebSocket event to all connected clients
        from Emergix import socketio
        socketio.emit('bed_updated', {
            'hospital_id': hospital_id,
            'bed_type': bed_type,
            'available_beds': inventory.available_beds,
            'total_beds': inventory.total_beds,
            'occupancy_pct': inventory.occupancy_pct,
            'updated_at': inventory.last_updated.isoformat()
        })

        return jsonify({
            'success': True,
            'data': inventory.to_dict()
        })
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to update bed count', 'code': 500}), 500


@api_bp.route('/admin/alerts/<int:alert_id>/status', methods=['PUT'])
@login_required_admin
def update_alert_status(alert_id):
    """PUT — Update alert status (admin only). Verifies alert belongs to admin's hospital."""
    hospital_id = session.get('hospital_id')
    alert = LiveAlert.query.filter_by(id=alert_id, hospital_id=hospital_id).first()

    if not alert:
        return jsonify({'success': False, 'error': 'Alert not found', 'code': 404}), 404

    data = request.get_json()
    new_status = data.get('status')

    if new_status not in ['acknowledged', 'admitted', 'cancelled']:
        return jsonify({'success': False, 'error': 'Invalid status', 'code': 400}), 400

    try:
        alert.status = new_status
        if new_status == 'acknowledged':
            alert.acknowledged_at = datetime.now(timezone.utc)
            alert.acknowledged_by = session.get('user_id')
        db.session.commit()

        # Emit WebSocket event to patient
        from Emergix import socketio
        hospital = Hospital.query.get(hospital_id)
        socketio.emit('alert_acknowledged', {
            'booking_ref': alert.booking_ref,
            'status': new_status,
            'hospital_name': hospital.name if hospital else ''
        }, room=f'user_{alert.user_id}')

        return jsonify({
            'success': True,
            'data': alert.to_dict()
        })
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to update alert status', 'code': 500}), 500


@api_bp.route('/admin/profile/update', methods=['PUT'])
@login_required_admin
def update_profile():
    """PUT — Update hospital profile (admin only)."""
    hospital_id = session.get('hospital_id')
    hospital = Hospital.query.get(hospital_id)

    if not hospital:
        return jsonify({'success': False, 'error': 'Hospital not found', 'code': 404}), 404

    data = request.get_json()

    # Only allow updating specific fields
    editable_fields = ['phone', 'email', 'website', 'address', 'emergency_24h', 'ambulance']
    for field in editable_fields:
        if field in data:
            setattr(hospital, field, data[field])

    try:
        hospital.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify({'success': True, 'data': hospital.to_dict()})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to update profile', 'code': 500}), 500
