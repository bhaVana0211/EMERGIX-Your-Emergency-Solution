from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def patient_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') == 'hospital_admin':
            flash('This area is for patients only.', 'warning')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            flash('Please log in as hospital staff.', 'warning')
            return redirect(url_for('auth.hospital_login'))
        if session.get('role') != 'hospital_admin':
            flash('Hospital staff access required.', 'danger')
            return redirect(url_for('hospitals.discovery'))
        return f(*args, **kwargs)
    return decorated
