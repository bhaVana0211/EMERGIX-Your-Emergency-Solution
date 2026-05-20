"""
EMERGIX — Alert Utilities
Booking reference generation and alert helper functions.
"""

from datetime import datetime, timezone
from Emergix.models import db, LiveAlert


def generate_booking_ref():
    """
    Generate a unique booking reference in format: EMX-YYYY-NNNNN
    e.g., EMX-2024-00142
    """
    year = datetime.now(timezone.utc).year
    last_alert = LiveAlert.query.order_by(LiveAlert.id.desc()).first()
    next_id = (last_alert.id + 1) if last_alert else 1
    return f"EMX-{year}-{next_id:05d}"


BED_TYPES = [
    'general', 'icu', 'oxygen', 'ventilator',
    'opd', 'emergency', 'pediatric', 'maternity'
]

BED_TYPE_LABELS = {
    'general': 'General',
    'icu': 'ICU',
    'oxygen': 'Oxygen',
    'ventilator': 'Ventilator',
    'opd': 'OPD',
    'emergency': 'Emergency',
    'pediatric': 'Pediatric',
    'maternity': 'Maternity'
}

BED_TYPE_ICONS = {
    'general': 'fa-bed',
    'icu': 'fa-heart-pulse',
    'oxygen': 'fa-lungs',
    'ventilator': 'fa-fan',
    'opd': 'fa-stethoscope',
    'emergency': 'fa-truck-medical',
    'pediatric': 'fa-baby',
    'maternity': 'fa-person-pregnant'
}

ALERT_STATUSES = ['pending', 'acknowledged', 'admitted', 'cancelled']

GENDER_OPTIONS = ['male', 'female', 'other']

ARRIVAL_OPTIONS = [
    (15, '15 minutes'),
    (30, '30 minutes'),
    (45, '45 minutes'),
    (60, '1 hour'),
    (90, 'More than 1 hour')
]
