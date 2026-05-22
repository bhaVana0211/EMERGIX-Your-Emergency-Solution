import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR     = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'instance'))

# Create the instance folder now — SQLite cannot create missing directories itself
os.makedirs(INSTANCE_DIR, exist_ok=True)

_DEFAULT_DB = 'sqlite:///' + os.path.join(INSTANCE_DIR, 'emergix.db').replace('\\', '/')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'emergix-dev-secret-change-in-production-2024')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', _DEFAULT_DB)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Connection pool: handles burst traffic without connection exhaustion
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping':    True,    # detect stale connections before use
        'pool_recycle':     300,     # recycle connections every 5 min
        'pool_timeout':     20,      # wait up to 20s for a free connection
        'connect_args':     {'timeout': 15} if 'sqlite' in os.environ.get('DATABASE_URL','sqlite') else {},
    }
    WTF_CSRF_ENABLED        = True
    WTF_CSRF_TIME_LIMIT     = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    RATELIMIT_DEFAULT       = "200 per day;50 per hour"
    SOCKETIO_ASYNC_MODE     = 'threading'
    DEFAULT_SEARCH_RADIUS_KM = 10
    MAX_SEARCH_RADIUS_KM     = 50
    # Google OAuth
    GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    # Larger pool for production concurrent load (100+ concurrent users)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping':  True,
        'pool_recycle':   300,
        'pool_size':      20,        # base pool connections
        'max_overflow':   40,        # extra connections during spikes
        'pool_timeout':   30,
    }

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
