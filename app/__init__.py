import os
import logging
from flask import Flask, render_template
from app.config import config
from app.extensions import db, socketio, csrf, limiter, oauth

logging.basicConfig(level=logging.INFO)


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')
    app.config.from_object(config.get(config_name, config['default']))

    # Ensure instance folder exists
    os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)

    # Init extensions
    db.init_app(app)
    socketio.init_app(app,
                      async_mode='threading',
                      cors_allowed_origins='*',
                      logger=False,
                      engineio_logger=False)
    csrf.init_app(app)
    limiter.init_app(app)
    oauth.init_app(app)

    # Register Google OAuth provider
    oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )

    # Register blueprints
    from app.blueprints.main import main_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.hospitals import hospitals_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.api import api_bp
    from app.blueprints.user import user_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(hospitals_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(user_bp)

    # Exempt API from CSRF (uses session auth, not form tokens)
    csrf.exempt(api_bp)

    # Import socket handlers
    from app import sockets  # noqa: F401

    # Create tables
    with app.app_context():
        db.create_all()

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(429)
    def rate_limited(e):
        from flask import request, jsonify
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Too many requests. Please slow down.'}), 429
        return render_template('errors/429.html'), 429

    @app.errorhandler(500)
    def server_error(e):
        from app.extensions import db as _db
        _db.session.rollback()     # always rollback on 500 to free the connection
        return render_template('errors/500.html'), 500

    # Ensure DB sessions are cleaned up after every request (prevents connection leaks under load)
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        from app.extensions import db as _db
        if exception:
            _db.session.rollback()
        _db.session.remove()

    # Template context processors
    @app.context_processor
    def inject_globals():
        from flask import session
        return {
            'session': session,
            'app_name': 'EMERGIX',
        }

    return app
