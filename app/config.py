import os
import pathlib
from dotenv import load_dotenv

load_dotenv()

# ── Paths (pathlib gives reliable cross-platform behaviour on Windows) ────────
_APP_DIR      = pathlib.Path(__file__).parent.resolve()   # .../EMERGIX/app/
_PROJECT_DIR  = _APP_DIR.parent.resolve()                 # .../EMERGIX/
_INSTANCE_DIR = _PROJECT_DIR / 'instance'
_INSTANCE_DIR.mkdir(parents=True, exist_ok=True)          # create NOW, before SQLAlchemy
_DB_FILE      = _INSTANCE_DIR / 'emergix.db'
_DEFAULT_DB   = 'sqlite:///' + str(_DB_FILE).replace('\\', '/')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'emergix-dev-secret-change-in-production-2024')
    SQLALCHEMY_DATABASE_URI     = os.environ.get('DATABASE_URL', _DEFAULT_DB)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS   = {
        'pool_pre_ping': True,
        'pool_recycle':  300,
        'pool_timeout':  20,
    }
    WTF_CSRF_ENABLED        = True
    WTF_CSRF_TIME_LIMIT     = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    RATELIMIT_DEFAULT       = "200 per day;50 per hour"
    SOCKETIO_ASYNC_MODE     = 'threading'
    DEFAULT_SEARCH_RADIUS_KM = 10
    MAX_SEARCH_RADIUS_KM     = 50
    GOOGLE_CLIENT_ID         = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET     = os.environ.get('GOOGLE_CLIENT_SECRET', '')


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle':  300,
        'pool_size':     20,
        'max_overflow':  40,
        'pool_timeout':  30,
    }


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}
