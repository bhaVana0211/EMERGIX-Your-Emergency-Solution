import os
import pathlib

# ── Guarantee instance/ folder exists before anything else runs ───────────────
_HERE = pathlib.Path(__file__).parent.resolve()
(_HERE / 'instance').mkdir(parents=True, exist_ok=True)

from app import create_app
from app.extensions import socketio

app = create_app(os.environ.get('FLASK_ENV', 'development'))

if __name__ == '__main__':
    print(f"\n  EMERGIX starting...")
    print(f"  DB : {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"  URL: http://localhost:5000\n")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000,
                 allow_unsafe_werkzeug=True)
