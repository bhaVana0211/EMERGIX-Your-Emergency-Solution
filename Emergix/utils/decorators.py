"""
EMERGIX — Route Decorators
Authentication and authorization decorators for route protection.
"""

from functools import wraps
from flask import session, redirect, url_for, flash, jsonify, request


def login_required(f):
    """Require any authenticated user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required', 'code': 401}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def login_required_patient(f):
    """Require authenticated patient user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required', 'code': 401}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') == 'hospital_admin':
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Patient access only', 'code': 403}), 403
            flash('This page is for patients only.', 'warning')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def login_required_admin(f):
    """Require authenticated hospital admin user."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required', 'code': 401}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.hospital_login'))
        if session.get('role') != 'hospital_admin':
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Admin access only', 'code': 403}), 403
            flash('This page is for hospital administrators only.', 'warning')
            return redirect(url_for('auth.hospital_login'))
        if not session.get('hospital_id'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'No hospital assigned', 'code': 403}), 403
            flash('Your account is not assigned to a hospital.', 'danger')
            return redirect(url_for('auth.hospital_login'))
        return f(*args, **kwargs)
    return decorated_function
