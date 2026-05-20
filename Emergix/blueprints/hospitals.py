"""
EMERGIX — Hospitals Blueprint
Patient-facing hospital discovery and detail pages.
"""

from flask import Blueprint, render_template, session, redirect, url_for, flash
from Emergix.models import db, Hospital, BedInventory
from Emergix.utils.decorators import login_required

hospitals_bp = Blueprint('hospitals', __name__)


@hospitals_bp.route('/hospitals')
@login_required
def discovery():
    """Hospital discovery page — geolocation-based nearby search."""
    return render_template('hospitals/discovery.html')


@hospitals_bp.route('/hospitals/<int:hospital_id>')
@login_required
def detail(hospital_id):
    """Hospital detail page with full bed inventory."""
    hospital = Hospital.query.get_or_404(hospital_id)
    inventory = BedInventory.query.filter_by(hospital_id=hospital_id).all()
    return render_template('hospitals/detail.html',
                           hospital=hospital,
                           inventory=inventory)


@hospitals_bp.route('/user/dashboard')
@login_required
def user_dashboard():
    """Patient dashboard — view sent alerts."""
    from Emergix.models import LiveAlert
    user_id = session.get('user_id')
    alerts = LiveAlert.query.filter_by(user_id=user_id).order_by(LiveAlert.created_at.desc()).all()
    return render_template('user/dashboard.html', alerts=alerts)
