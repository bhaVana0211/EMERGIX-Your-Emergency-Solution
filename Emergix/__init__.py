"""
EMERGIX — Flask Application Factory
Creates and configures the Flask application with all extensions and blueprints.
"""

import os
import logging
from flask import Flask
from flask_socketio import SocketIO
from dotenv import load_dotenv

from Emergix.models import db

load_dotenv()

socketio = SocketIO()


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'emergix-dev-secret-key')
    
    # Database — PostgreSQL with SQLite fallback
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///hospital.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
    }

    # Session security
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    if os.environ.get('FLASK_ENV') == 'production':
        app.config['SESSION_COOKIE_SECURE'] = True

    # Apply any override config
    if config:
        app.config.update(config)

    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('emergix')
    logger.setLevel(logging.INFO)

    # Initialize extensions
    db.init_app(app)

    # Initialize SocketIO
    message_queue = os.environ.get('SOCKETIO_MESSAGE_QUEUE') or None
    socketio.init_app(app,
                      async_mode='eventlet' if message_queue else 'threading',
                      message_queue=message_queue,
                      cors_allowed_origins="*")
                      
    # Initialize OAuth
    from Emergix.oauth import oauth
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
    oauth.init_app(app)
    if app.config['GOOGLE_CLIENT_ID'] and app.config['GOOGLE_CLIENT_SECRET']:
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )

    # Register blueprints
    from Emergix.blueprints.main import main_bp
    from Emergix.blueprints.auth import auth_bp
    from Emergix.blueprints.hospitals import hospitals_bp
    from Emergix.blueprints.admin import admin_bp
    from Emergix.blueprints.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(hospitals_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Register socket handlers
    from Emergix import sockets  # noqa: F401

    # Register legacy route redirects for backward compatibility
    _register_legacy_routes(app)

    # Register error handlers
    _register_error_handlers(app)

    # Register template context processors
    @app.context_processor
    def inject_globals():
        from Emergix.utils.alerts import BED_TYPES, BED_TYPE_LABELS, BED_TYPE_ICONS
        return {
            'BED_TYPES': BED_TYPES,
            'BED_TYPE_LABELS': BED_TYPE_LABELS,
            'BED_TYPE_ICONS': BED_TYPE_ICONS,
        }

    # Create database tables
    with app.app_context():
        db.create_all()

    return app


def _register_legacy_routes(app):
    """Register redirects for all existing route paths to maintain backward compatibility."""
    from flask import redirect, url_for, session

    @app.route('/login', methods=['GET', 'POST'])
    def legacy_login():
        return redirect(url_for('auth.login'))

    @app.route('/register', methods=['GET', 'POST'])
    def legacy_register():
        return redirect(url_for('auth.register'))

    @app.route('/logout')
    def legacy_logout():
        return redirect(url_for('auth.logout'))

    @app.route('/beds')
    def legacy_beds():
        return redirect(url_for('hospitals.discovery'))

    @app.route('/hospital_details/<int:hospital_id>')
    def legacy_hospital_details(hospital_id):
        return redirect(url_for('hospitals.detail', hospital_id=hospital_id))

    @app.route('/hospital_management')
    def legacy_hospital_management():
        if session.get('role') == 'hospital_admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('hospitals.discovery'))

    @app.route('/add_hospital', methods=['GET', 'POST'])
    def legacy_add_hospital():
        return redirect(url_for('admin.dashboard'))

    @app.route('/add_beds/<int:hospital_id>', methods=['GET', 'POST'])
    def legacy_add_beds(hospital_id):
        return redirect(url_for('admin.beds'))


def _register_error_handlers(app):
    """Register custom error handlers."""
    from flask import render_template, jsonify, request

    @app.errorhandler(404)
    def not_found(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Not found', 'code': 404}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Internal server error', 'code': 500}), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Forbidden', 'code': 403}), 403
        return render_template('errors/404.html'), 403
