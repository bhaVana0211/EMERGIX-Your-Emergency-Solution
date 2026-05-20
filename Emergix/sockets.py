"""
EMERGIX — WebSocket Event Handlers
Flask-SocketIO event handlers for real-time communication.
"""

from flask import session
from flask_socketio import join_room, leave_room, emit
from Emergix import socketio
import logging

logger = logging.getLogger('emergix.sockets')


@socketio.on('connect')
def handle_connect():
    """Handle client connection — join appropriate room based on role."""
    user_id = session.get('user_id')
    role = session.get('role')
    hospital_id = session.get('hospital_id')

    if not user_id:
        return False  # Reject connection

    if role == 'hospital_admin' and hospital_id:
        room = f'hospital_{hospital_id}'
        join_room(room)
        logger.info(f'Admin user {user_id} joined room {room}')
        emit('connected', {'message': 'Connected to hospital alert channel', 'room': room})
    else:
        room = f'user_{user_id}'
        join_room(room)
        logger.info(f'Patient user {user_id} joined room {room}')
        emit('connected', {'message': 'Connected to notification channel', 'room': room})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    user_id = session.get('user_id')
    role = session.get('role')
    hospital_id = session.get('hospital_id')

    if role == 'hospital_admin' and hospital_id:
        room = f'hospital_{hospital_id}'
        leave_room(room)
        logger.info(f'Admin user {user_id} left room {room}')
    elif user_id:
        room = f'user_{user_id}'
        leave_room(room)
        logger.info(f'Patient user {user_id} left room {room}')


@socketio.on('join_hospital')
def handle_join_hospital(data):
    """Admin explicitly joins their hospital room."""
    hospital_id = session.get('hospital_id')
    if hospital_id:
        room = f'hospital_{hospital_id}'
        join_room(room)
        emit('room_joined', {'room': room})


@socketio.on('join_user')
def handle_join_user(data):
    """Patient explicitly joins their user room."""
    user_id = session.get('user_id')
    if user_id:
        room = f'user_{user_id}'
        join_room(room)
        emit('room_joined', {'room': room})
