from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
import random
import string


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(15), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=True)   # nullable for Google-only accounts
    google_id = db.Column(db.String(128), unique=True, nullable=True)
    avatar_url = db.Column(db.String(300), nullable=True)      # Google profile picture
    auth_provider = db.Column(db.String(20), default='local')  # 'local' or 'google'
    role = db.Column(db.String(20), default='patient')
    is_management = db.Column(db.Boolean, default=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    # Relationships
    alerts = db.relationship('LiveAlert', foreign_keys='LiveAlert.user_id', backref='patient', lazy='dynamic')
    managed_hospital = db.relationship('Hospital', foreign_keys=[hospital_id], backref='admin_users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False   # Google-only account — no password set
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'hospital_admin' or self.is_management

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
        }

    def __repr__(self):
        return f'<User {self.username}>'


class Hospital(db.Model):
    __tablename__ = 'hospitals'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(100), nullable=False, default='Bhubaneswar')
    state = db.Column(db.String(100), nullable=False, default='Odisha')
    pincode = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    hospital_type = db.Column(db.String(20), default='government')  # government, private, trust
    established = db.Column(db.Integer, nullable=True)
    emergency_24h = db.Column(db.Boolean, default=True)
    ambulance = db.Column(db.Boolean, default=False)
    image_url = db.Column(db.String(300), nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    bed_inventory = db.relationship('BedInventory', backref='hospital', lazy='dynamic',
                                     cascade='all, delete-orphan')
    alerts = db.relationship('LiveAlert', backref='hospital', lazy='dynamic')
    beds = db.relationship('Bed', backref='hospital', lazy='dynamic')

    def total_available(self):
        return sum(b.available_beds for b in self.bed_inventory)

    def total_beds(self):
        return sum(b.total_beds for b in self.bed_inventory)

    def to_dict(self, distance_km=None):
        inventory = {b.bed_type: {'available': b.available_beds, 'total': b.total_beds,
                                   'occupancy_pct': b.occupancy_pct(), 'last_updated': b.last_updated.isoformat() if b.last_updated else None}
                     for b in self.bed_inventory}
        result = {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'city': self.city,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'hospital_type': self.hospital_type,
            'emergency_24h': self.emergency_24h,
            'ambulance': self.ambulance,
            'bed_inventory': inventory,
            'total_available': self.total_available(),
            'total_beds': self.total_beds(),
        }
        if distance_km is not None:
            result['distance_km'] = round(distance_km, 1)
        return result

    def __repr__(self):
        return f'<Hospital {self.name}>'


BED_TYPES = ['general', 'icu', 'oxygen', 'ventilator', 'opd', 'emergency', 'pediatric', 'maternity']

BED_TYPE_LABELS = {
    'general': 'General',
    'icu': 'ICU',
    'oxygen': 'Oxygen',
    'ventilator': 'Ventilator',
    'opd': 'OPD',
    'emergency': 'Emergency',
    'pediatric': 'Pediatric',
    'maternity': 'Maternity',
}

BED_TYPE_ICONS = {
    'general': 'fa-bed',
    'icu': 'fa-heart-pulse',
    'oxygen': 'fa-lungs',
    'ventilator': 'fa-wind',
    'opd': 'fa-stethoscope',
    'emergency': 'fa-truck-medical',
    'pediatric': 'fa-child',
    'maternity': 'fa-baby',
}


class BedInventory(db.Model):
    __tablename__ = 'bed_inventory'

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    bed_type = db.Column(db.String(20), nullable=False)
    total_beds = db.Column(db.Integer, nullable=False, default=0)
    available_beds = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('hospital_id', 'bed_type', name='uq_hospital_bedtype'),
    )

    def occupancy_pct(self):
        if self.total_beds == 0:
            return 0
        return round(((self.total_beds - self.available_beds) / self.total_beds) * 100)

    def to_dict(self):
        return {
            'id': self.id,
            'hospital_id': self.hospital_id,
            'bed_type': self.bed_type,
            'bed_type_label': BED_TYPE_LABELS.get(self.bed_type, self.bed_type.title()),
            'bed_type_icon': BED_TYPE_ICONS.get(self.bed_type, 'fa-bed'),
            'total_beds': self.total_beds,
            'available_beds': self.available_beds,
            'occupied_beds': self.total_beds - self.available_beds,
            'occupancy_pct': self.occupancy_pct(),
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
        }

    def __repr__(self):
        return f'<BedInventory {self.hospital_id}:{self.bed_type} {self.available_beds}/{self.total_beds}>'


class Bed(db.Model):
    """Legacy individual bed model - kept for backward compatibility."""
    __tablename__ = 'beds'

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    bed_type = db.Column(db.String(50), nullable=False)
    available = db.Column(db.Boolean, default=True)
    booked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    booking_time = db.Column(db.DateTime, nullable=True)
    booking_ref = db.Column(db.String(20), unique=True, nullable=True)


def _generate_booking_ref():
    year = datetime.now().year
    suffix = ''.join(random.choices(string.digits, k=5))
    return f"EMX-{year}-{suffix}"


class LiveAlert(db.Model):
    __tablename__ = 'live_alerts'

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    patient_name = db.Column(db.String(200), nullable=False)
    patient_age = db.Column(db.Integer, nullable=True)
    patient_gender = db.Column(db.String(10), nullable=True)
    bed_type_needed = db.Column(db.String(20), nullable=False)
    contact_phone = db.Column(db.String(15), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, acknowledged, admitted, cancelled
    user_lat = db.Column(db.Float, nullable=True)
    user_lng = db.Column(db.Float, nullable=True)
    distance_km = db.Column(db.Float, nullable=True)
    est_arrival_min = db.Column(db.Integer, nullable=True)
    booking_ref = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    acknowledger = db.relationship('User', foreign_keys=[acknowledged_by])

    def __init__(self, **kwargs):
        if 'booking_ref' not in kwargs:
            kwargs['booking_ref'] = _generate_booking_ref()
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'hospital_id': self.hospital_id,
            'hospital_name': self.hospital.name if self.hospital else None,
            'user_id': self.user_id,
            'patient_name': self.patient_name,
            'patient_age': self.patient_age,
            'patient_gender': self.patient_gender,
            'bed_type_needed': self.bed_type_needed,
            'bed_type_label': BED_TYPE_LABELS.get(self.bed_type_needed, self.bed_type_needed.title()),
            'contact_phone': self.contact_phone,
            'notes': self.notes,
            'status': self.status,
            'distance_km': self.distance_km,
            'est_arrival_min': self.est_arrival_min,
            'booking_ref': self.booking_ref,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }

    def __repr__(self):
        return f'<LiveAlert {self.booking_ref} {self.status}>'
