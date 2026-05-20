"""
EMERGIX — Admin Blueprint
Hospital admin dashboard, bed management, alerts, and profile.
"""

from flask import Blueprint, render_template, session
from Emergix.models import db, Hospital, BedInventory, LiveAlert
from Emergix.utils.decorators import login_required_admin
from datetime import datetime, timezone, timedelta

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required_admin
def dashboard():
    """Admin overview dashboard with summary cards and recent activity."""
    hospital_id = session.get('hospital_id')
    hospital = Hospital.query.get(hospital_id)
    inventory = BedInventory.query.filter_by(hospital_id=hospital_id).all()

    # Calculate summary stats
    total_beds = sum(bi.total_beds for bi in inventory)
    available_beds = sum(bi.available_beds for bi in inventory)

    # Today's alerts
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_alerts = LiveAlert.query.filter(
        LiveAlert.hospital_id == hospital_id,
        LiveAlert.created_at >= today_start
    ).count()

    pending_alerts = LiveAlert.query.filter_by(
        hospital_id=hospital_id,
        status='pending'
    ).count()

    # Recent alerts (last 5)
    recent_alerts = LiveAlert.query.filter_by(hospital_id=hospital_id).order_by(
        LiveAlert.created_at.desc()
    ).limit(5).all()

    return render_template('admin/dashboard.html',
                           hospital=hospital,
                           inventory=inventory,
                           total_beds=total_beds,
                           available_beds=available_beds,
                           today_alerts=today_alerts,
                           pending_alerts=pending_alerts,
                           recent_alerts=recent_alerts)


@admin_bp.route('/beds')
@login_required_admin
def beds():
    """Bed management page with increment/decrement controls."""
    hospital_id = session.get('hospital_id')
    hospital = Hospital.query.get(hospital_id)
    inventory = BedInventory.query.filter_by(hospital_id=hospital_id).all()
    return render_template('admin/beds.html',
                           hospital=hospital,
                           inventory=inventory)


@admin_bp.route('/alerts')
@login_required_admin
def alerts():
    """Real-time incoming alerts panel."""
    hospital_id = session.get('hospital_id')
    hospital = Hospital.query.get(hospital_id)
    all_alerts = LiveAlert.query.filter_by(hospital_id=hospital_id).order_by(
        LiveAlert.created_at.desc()
    ).all()
    return render_template('admin/alerts.html',
                           hospital=hospital,
                           alerts=all_alerts)


@admin_bp.route('/profile')
@login_required_admin
def profile():
    """Hospital profile management."""
    hospital_id = session.get('hospital_id')
    hospital = Hospital.query.get(hospital_id)
    return render_template('admin/profile.html', hospital=hospital)
