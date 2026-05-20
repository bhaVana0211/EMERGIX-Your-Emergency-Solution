"""
EMERGIX — Main Blueprint
Landing page and health check endpoint.
"""

from flask import Blueprint, render_template, jsonify
from datetime import datetime, timezone
from Emergix.models import db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def landing():
    """Landing page — public, no auth required."""
    return render_template('main/landing.html')


@main_bp.route('/health')
def health():
    """Health check endpoint for load balancer / monitoring."""
    try:
        db.session.execute(db.text('SELECT 1'))
        db_status = 'connected'
    except Exception:
        db_status = 'disconnected'
    
    return jsonify({
        'status': 'ok',
        'db': db_status,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
