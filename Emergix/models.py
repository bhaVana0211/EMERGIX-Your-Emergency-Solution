"""
EMERGIX — Database Models
All SQLAlchemy models for the EMERGIX platform.
Supports both PostgreSQL (with PostGIS) and SQLite (fallback for local dev).
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    """User model — supports both patient and hospital_admin roles."""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='patient')  # 'patient' or 'hospital_admin'
    is_management = db.Column(db.Boolean, default=False)  # backward compatibility
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    hospital = db.relationship('Hospital', backref=db.backref('admins', lazy=True), foreign_keys=[hospital_id])
    beds = db.relationship('Bed', backref='user', lazy=True)
    alerts_sent = db.relationship('LiveAlert', backref='user', lazy=True, foreign_keys='LiveAlert.user_id')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'hospital_id': self.hospital_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Hospital(db.Model):
    """Hospital model — extended with location, contact, and operational details."""
    __tablename__ = 'hospital'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text, nullable=True, default='')
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=True)
    pincode = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True, index=True)
    longitude = db.Column(db.Float, nullable=True, index=True)
    hospital_type = db.Column(db.String(20), default='government')  # government, private, trust
    established = db.Column(db.Integer, nullable=True)
    emergency_24h = db.Column(db.Boolean, default=True)
    ambulance = db.Column(db.Boolean, default=False)
    image_url = db.Column(db.String(300), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    beds = db.relationship('Bed', backref='hospital', lazy=True)
    bed_inventory = db.relationship('BedInventory', backref='hospital', lazy=True)
    alerts = db.relationship('LiveAlert', backref='hospital', lazy=True)

    def to_dict(self, include_beds=False):
        data = {
            'id': self.id,
            'name': self.name,
            'address': self.address or '',
            'city': self.city,
            'state': self.state,
            'pincode': self.pincode,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'hospital_type': self.hospital_type,
            'established': self.established,
            'emergency_24h': self.emergency_24h,
            'ambulance': self.ambulance,
            'image_url': self.image_url,
            'is_active': self.is_active,
        }
        if include_beds:
            inventory = []
            total_available = 0
            total_beds = 0
            for bi in self.bed_inventory:
                inv = bi.to_dict()
                inventory.append(inv)
                total_available += bi.available_beds
                total_beds += bi.total_beds
            data['bed_inventory'] = inventory
            data['total_available'] = total_available
            data['total_beds'] = total_beds
            last_updated = None
            for bi in self.bed_inventory:
                if bi.last_updated and (last_updated is None or bi.last_updated > last_updated):
                    last_updated = bi.last_updated
            data['last_updated'] = last_updated.isoformat() if last_updated else None
        return data


class BedInventory(db.Model):
    """Aggregated bed counts per type per hospital."""
    __tablename__ = 'bed_inventory'

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    bed_type = db.Column(db.String(20), nullable=False)
    total_beds = db.Column(db.Integer, nullable=False, default=0)
    available_beds = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('hospital_id', 'bed_type', name='uq_hospital_bed_type'),
    )

    @property
    def occupied_beds(self):
        return self.total_beds - self.available_beds

    @property
    def occupancy_pct(self):
        if self.total_beds == 0:
            return 0
        return round((self.occupied_beds / self.total_beds) * 100)

    def to_dict(self):
        return {
            'bed_type': self.bed_type,
            'available': self.available_beds,
            'total': self.total_beds,
            'occupied': self.occupied_beds,
            'occupancy_pct': self.occupancy_pct,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }


class Bed(db.Model):
    """Individual bed records — kept for backward compatibility with existing booking logic."""
    __tablename__ = 'bed'

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    bed_type = db.Column(db.String(50), nullable=False)
    available = db.Column(db.Boolean, default=True)
    booked_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    booking_time = db.Column(db.DateTime, nullable=True)
    booking_ref = db.Column(db.String(20), unique=True, nullable=True)
    notes = db.Column(db.Text, nullable=True)


class LiveAlert(db.Model):
    """Pre-arrival alerts sent by patients to hospitals."""
    __tablename__ = 'live_alert'

    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_name = db.Column(db.String(200), nullable=False)
    patient_age = db.Column(db.Integer, nullable=True)
    patient_gender = db.Column(db.String(10), nullable=True)  # male, female, other
    bed_type_needed = db.Column(db.String(20), nullable=True)
    contact_phone = db.Column(db.String(15), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, acknowledged, admitted, cancelled
    user_lat = db.Column(db.Float, nullable=True)
    user_lng = db.Column(db.Float, nullable=True)
    distance_km = db.Column(db.Float, nullable=True)
    est_arrival_min = db.Column(db.Integer, nullable=True)
    booking_ref = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    acknowledger = db.relationship('User', foreign_keys=[acknowledged_by])

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
            'contact_phone': self.contact_phone,
            'notes': self.notes,
            'status': self.status,
            'user_lat': self.user_lat,
            'user_lng': self.user_lng,
            'distance_km': self.distance_km,
            'est_arrival_min': self.est_arrival_min,
            'booking_ref': self.booking_ref,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }
