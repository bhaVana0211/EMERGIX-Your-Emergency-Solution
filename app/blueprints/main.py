from flask import Blueprint, render_template, jsonify
from app.extensions import db
from app.models import Hospital, BedInventory

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def landing():
    total_hospitals = Hospital.query.filter_by(is_active=True).count()
    total_available = db.session.query(db.func.sum(BedInventory.available_beds)).scalar() or 0
    return render_template('main/landing.html',
                           total_hospitals=total_hospitals,
                           total_available=total_available)


@main_bp.route('/health')
def health():
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = 'connected'
    except Exception as e:
        db_status = f'error: {str(e)}'
    from datetime import datetime
    return jsonify({'status': 'ok', 'db': db_status,
                    'timestamp': datetime.utcnow().isoformat()})


# Legacy route redirects for backward compatibility
@main_bp.route('/beds')
def legacy_beds():
    from flask import redirect, url_for, session
    if session.get('role') == 'hospital_admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('hospitals.discovery'))


@main_bp.route('/hospital_management')
def legacy_management():
    from flask import redirect, url_for
    return redirect(url_for('admin.dashboard'))
