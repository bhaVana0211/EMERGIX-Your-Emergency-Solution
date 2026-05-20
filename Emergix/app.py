"""
EMERGIX — Entry Point
Run this script to start the Flask development server with Socket.IO.
"""

import os
import sys

# Add project root to path if running directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Emergix import create_app, socketio

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # Start the bed simulator daemon if in development mode
    if os.environ.get('FLASK_ENV', 'development') == 'development':
        import threading
        from mock_bed_simulator import run_simulator
        simulator_thread = threading.Thread(target=run_simulator, args=(app, socketio), daemon=True)
        simulator_thread.start()

    # Run the application with Socket.IO (Eventlet recommended)
    print("Starting EMERGIX Server...")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)