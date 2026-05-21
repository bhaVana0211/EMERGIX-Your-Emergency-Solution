from flask_socketio import join_room, leave_room, emit
from flask import session
from app.extensions import socketio
import logging

logger = logging.getLogger(__name__)


@socketio.on('connect')
def handle_connect():
    user_id = session.get('user_id')
    role = session.get('role')
    if user_id:
        join_room(f'user_{user_id}')
        if role == 'hospital_admin':
            hospital_id = session.get('hospital_id')
            if hospital_id:
                join_room(f'hospital_{hospital_id}')
                logger.info(f'Admin user {user_id} joined hospital room {hospital_id}')
        logger.info(f'User {user_id} connected ({role})')


@socketio.on('disconnect')
def handle_disconnect():
    user_id = session.get('user_id')
    logger.info(f'User {user_id} disconnected')


@socketio.on('join_hospital')
def handle_join_hospital(data):
    """Allow admin to explicitly join their hospital room."""
    hospital_id = session.get('hospital_id')
    if hospital_id and session.get('role') == 'hospital_admin':
        join_room(f'hospital_{hospital_id}')
        emit('joined', {'room': f'hospital_{hospital_id}'})


def emit_new_alert(hospital_id: int, alert_data: dict):
    """Emit new alert to hospital's admin room."""
    socketio.emit('new_alert', alert_data, room=f'hospital_{hospital_id}')


def emit_alert_acknowledged(user_id: int, data: dict):
    """Emit acknowledgement to patient user."""
    socketio.emit('alert_acknowledged', data, room=f'user_{user_id}')


def emit_bed_updated(hospital_id: int, bed_data: dict):
    """Broadcast bed update to all connected clients."""
    socketio.emit('bed_updated', bed_data)
