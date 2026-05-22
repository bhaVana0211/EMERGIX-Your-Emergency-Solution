from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
socketio = SocketIO()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
oauth = OAuth()
