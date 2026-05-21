from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from app.extensions import db
from app.models import (Hospital, BedInventory, LiveAlert, BED_TYPES,
                         BED_TYPE_LABELS, BED_TYPE_ICONS, utcnow)
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    hospital_id = session.get('hospital_id')
    hospital = Hospital.query.get_or_404(hospital_id)
    inventory = list(hospital.bed_inventory.all())

    from datetime import date
    today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_alerts = LiveAlert.query.filter(
        LiveAlert.hospital_id == hospital_id,
        LiveAlert.created_at >= today_start
    ).count()
    pending_alerts = LiveAlert.query.filter_by(
        hospital_id=hospital_id, status='pending'
    ).count()
    recent_alerts = LiveAlert.query.filter_by(hospital_id=hospital_id)\
        .order_by(LiveAlert.created_at.desc()).limit(5).all()

    total_available = sum(b.available_beds for b in inventory)
    total_beds = sum(b.total_beds for b in inventory)

    return render_template('admin/dashboard.html',
                           hospital=hospital,
                           inventory=inventory,
                           bed_type_labels=BED_TYPE_LABELS,
                           bed_type_icons=BED_TYPE_ICONS,
                           today_alerts=today_alerts,
                           pending_alerts=pending_alerts,
                           recent_alerts=recent_alerts,
                           total_available=total_available,
                           total_beds=total_beds)


@admin_bp.route('/beds')
@admin_required
def beds():
    hospital_id = session.get('hospital_id')
    hospital = Hospital.query.get_or_404(hospital_id)
    inventory = {b.bed_type: b for b in hospital.bed_inventory}
    all_inventory = []
    for bt in BED_TYPES:
        if bt in inventory:
            all_inventory.append(inventory[bt])
        else:
            # Create missing bed type with 0 counts
            new_bi = BedInventory(hospital_id=hospital_id, bed_type=bt,
                                   total_beds=0, available_beds=0)
            db.session.add(new_bi)
            all_inventory.append(new_bi)
    db.session.commit()

    return render_template('admin/beds.html',
                           hospital=hospital,
                           inventory=all_inventory,
                           bed_type_labels=BED_TYPE_LABELS,
                           bed_type_icons=BED_TYPE_ICONS)


@admin_bp.route('/alerts')
@admin_required
def alerts():
    hospital_id = session.get('hospital_id')
    hospital = Hospital.query.get_or_404(hospital_id)
    status_filter = request.args.get('status', 'all')
    query = LiveAlert.query.filter_by(hospital_id=hospital_id)
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    alerts_list = query.order_by(LiveAlert.created_at.desc()).all()
    counts = {
        'all': LiveAlert.query.filter_by(hospital_id=hospital_id).count(),
        'pending': LiveAlert.query.filter_by(hospital_id=hospital_id, status='pending').count(),
        'acknowledged': LiveAlert.query.filter_by(hospital_id=hospital_id, status='acknowledged').count(),
        'admitted': LiveAlert.query.filter_by(hospital_id=hospital_id, status='admitted').count(),
        'cancelled': LiveAlert.query.filter_by(hospital_id=hospital_id, status='cancelled').count(),
    }
    return render_template('admin/alerts.html',
                           hospital=hospital,
                           alerts=alerts_list,
                           status_filter=status_filter,
                           counts=counts,
                           bed_type_labels=BED_TYPE_LABELS,
                           bed_type_icons=BED_TYPE_ICONS)


@admin_bp.route('/profile', methods=['GET', 'POST'])
@admin_required
def profile():
    hospital_id = session.get('hospital_id')
    hospital = Hospital.query.get_or_404(hospital_id)
    if request.method == 'POST':
        hospital.phone = request.form.get('phone', hospital.phone)
        hospital.email = request.form.get('email', hospital.email)
        hospital.website = request.form.get('website', hospital.website)
        hospital.description = request.form.get('description', hospital.description)
        hospital.emergency_24h = bool(request.form.get('emergency_24h'))
        hospital.ambulance = bool(request.form.get('ambulance'))
        db.session.commit()
        flash('Hospital profile updated successfully.', 'success')
        return redirect(url_for('admin.profile'))
    return render_template('admin/profile.html', hospital=hospital)
