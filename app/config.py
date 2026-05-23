import os
import pathlib
from dotenv import load_dotenv

load_dotenv()

# ── Compute absolute paths with pathlib (reliable on Windows) ─────────────────
_APP_DIR      = pathlib.Path(__file__).parent.resolve()   # .../EMERGIX/app/
_PROJECT_DIR  = _APP_DIR.parent.resolve()                 # .../EMERGIX/
_INSTANCE_DIR = _PROJECT_DIR / 'instance'
_INSTANCE_DIR.mkdir(parents=True, exist_ok=True)          # create folder NOW
_DB_FILE      = _INSTANCE_DIR / 'emergix.db'
_SQLITE_URI   = 'sqlite:///' + str(_DB_FILE).replace('\\', '/')

# ── Resolve DATABASE_URL from .env ────────────────────────────────────────────
# If .env sets a PostgreSQL/MySQL URL → use it.
# If .env sets a relative sqlite path (e.g. sqlite:///instance/emergix.db)
#   → IGNORE it and use our computed absolute path instead.
#   Relative sqlite URIs break on Windows because SQLite can't mkdir.
_env_db = os.environ.get('DATABASE_URL', '')
if _env_db.lower().startswith(('postgresql', 'postgres', 'mysql')):
    _RESOLVED_DB = _env_db          # production DB → use as-is
else:
    _RESOLVED_DB = _SQLITE_URI      # dev → always use absolute path we computed


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'emergix-dev-secret-change-in-production-2024')
    SQLALCHEMY_DATABASE_URI        = _RESOLVED_DB
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS      = {
        'pool_pre_ping': True,
        'pool_recycle':  300,
        'pool_timeout':  20,
    }
    WTF_CSRF_ENABLED         = True
    WTF_CSRF_TIME_LIMIT      = 3600
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = 'Lax'
    RATELIMIT_DEFAULT        = "200 per day;50 per hour"
    SOCKETIO_ASYNC_MODE      = 'threading'
    DEFAULT_SEARCH_RADIUS_KM = 10
    MAX_SEARCH_RADIUS_KM     = 50
    GOOGLE_CLIENT_ID         = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
    GOOGLE_CLIENT_SECRET     = os.environ.get('GOOGLE_CLIENT_SECRET', '').strip()


class DevelopmentConfig(Config):
    DEBUG                 = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG                 = False
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
